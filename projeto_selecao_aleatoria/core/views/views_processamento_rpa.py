from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.models import ProcessamentoRPA
from core.serializers.processamentoserializer import ProcessamentoRPASerializer


class ProcessamentoRPAViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para listar e visualizar informações de processamentos RPA.
    """
    queryset = ProcessamentoRPA.objects.select_related('user').all()
    serializer_class = ProcessamentoRPASerializer
    ordering = ['-criado_em']
    filterset_fields = ['status', 'tipo', 'user']
    search_fields = ['descricao']

    @swagger_auto_schema(
        operation_description="Retorna todos os processamentos RPA registrados no sistema.",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filtra por status", type=openapi.TYPE_STRING),
            openapi.Parameter('tipo', openapi.IN_QUERY, description="Filtra por tipo", type=openapi.TYPE_STRING),
            openapi.Parameter('user', openapi.IN_QUERY, description="Filtra por ID do usuário", type=openapi.TYPE_INTEGER),
            openapi.Parameter('search', openapi.IN_QUERY, description="Busca por parte da descrição", type=openapi.TYPE_STRING)
        ],
        responses={200: ProcessamentoRPASerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """Lista todos os processamentos RPA com filtros"""
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='resumo-processamento')
    @swagger_auto_schema(
        operation_description="Retorna um resumo com a média de tempo, total, concluídos, em andamento e falhas.",
        responses={200: openapi.Response(description="Resumo dos processamentos")}
    )
    def resumo_processamento(self, request):
        """
        Endpoint para retornar estatísticas resumidas:
        - Média de tempo de processamento
        - Total de registros
        - Quantidade de processamentos concluídos
        - Quantidade em andamento
        - Quantidade com falha
        """
        queryset = self.filter_queryset(self.get_queryset())

        tempo_segundos = queryset.aggregate(media_tempo=Avg('tempo_real')).get('media_tempo') or 0
        minutos = int(tempo_segundos) // 60
        segundos = int(tempo_segundos) % 60
        tempo_formatado = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"

        return Response({
            "media_formatada": tempo_formatado,
            "media_segundos": round(tempo_segundos, 2),
            "total": queryset.count(),
            "concluidos": queryset.filter(status='concluido').count(),
            "em_andamento": queryset.filter(Q(status='processando') | Q(status='em_andamento')).count(),
            "falhas": queryset.filter(Q(status='falha') | Q(status='erro')).count()
        }, status=status.HTTP_200_OK)
