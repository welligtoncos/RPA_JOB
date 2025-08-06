from rest_framework import viewsets
from core.models import ProcessamentoRPA 
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from core.serializers.processamentoserializer import ProcessamentoRPASerializer

class ProcessamentoRPAViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para listar todos os processamentos RPA realizados por todos os usuários.
    """
    queryset = ProcessamentoRPA.objects.select_related('user').all()
    serializer_class = ProcessamentoRPASerializer
    ordering = ['-criado_em']
    filterset_fields = ['status', 'tipo', 'user']
    search_fields = ['descricao']

    @swagger_auto_schema(
        operation_description="Retorna todos os processamentos RPA registrados no sistema.",
        manual_parameters=[
            openapi.Parameter(
                'status', openapi.IN_QUERY, 
                description="Filtra por status (ex: pendente, processando, concluido, falha)", 
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'tipo', openapi.IN_QUERY, 
                description="Filtra por tipo (ex: selecao_aleatoria, docker_rpa, planilha, email)", 
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'user', openapi.IN_QUERY, 
                description="Filtra por ID do usuário que criou o processamento", 
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'search', openapi.IN_QUERY,
                description="Busca por parte da descrição",
                type=openapi.TYPE_STRING
            )
        ],
        responses={200: ProcessamentoRPASerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """Lista todos os processamentos RPA"""
        return super().list(request, *args, **kwargs)
