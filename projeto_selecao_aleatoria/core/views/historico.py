from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import ProcessamentoRPA
from ..serializers import RPAHistoricoSerializer
from .base import HistoricoPagination

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