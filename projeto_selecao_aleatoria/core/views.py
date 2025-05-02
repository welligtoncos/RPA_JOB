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
 

from .models import ProcessamentoRPA
from .serializers import RPADockerCreateSerializer, RPADockerHistoricoSerializer, RPADockerSerializer, RPAHistoricoSerializer

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
        # Check if this is a schema request
        is_swagger_fake_view = getattr(self, 'swagger_fake_view', False)
        
        if is_swagger_fake_view:
            # Return None or raise an appropriate exception for swagger
            from rest_framework.exceptions import NotFound
            raise NotFound("This is a schema request")
            
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
        # Check if this is a schema request
        is_swagger_fake_view = getattr(self, 'swagger_fake_view', False)
        
        if is_swagger_fake_view:
            # Return empty queryset for swagger schema generation
            return ProcessamentoRPA.objects.none()
            
        # Normal query for authenticated users
        return ProcessamentoRPA.objects.filter(
            user=self.request.user,
            status__in=['pendente', 'processando']
        ).order_by('-criado_em')

    def get_serializer_class(self):
        return RPADockerSerializer


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
        # Check if this is a schema request
        is_swagger_fake_view = getattr(self, 'swagger_fake_view', False)
        
        if is_swagger_fake_view:
            # Return empty queryset for swagger schema generation
            return ProcessamentoRPA.objects.none()
            
        # Normal query for authenticated users
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
class RPADockerViewSet(viewsets.ModelViewSet):  
    """ViewSet para gerenciar processamentos RPA via Docker."""
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        # Check if this is a schema request
        is_swagger_fake_view = getattr(self, 'swagger_fake_view', False)
        
        if is_swagger_fake_view:
            # Return empty queryset for swagger schema generation
            return ProcessamentoRPA.objects.none()
            
        # Normal query for authenticated users
        return ProcessamentoRPA.objects.filter(
            user=self.request.user,
            tipo='docker_rpa',
            status__in=['pendente', 'processando']
        ).order_by('-criado_em')

    def get_serializer_class(self):
        if self.action == 'create':
            return RPADockerCreateSerializer
        return RPADockerSerializer  # para leitura histórica/listagem


    def perform_create(self, serializer):
        """Salva e inicia o processamento."""
        processamento = serializer.save(user=self.request.user)
        RPADockerProcessor.processar_async(processamento)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # loga o erro completo no console
            logger.error("Erros validando payload Docker: %s", serializer.errors)
            return Response(
                {"erros": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
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
    
    @action(detail=False, methods=['get'])
    def ativos(self, request):
        """Só processos docker pendentes ou processando."""
        qs = ProcessamentoRPA.objects.filter(
            user=request.user,
            tipo='docker_rpa',
            status__in=['pendente', 'processando']
        ).order_by('-criado_em')
        serializer = RPADockerSerializer(qs, many=True)
        return Response(serializer.data)
    
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

# core/views.py (ou onde você tenha seus ViewSets)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ProcessamentoRPA
from .serializers import RPADockerHistoricoSerializer
from .views import HistoricoPagination  # sua classe de paginação customizada

class DockerHistoricoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar e resumir o histórico de processamentos Docker do usuário.
    Aceita ?page=…&page_size=… e ?status=pendente|processando|concluido|falha
    """
    serializer_class = RPADockerHistoricoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HistoricoPagination
    lookup_field = 'id'

    def get_queryset(self):
        # Base: apenas docker_rpa do usuário
        qs = ProcessamentoRPA.objects.filter(
            user=self.request.user,
            tipo='docker_rpa'
        )

        # Se vier ?status=… aplica o filtro
        status = self.request.query_params.get('status')
        if status in {'pendente','processando','concluido','falha'}:
            qs = qs.filter(status=status)

        return qs.order_by('-criado_em')

    @action(detail=False, methods=['get'])
    def resumo(self, request):
        """
        Retorna estatísticas agregadas:
         - total_executados
         - concluidos
         - falhas
         - tempo_medio_segundos
         - imagens_populares (top 5)
        """
        qs = self.get_queryset()
        total_executados = qs.count()
        concluidos      = qs.filter(status='concluido').count()
        falhas          = qs.filter(status='falha').count()

        # tempo médio de execução
        soma = 0
        cont = 0
        for p in qs.filter(status='concluido'):
            info = p.resultado.get('container_info') if p.resultado else None
            if info and info.get('duracao_segundos') is not None:
                soma += info['duracao_segundos']
                cont += 1
        tempo_medio = (soma / cont) if cont else 0

        # imagens mais usadas
        imagens = {}
        for p in qs:
            info = p.resultado.get('container_info') if p.resultado else None
            img = info.get('imagem') if info else None
            if img:
                imagens[img] = imagens.get(img, 0) + 1
        imagens_populares = dict(
            sorted(imagens.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        return Response({
            'total_executados': total_executados,
            'concluidos': concluidos,
            'falhas': falhas,
            'tempo_medio_segundos': tempo_medio,
            'imagens_populares': imagens_populares,
        })


#----------

 # core/views_api.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q
from django.shortcuts import get_object_or_404

from .models import ProcessamentoRPA, ResultadoProcessamento
from .serializers import RPAHistoricoSerializer, RPADockerHistoricoSerializer

User = get_user_model()

class UserProcessamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para gerenciar e visualizar processamentos por usuário específico.
    
    Para acesso administrativo apenas - permite consultar processamentos 
    de qualquer usuário no sistema.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['tipo', 'status', 'id', 'descricao']
    ordering_fields = ['criado_em', 'concluido_em', 'status', 'tipo']
    ordering = ['-criado_em']
    
    def get_queryset(self):
        """Filtra por usuário específico baseado no user_id na URL"""
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        queryset = ProcessamentoRPA.objects.filter(user=user)
        
        # Aplicar filtros adicionais por query params
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)
            
        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')
        if data_inicio and data_fim:
            queryset = queryset.filter(criado_em__range=[data_inicio, data_fim])
        
        return queryset
    
    def get_serializer_class(self):
        """Determina o serializer apropriado com base no tipo de processamento"""
        if self.action in ['retrieve', 'list']:
            tipo = self.request.query_params.get('tipo')
            if tipo == 'docker_rpa':
                return RPADockerHistoricoSerializer
        
        return RPAHistoricoSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """
        Personaliza a resposta para incluir informações sobre resultados associados
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Adiciona contagem de resultados
        resultados_count = ResultadoProcessamento.objects.filter(processamento=instance).count()
        data['resultados_count'] = resultados_count
        
        # Adiciona link para o endpoint de resultados
        if resultados_count > 0:
            data['resultados_url'] = request.build_absolute_uri() + 'resultados/'
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def estatisticas(self, request, user_id=None):
        """
        Fornece estatísticas dos processamentos do usuário específico.
        """
        user = get_object_or_404(User, id=user_id)
        queryset = ProcessamentoRPA.objects.filter(user=user)
        
        # Contagem por status
        status_count = queryset.values('status').annotate(
            count=Count('status')
        ).order_by('status')
        
        # Contagem por tipo
        tipo_count = queryset.values('tipo').annotate(
            count=Count('tipo')
        ).order_by('tipo')
        
        # Tempo médio de execução
        tempo_medio = queryset.filter(
            status='concluido', 
            tempo_real__isnull=False
        ).aggregate(media=Avg('tempo_real'))
        
        # Total de processamentos
        total = queryset.count()
        concluidos = queryset.filter(status='concluido').count()
        falhas = queryset.filter(status='falha').count()
        
        # Contagem de resultados gerados
        resultados_count = ResultadoProcessamento.objects.filter(
            processamento__user=user
        ).count()
        
        # Tipos de resultados
        tipos_resultados = ResultadoProcessamento.objects.filter(
            processamento__user=user
        ).values('tipo_resultado').annotate(
            count=Count('tipo_resultado')
        ).order_by('tipo_resultado')
        
        return Response({
            'usuario': {
                'id': user.id,
                'username': user.username
            },
            'total_processamentos': total,
            'concluidos': concluidos,
            'falhas': falhas,
            'taxa_sucesso': round((concluidos / total * 100), 2) if total > 0 else 0,
            'tempo_medio_segundos': tempo_medio['media'] if tempo_medio['media'] else 0,
            'por_status': status_count,
            'por_tipo': tipo_count,
            'resultados': {
                'total': resultados_count,
                'por_tipo': tipos_resultados
            }
        })
    
    @action(detail=True, methods=['get'])
    def resultados(self, request, pk=None, user_id=None):
        """
        Retorna os resultados associados a um processamento específico.
        """
        processamento = self.get_object()
        
        # Buscar resultados associados do novo modelo
        resultados = ResultadoProcessamento.objects.filter(processamento=processamento)
        
        if resultados.exists():
            # Formatar dados dos resultados
            data = []
            for r in resultados:
                data.append({
                    'id': str(r.id),
                    'nome_arquivo': r.nome_arquivo,
                    'caminho_s3': r.caminho_s3,
                    'tipo_resultado': r.get_tipo_resultado_display(),
                    'criado_em': r.criado_em.strftime('%Y-%m-%d %H:%M:%S'),
                    'tamanho': r.tamanho_formatado,
                    'extensao': r.extensao
                })
            return Response(data)
        
        # Se não houver resultados no modelo específico, tentar o campo resultado
        if not processamento.resultado:
            return Response(
                {"detail": "Este processamento não possui resultados."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Fallback para o campo resultado do processamento
        if isinstance(processamento.resultado, dict):
            container_info = processamento.resultado.get('container_info', {})
            resultado_arquivo = container_info.get('resultado_arquivo')
            caminho_arquivo = container_info.get('caminho_arquivo')
            
            if resultado_arquivo and caminho_arquivo:
                return Response({
                    'resultado_arquivo': resultado_arquivo,
                    'caminho_arquivo': caminho_arquivo,
                    's3_directory': container_info.get('s3_directory'),
                })
        
        # Último recurso: retorna o campo resultado completo
        return Response(processamento.resultado)


class UserDockerProcessamentoViewSet(UserProcessamentoViewSet):
    """ViewSet específico para processamentos Docker por usuário."""
    
    def get_queryset(self):
        """Sobrescreve para filtrar apenas processamentos Docker"""
        queryset = super().get_queryset()
        return queryset.filter(tipo='docker_rpa')
    
    def get_serializer_class(self):
        """Sempre usa o serializer Docker para este ViewSet"""
        return RPADockerHistoricoSerializer
    