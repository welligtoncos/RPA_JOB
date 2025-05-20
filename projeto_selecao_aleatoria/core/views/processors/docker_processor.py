import os, shlex, subprocess, threading, logging
from pathlib import Path
from datetime import datetime

docker_logger = logging.getLogger("docker_rpa")

class RPADockerProcessor:
    """
    Executa o ETL dentro de um container Docker, fazendo stream dos logs e
    atualizando o modelo ProcessamentoRPA em tempo real.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _make_volume_option(output_dir: Path) -> str:
        """
        Gera string -v <host_abs>:<container_dir>:rw compatível com Linux/macOS
        e Windows (C:\ → /c/).
        """
        host_path = output_dir.resolve()           # sempre absoluto

        if os.name == "nt":                        # Windows
            drive, rest = os.path.splitdrive(host_path)
            docker_host = f"/{drive.rstrip(':').lower()}{rest.replace('\\', '/')}"
        else:                                      # Unix-like já serve
            docker_host = str(host_path)

        return f"-v {docker_host}:/app/output:rw"

    # ──────────────────────────────────────────────────────────────────────────
    # DISPARA EM THREAD
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def processar_async(processamento):
        threading.Thread(
            target=RPADockerProcessor._processar,
            args=(processamento,),  
            daemon=True,
        ).start()

    # ──────────────────────────────────────────────────────────────────────────
    # LÓGICA PRINCIPAL
    # ──────────────────────────────────────────────────────────────────────────
 
    @staticmethod
    def _processar(processamento):
        try:
            docker_logger.info(
                "Iniciando Docker ETL (proc=%s, user=%s)",
                processamento.id,
                processamento.user_id,
            )
            processamento.iniciar_processamento()

            # 1) Dados base
            imagem_docker = "selecao_aleatoria:v1.1"
            comando = processamento.dados_entrada.get(
                "comando", "python /app/selecaoaleatoria.py"
            )
            container_name = f"selecao-aleatoria-{str(processamento.id).replace('-', '')[:12]}"

            container_info = {
                "container_iniciado": datetime.now().isoformat(),
                "imagem": imagem_docker,
                "comando": comando,
                "container_name": container_name,
                "user_id": processamento.user_id,
            }
            processamento.resultado = {"container_info": container_info}
            processamento.save(update_fields=["resultado"])

            # 2) Criar estrutura de diretórios local temporária para os resultados
            output_dir = Path(f"temp_output/{processamento.user_id}/processamento_{processamento.id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            volume_option = RPADockerProcessor._make_volume_option(output_dir)

            # 2.1) Adicionar volume para as credenciais AWS
            aws_creds_dir = os.path.expanduser("~/.aws")
            # Para Windows, ajustar o formato do caminho
            if os.name == "nt":
                drive, rest = os.path.splitdrive(aws_creds_dir)
                aws_creds_dir_docker = f"/{drive.rstrip(':').lower()}{rest.replace('\\', '/')}"
            else:
                aws_creds_dir_docker = aws_creds_dir
                
            aws_volume = f"-v {aws_creds_dir_docker}:/root/.aws:ro"

            # 2.2) Criar estrutura de diretórios no S3
            try:
                import boto3
                from botocore.exceptions import ClientError
                
                # Usar perfil específico
                session = boto3.Session(profile_name='appbeta-s3-user', region_name='us-east-2')
                s3_client = session.client('s3')
                
                bucket_name = "appbeta-user-results"
                
                # Caminho para a pasta do processamento
                s3_dir_key = f"selecao_aleatoria/usuarios/{processamento.user_id}/resultados/processamento_{processamento.id}/"
                
                # Criar diretório no S3
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_dir_key,
                    Body=''
                )
                
                # Registrar o caminho nos metadados do processamento
                container_info["s3_directory"] = f"s3://{bucket_name}/{s3_dir_key}"
                processamento.resultado["container_info"] = container_info
                processamento.save(update_fields=["resultado"])
                
                docker_logger.info(f"Diretório S3 criado: s3://{bucket_name}/{s3_dir_key}")
            except Exception as e:
                docker_logger.error(f"Erro ao criar diretório no S3: {e}")

            # 3) Variáveis de ambiente
            env_vars = processamento.dados_entrada.get("env_vars", {})
            env_vars["USER_ID"] = str(processamento.user_id)
            env_vars["PROCESSAMENTO_ID"] = str(processamento.id)
            env_option = " ".join(f"-e {k}='{v}'" for k, v in env_vars.items())

            # 4) Comando docker (incluindo volume AWS)
            docker_cmd = (
                f"docker run -it --rm --name {container_name} "
                f"{volume_option} {aws_volume} {env_option} {imagem_docker}"
            )
            
            if comando and comando != "python /app/selecaoaleatoria.py":
                docker_cmd += f" {comando}"
                    
            docker_logger.info("Docker cmd: %s", docker_cmd)

            # 5) Executa container
            run_proc = subprocess.Popen(
                shlex.split(docker_cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
            )

            # 6) Stream dos logs
            for linha in run_proc.stdout:
                linha = linha.rstrip()
                docker_logger.info("[%s] %s", container_name, linha)

                # Atualiza progresso por palavras-chave
                if any(p in linha for p in ("Baixando arquivo", "Extraindo dados")):
                    processamento.atualizar_progresso(25)
                elif any(p in linha for p in ("Transformação", "Coluna para acessar")):
                    processamento.atualizar_progresso(50)
                elif "Seleção de itens concluída" in linha:
                    processamento.atualizar_progresso(60)
                elif "Resultado salvo como" in linha:
                    processamento.atualizar_progresso(75)
                    try:
                        nome = linha.split("Resultado salvo como")[-1].strip()
                        container_info["resultado_arquivo"] = nome
                        processamento.resultado["container_info"] = container_info
                        processamento.save(update_fields=["resultado"])
                    except Exception:
                        pass
                elif "Upload concluído" in linha:
                    processamento.atualizar_progresso(90)
                elif "Pipeline ETL Concluído" in linha:
                    processamento.atualizar_progresso(100)
                elif "progresso:" in linha.lower():
                    try:
                        pct = int(linha.split("progresso:")[-1].strip().rstrip("%"))
                        processamento.atualizar_progresso(min(pct, 100))
                    except Exception as exc:
                        docker_logger.error("Progresso malformado: %s", exc)

            # 7) Aguarda término
            run_proc.wait()
            exit_code = run_proc.returncode or 0

            # 8) Procura arquivos de resultado e faz upload para S3
            arquivos = [f for f in output_dir.glob("SA_*.xlsx") if f.is_file()]
            if arquivos:
                arq = arquivos[0]
                
                # Upload para o S3 com a estrutura solicitada
                try:
                    import boto3
                    # Usar perfil específico
                    session = boto3.Session(profile_name='appbeta-s3-user', region_name='us-east-2')
                    s3_client = session.client('s3')
                    
                    bucket_name = "appbeta-user-results"
                    
                    # Caminho no formato: selecao_aleatoria/usuarios/14/resultados/processamento_1/arquivo.xlsx
                    s3_key = f"selecao_aleatoria/usuarios/{processamento.user_id}/resultados/processamento_{processamento.id}/{arq.name}"
                    
                    # Upload do arquivo
                    s3_client.upload_file(str(arq), bucket_name, s3_key)
                    
                    # Caminho completo para o arquivo no S3
                    s3_path = f"s3://{bucket_name}/{s3_key}"
                    container_info.update(
                        resultado_arquivo=arq.name,
                        caminho_arquivo=s3_path,
                    )
                    docker_logger.info(f"Arquivo enviado para S3: {s3_path}")
                except Exception as e:
                    # Fallback para caminho local se falhar o upload
                    docker_logger.error(f"Erro ao enviar para S3: {e}")
                    container_info.update(
                        resultado_arquivo=arq.name,
                        caminho_arquivo=str(arq),
                    )

            # 9) Metadados finais
            fim = datetime.now()
            duracao = (
                fim - datetime.fromisoformat(container_info["container_iniciado"])
            ).total_seconds()

            container_info.update(
                container_finalizado=fim.isoformat(),
                duracao_segundos=duracao,
                exit_code=exit_code,
                output_dir=str(output_dir),
            )
            processamento.resultado["container_info"] = container_info
            processamento.save(update_fields=["resultado"])

            # 10) Status final
            if exit_code == 0:
                processamento.concluir(
                    {
                        "tipo": processamento.tipo,
                        "mensagem": "Processamento ETL concluído com sucesso",
                        "timestamp": fim.isoformat(),
                        **container_info,
                    }
                )
                docker_logger.info("Processo %s concluído com sucesso.", processamento.id)
            else:
                processamento.falhar(
                    f"Container retornou código {exit_code}."
                )
                docker_logger.error(
                    "Processo %s falhou (exit=%s).", processamento.id, exit_code
                )

        except Exception as exc:
            docker_logger.exception("Falha geral no Docker ETL: %s", exc)
            processamento.falhar(str(exc))
            # Limpeza (se ainda existir)
            try:
                subprocess.run(["docker", "rm", "-f", container_name])
            except Exception:
                pass
                