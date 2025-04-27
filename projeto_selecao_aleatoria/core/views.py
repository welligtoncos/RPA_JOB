# views.py
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

    def get_object(self):
        return ProcessamentoRPA.objects.get(id=self.kwargs['pk'])

    def list(self, request, *args, **kwargs):
        # Log para verificar processos retornados
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Processos retornados: {serializer.data}")
        return Response(serializer.data)

    def get_queryset(self):
        # Retorna processos do usuário atual
        return ProcessamentoRPA.objects.filter(
            user=self.request.user, 
            status__in=['pendente', 'processando']
        ).order_by('-criado_em')

    def get_serializer_class(self):
        if self.action == 'create':
            return RPACreateSerializer
        return RPASerializer

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
        """Retorna todos os processamentos do usuário, incluindo concluídos e com falha"""
        return ProcessamentoRPA.objects.filter(
            user=self.request.user
        ).order_by('-criado_em')

# serializers.py
class RPAHistoricoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessamentoRPA
        fields = [
            'id', 
            'tipo', 
            'status', 
            'progresso', 
            'criado_em', 
            'concluido_em', 
            'resultado',
            'mensagem_erro'
        ]
        read_only_fields = fields

# urls.py

# Adicione ao arquivo views.py
import shlex
import subprocess

import shlex
import subprocess
import logging
from datetime import datetime

# Para classes regulares não relacionadas ao Docker
logger = logging.getLogger(__name__)

# Para classes Docker, defina o logger específico
docker_logger = logging.getLogger('docker_rpa')

class RPADockerProcessor:
    """Classe para executar processamento RPA via Docker com atualizações em tempo real."""

  
    # Adicione este método que está faltando na classe RPADockerProcessor
    @staticmethod
    def processar_async(processamento):
        """Inicia o processamento em segundo plano usando threading para cada usuário."""
        thread = threading.Thread(
            target=RPADockerProcessor._processar,
            args=(processamento,),
            daemon=True
        )
        thread.start()
        return thread
    
    @staticmethod
    def _processar(processamento):
        """Executa o container Docker e monitora seu progresso em tempo real para cada usuário."""
        try:
             # Use o logger específico para Docker desde o início
            docker_logger.info(f"Iniciando processamento Docker RPA para o usuário {processamento.user.id} com ID {processamento.id}")
            processamento.iniciar_processamento()

            # Utilizando a imagem "rpa-homologacao:1.0" para o container Docker
            imagem_docker = "rpa-homologacao:1.0"
            comando = processamento.parametros.get('comando', 'python -c "print(\'Hello from Docker\')"')
            
            # Gera um nome único para o container baseado no ID do processamento
            container_name = f"rpa_{processamento.id.replace('-', '')[:12]}"

            # Registra informações iniciais do container
            container_info = {
                'container_iniciado': datetime.now().isoformat(),
                'imagem': imagem_docker,
                'comando': comando,
                'container_name': container_name
            }
            processamento.resultado = {'container_info': container_info}
            processamento.save(update_fields=['resultado'])
            
             # Prepara o comando Docker com nome específico (sem --rm para poder obter logs)
            docker_comando = f"docker run -d --name {container_name} {imagem_docker} {comando}"
            # Use docker_logger em vez de logger
            docker_logger.info(f"Executando comando Docker: {docker_comando}")
            
            # Executa o container Docker
            processo = subprocess.Popen(
                shlex.split(docker_comando),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Captura o ID do container
            container_id = processo.stdout.read().strip()
            container_info['container_id'] = container_id
            processamento.resultado['container_info'] = container_info
            processamento.save(update_fields=['resultado'])
            docker_logger.info(f"Container iniciado com ID: {container_id}")
            
            # Monitora logs em tempo real
            logs_cmd = f"docker logs -f {container_name}"
            logs_processo = subprocess.Popen(
                shlex.split(logs_cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Lê e registra a saída do container em tempo real
            for linha in logs_processo.stdout:
                linha_limpa = linha.strip()
                docker_logger.info(f"Docker output ({container_name}): {linha_limpa}")
                if "progresso" in linha_limpa.lower():  # Caso o progresso seja informado no log
                    try:
                        progresso = int(linha_limpa.split(':')[1].strip().replace('%', ''))
                        processamento.atualizar_progresso(min(progresso, 100))
                    except (ValueError, IndexError) as e:
                        docker_logger.error(f"Erro ao processar progresso: {e}")
            
            # Aguarda o término do container
            wait_cmd = f"docker wait {container_name}"
            wait_processo = subprocess.Popen(
                shlex.split(wait_cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            returncode = int(wait_processo.stdout.read().strip() or 0)
            
            # Captura logs de erro, se houver
            err_cmd = f"docker logs {container_name} 2>&1 | grep -i error"
            err_processo = subprocess.Popen(
                err_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            erros = err_processo.stdout.read().strip()
            
            # Calcula tempo de execução
            tempo_final = datetime.now()
            tempo_inicial = datetime.fromisoformat(container_info['container_iniciado'])
            duracao_segundos = (tempo_final - tempo_inicial).total_seconds()
            
            # Atualiza informações do container
            container_info['container_finalizado'] = tempo_final.isoformat()
            container_info['duracao_segundos'] = duracao_segundos
            container_info['exit_code'] = returncode
            processamento.resultado['container_info'] = container_info
            processamento.save(update_fields=['resultado'])
            
            # Remove o container após o processamento
            rm_cmd = f"docker rm {container_name}"
            subprocess.run(shlex.split(rm_cmd))
            docker_logger.info(f"Container {container_name} removido após processamento")
            
            # Define o status de sucesso ou falha
            if returncode == 0:
                resultado = {
                    'tipo': processamento.tipo,
                    'mensagem': 'Processamento Docker concluído com sucesso',
                    'timestamp': datetime.now().isoformat(),
                    'container_info': container_info
                }
                processamento.concluir(resultado)
                docker_logger.info(f"Processamento Docker RPA para o usuário {processamento.user.id} com ID {processamento.id} concluído com sucesso.")
            else:
                resultado = {
                    'tipo': processamento.tipo,
                    'mensagem': 'Processamento Docker falhou',
                    'timestamp': datetime.now().isoformat(),
                    'container_info': container_info,
                    'erros_detectados': erros
                }
                processamento.falhar(f"Container falhou com código {returncode}. Erros: {erros}")
                processamento.resultado = resultado
                processamento.save(update_fields=['resultado'])
                
        except Exception as e:
            docker_logger.error(f"Erro no processamento Docker RPA para o usuário {processamento.user.id} com ID {processamento.id}: {str(e)}")
            processamento.falhar(str(e))
            
            # Tenta remover o container em caso de erro (limpeza)
            try:
                container_name = f"rpa_{processamento.id.replace('-', '')[:12]}"
                rm_cmd = f"docker rm -f {container_name}"
                subprocess.run(shlex.split(rm_cmd))
                docker_logger.info(f"Container {container_name} removido após erro")
            except Exception as cleanup_error:
                docker_logger.error(f"Erro ao limpar o container: {str(cleanup_error)}")


class RPADockerViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar processamentos RPA via Docker."""
    permission_classes = [IsAuthenticated]

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