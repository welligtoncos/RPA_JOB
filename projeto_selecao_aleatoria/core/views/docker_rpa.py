import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import ProcessamentoRPA
from ..serializers import (
    RPADockerCreateSerializer, RPADockerSerializer, 
    RPADockerHistoricoSerializer
)
from .processors.docker_processor import RPADockerProcessor
from .base import HistoricoPagination

docker_logger = logging.getLogger('docker_rpa')

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
            docker_logger.error("Erros validando payload Docker: %s", serializer.errors)
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