# views.py
from pathlib import Path
import threading
import time
import logging
from datetime import datetime
from django.utils import timezone
from rest_framework import viewsets, status, serializers  # Adicione serializers aqui
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.pagination import PageNumberPagination

from .models import ProcessamentoRPA, ProcessamentoRPATemplate
from .serializers import RPADockerHistoricoSerializer, RPADockerSerializer, RPASerializer, RPACreateSerializer, RPAHistoricoSerializer

logger = logging.getLogger(__name__)

class RPAProcessor:
    """Classe para simular processamento RPA de forma assíncrona."""

    @staticmethod
    def processar_async(processamento):
        """Inicia o processamento em segundo plano usando threading."""
        thread = threading.Thread(
            target=RPAProcessor._processar,
            args=(processamento,),
            daemon=True
        )
        thread.start()
        return thread

    @staticmethod
    def _processar(processamento):
        """Executa o processamento simulado."""
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"Iniciando processamento RPA {processamento.id}")
            processamento.iniciar_processamento()

            duracao_total = 30  # tempo total do processamento (segundos)
            processamento.tempo_estimado = duracao_total
            processamento.save(update_fields=['tempo_estimado'])

            progresso_intervalo = 5
            passos = duracao_total // progresso_intervalo

            for i in range(1, passos + 1):
                time.sleep(progresso_intervalo)
                progresso = int((i / passos) * 100)
                processamento.atualizar_progresso(min(progresso, 99))

            resultado = {
                'tipo': processamento.tipo,
                'mensagem': 'Processamento concluído com sucesso',
                'timestamp': datetime.now().isoformat()
            }

            processamento.concluir(resultado)
            logger.info(f"Processamento RPA {processamento.id} concluído.")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erro no processamento RPA {processamento.id}: {str(e)}")
            processamento.falhar(str(e))


class RPAViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar processamentos RPA."""
    permission_classes = [IsAuthenticated]
    pagination_class  = PageNumberPagination

    def get_object(self):
        return ProcessamentoRPA.objects.get(
            id=self.kwargs['pk'],
            user=self.request.user
        )


    def list(self, request, *args, **kwargs):
        # Log para verificar processos retornados
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Processos retornados: {serializer.data}")
        return Response(serializer.data)

    def get_queryset(self):
        """Somente processos ativos do usuário logado."""
        return ProcessamentoRPA.objects.filter(
            user=self.request.user,
            status__in=['pendente', 'processando']
        ).order_by('-criado_em')

    def get_serializer_class(self):
        return RPACreateSerializer if self.action == 'create' else RPASerializer

    def perform_create(self, serializer):
        """Salva o processamento associando ao usuário automaticamente."""
        processamento = serializer.save(user=self.request.user)
        RPAProcessor.processar_async(processamento)

    def create(self, request, *args, **kwargs):
        """Cria um novo processamento RPA."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'id': serializer.instance.id, 
                'mensagem': 'Processamento RPA iniciado',
                'tipo': serializer.instance.tipo
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(detail=True, methods=['post'])
    def reiniciar(self, request, pk=None):
        """Permite reiniciar um processamento concluído ou com falha."""
        processamento = self.get_object()

        if processamento.status in ['concluido', 'falha']:
            processamento.status = 'pendente'
            processamento.iniciado_em = None
            processamento.concluido_em = None
            processamento.resultado = None
            processamento.mensagem_erro = None
            processamento.progresso = 0
            processamento.tempo_real = None
            processamento.save()

            RPAProcessor.processar_async(processamento)

            return Response({'mensagem': 'Processamento RPA reiniciado'})
        else:
            return Response(
                {'erro': f'Não é possível reiniciar um processamento com status {processamento.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

 
class HistoricoPagination(PageNumberPagination):
    page_size = 10  # Número de itens por página
    page_size_query_param = 'page_size'
    max_page_size = 100

class HistoricoRPAViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para listar histórico de processamentos do usuário"""
    permission_classes = [IsAuthenticated]
    serializer_class = RPAHistoricoSerializer
    pagination_class = HistoricoPagination

    def get_queryset(self):
        return ProcessamentoRPA.objects.filter(
            user=self.request.user
        ).order_by('-criado_em')

 
 

# Para classes Docker, defina o logger específico 
import os
import shlex
import subprocess
import logging
from datetime import datetime
import threading

docker_logger = logging.getLogger('docker_rpa')

# rpa/docker_processor.py
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
            imagem_docker = "sharepoint-etl"          # sem tag ⇒ latest
            comando       = processamento.dados_entrada.get(
                "comando", "python /app/sharepoint_etl.py"
            )
            container_name = f"etl_{str(processamento.id).replace('-', '')[:12]}"

            container_info = {
                "container_iniciado": datetime.now().isoformat(),
                "imagem": imagem_docker,
                "comando": comando,
                "container_name": container_name,
            }
            processamento.resultado = {"container_info": container_info}
            processamento.save(update_fields=["resultado"])

            # 2) Saída (host)
            output_dir = Path("docker_output") / container_name
            output_dir.mkdir(parents=True, exist_ok=True)
            volume_option = RPADockerProcessor._make_volume_option(output_dir)

            # 3) Variáveis de ambiente opcionais
            env_vars   = processamento.dados_entrada.get("env_vars", {})
            env_option = " ".join(f"-e {k}='{v}'" for k, v in env_vars.items())

            # 4) Comando docker: -it + --rm + nome fixo
            docker_cmd = (
                f"docker run -it --rm --name {container_name} "
                f"{volume_option} {env_option} {imagem_docker} {comando}"
            )
            docker_logger.info("Docker cmd: %s", docker_cmd)

            # 5) Executa container (Popen para ler logs)
            run_proc = subprocess.Popen(
            shlex.split(docker_cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',       # força UTF-8
            errors='replace',       # substitui bytes inválidos por �
            bufsize=1,
        )
            # container_id é a primeira linha de saída em modo -it? Não; vamos
            # apenas usar o nome do container para 'wait' e 'logs'.

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

            # 8) Procura arquivos de resultado
            arquivos = [f for f in output_dir.glob("SA_*.xlsx") if f.is_file()]
            if arquivos:
                arq = arquivos[0]
                container_info.update(
                    resultado_arquivo=arq.name,
                    caminho_arquivo=str(arq),
                )
                docker_logger.info("Arquivo extraído: %s", arq.name)

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

class RPADockerViewSet(viewsets.ModelViewSet):  
    """ViewSet para gerenciar processamentos RPA via Docker."""
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return ProcessamentoRPA.objects.filter(
            user=self.request.user,
            tipo='docker_rpa',
            status__in=['pendente', 'processando']
        ).order_by('-criado_em')

    def get_serializer_class(self):
        return RPADockerSerializer

    def perform_create(self, serializer):
        """Salva e inicia o processamento."""
        processamento = serializer.save(user=self.request.user)
        RPADockerProcessor.processar_async(processamento)

    def create(self, request, *args, **kwargs):
        """Cria um novo processamento Docker RPA."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'id': serializer.instance.id, 
                'mensagem': 'Processamento Docker RPA iniciado',
                'tipo': 'docker_rpa'
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=True, methods=['post'])
    def reiniciar(self, request, pk=None):
        """Permite reiniciar um processamento."""
        processamento = self.get_object()

        if processamento.status in ['concluido', 'falha']:
            processamento.status = 'pendente'
            processamento.iniciado_em = None
            processamento.concluido_em = None
            processamento.resultado = None
            processamento.mensagem_erro = None
            processamento.progresso = 0
            processamento.tempo_real = None
            processamento.save()

            RPADockerProcessor.processar_async(processamento)

            return Response({'mensagem': 'Processamento Docker RPA reiniciado'})
        else:
            return Response(
                {'erro': f'Não é possível reiniciar um processamento com status {processamento.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class DockerHistoricoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para listar histórico de processamentos Docker."""
    permission_classes = [IsAuthenticated]
    pagination_class = HistoricoPagination
    
    def get_serializer_class(self):
        return RPADockerHistoricoSerializer
        
    def get_queryset(self):
        """Retorna todos os processamentos Docker do usuário."""
        return ProcessamentoRPA.objects.filter(
            user=self.request.user,
            tipo='docker_rpa'
        ).order_by('-criado_em')
    
    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """Retorna um resumo consolidado dos containers Docker executados."""
        queryset = self.get_queryset()
        
        # Estatísticas básicas
        total_executados = queryset.count()
        concluidos = queryset.filter(status='concluido').count()
        falhas = queryset.filter(status='falha').count()
        
        # Tempo médio de execução
        tempo_medio = 0
        containers_com_tempo = 0
        
        for proc in queryset.filter(status='concluido'):
            if proc.resultado and isinstance(proc.resultado, dict) and 'container_info' in proc.resultado:
                if 'duracao_segundos' in proc.resultado['container_info']:
                    tempo_medio += proc.resultado['container_info']['duracao_segundos']
                    containers_com_tempo += 1
        
        if containers_com_tempo > 0:
            tempo_medio = tempo_medio / containers_com_tempo
            
        # Imagens mais usadas
        imagens = {}
        for proc in queryset:
            if proc.resultado and isinstance(proc.resultado, dict) and 'container_info' in proc.resultado:
                imagem = proc.resultado['container_info'].get('imagem', 'desconhecida')
                if imagem in imagens:
                    imagens[imagem] += 1
                else:
                    imagens[imagem] = 1
                    
        # Ordena por uso
        imagens_ordenadas = sorted(imagens.items(), key=lambda x: x[1], reverse=True)
        
        return Response({
            'total_executados': total_executados,
            'concluidos': concluidos,
            'falhas': falhas,
            'tempo_medio_segundos': tempo_medio,
            'imagens_populares': dict(imagens_ordenadas[:5])  # Top 5 imagens
        })