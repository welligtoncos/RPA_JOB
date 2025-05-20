import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import ProcessamentoRPA
from ..serializers import RPADockerSerializer
from .processors.rpa_processor import RPAProcessor

logger = logging.getLogger(__name__)

class RPAViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar processamentos RPA."""
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

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