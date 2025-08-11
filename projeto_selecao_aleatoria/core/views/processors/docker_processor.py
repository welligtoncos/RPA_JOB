import os, shlex, subprocess, threading, logging
from pathlib import Path
from datetime import datetime

docker_logger = logging.getLogger("docker_rpa")

 # helper no topo do arquivo (depois dos imports)
def _safe_console(s: str) -> str:
    # Remove apenas chars que não existem no cp1252 (emojis, etc.); mantém acentos.
    return s.encode("cp1252", "ignore").decode("cp1252") if os.name == "nt" else s

class RPADockerProcessor:
    """
    Executa o ETL dentro de um container Docker, fazendo stream dos logs e
    atualizando o modelo ProcessamentoRPA em tempo real.
    """

 

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
            imagem_docker = "selecao_aleatoria:v2.2"  # use a mesma tag em todo lugar
            comando = processamento.dados_entrada.get("comando", "python -u main.py")
            container_name = f"selecao-aleatoria-{str(processamento.id).replace('-', '')[:12]}"

            container_info = {
                "container_iniciado": datetime.now().isoformat(),
                "imagem": imagem_docker,          # agora bate com o docker run
                "comando": comando,
                "container_name": container_name,
                "user_id": processamento.user_id,
            }
            processamento.resultado = {"container_info": container_info}
            processamento.save(update_fields=["resultado"])


            # 2) Criar estrutura de diretórios local temporária para os resultados
            output_dir = Path(f"temp_output/{processamento.user_id}/processamento_{processamento.id}")
            output_dir.mkdir(parents=True, exist_ok=True) 
  

            # 2.2) Criar estrutura de diretórios no S3
            try:
                import boto3 
                
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

          # 3) Variáveis de ambiente (inclui AWS e OUTPUT_DIR)
            env_vars = processamento.dados_entrada.get("env_vars", {})
            env_vars.update({
                "USER_ID": str(processamento.user_id),
                "PROCESSAMENTO_ID": str(processamento.id),
                "OUTPUT_DIR": "/app/output",  # garanta que seu salvar_excel use isso
                "AWS_REGION": os.getenv("AWS_REGION", "us-east-2"),
                "AWS_S3_BUCKET": os.getenv("AWS_S3_BUCKET", "appbeta-user-results"),
                "AWS_PROFILE": os.getenv("AWS_PROFILE", "appbeta-s3-user"),
                "S3_SSE": os.getenv("S3_SSE", "AES256"),
                "S3_BASE_PREFIX": os.getenv("S3_BASE_PREFIX", "selecao_aleatoria"),
            })

            # 4) Volumes (output + dados + ~/.aws)
            def to_docker_path(p: str) -> str:
                if os.name == "nt":
                    drive, rest = os.path.splitdrive(p)
                    return f"/{drive.rstrip(':').lower()}{rest.replace('\\', '/')}"
                return p

            output_dir.mkdir(parents=True, exist_ok=True)
            host_output = to_docker_path(str(output_dir.resolve()))

            aws_creds_dir = os.path.expanduser("~/.aws")
            aws_creds_dir_docker = to_docker_path(aws_creds_dir)

            dados_dir = Path(f"temp_dados/{processamento.user_id}/processamento_{processamento.id}")
            dados_dir.mkdir(parents=True, exist_ok=True)
            host_dados = to_docker_path(str(dados_dir.resolve()))

            # 5) docker run como LISTA (sem -it, sem aspas simples) 
            args = [
                "docker", "run", "--rm",
                "--name", container_name,
                "-w", "/app",
                "-v", f"{host_output}:/app/output:rw",
                "-v", f"{aws_creds_dir_docker}:/root/.aws:ro",
                "-v", f"{host_dados}:/app/dados:rw",
            ]
            for k, v in env_vars.items():
                args += ["-e", f"{k}={v}"]

            args.append(imagem_docker)
            if comando and comando.strip():
                args += shlex.split(comando)

            docker_logger.info("Docker args: %s", args)

            # 6) Executa container e stream de logs
            run_proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            for linha in run_proc.stdout:
                linha = linha.rstrip()
                docker_logger.info("[%s] %s", container_name, _safe_console(linha))  # <- sem emojis no console

                # Use a linha original para detectar progresso (funciona mesmo com emojis)
                if any(p in linha for p in ("Baixando arquivo", "Extraindo dados")):
                    processamento.atualizar_progresso(25)
                elif any(p in linha for p in ("Transformação", "Coluna para acessar")):
                    processamento.atualizar_progresso(50)
                elif "Seleção de itens concluída" in linha:
                    processamento.atualizar_progresso(60)
                elif "Resultado salvo como" in linha:
                    processamento.atualizar_progresso(75)
                elif "Upload concluído" in linha:
                    processamento.atualizar_progresso(90)
                elif "Pipeline ETL Concluído" in linha:
                    processamento.atualizar_progresso(100)

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
                    s3_client.upload_file(
                        str(arq), bucket_name, s3_key,
                        ExtraArgs={"ServerSideEncryption": "AES256", "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
                    )

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
                