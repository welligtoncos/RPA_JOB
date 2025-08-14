from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db.models import Q
from datetime import datetime, timedelta

from ..models import ProcessamentoRPA
from ..serializers import RPAHistoricoSerializer
from .base import HistoricoPagination


class ProcessamentoRPAFilter(django_filters.FilterSet):
    """Filtros personalizados para ProcessamentoRPA"""
    
    # Filtros por data
    data_inicio = django_filters.DateFilter(field_name='criado_em', lookup_expr='gte')
    data_fim = django_filters.DateFilter(field_name='criado_em', lookup_expr='lte')
    data_range = django_filters.DateFromToRangeFilter(field_name='criado_em')
    
    # Filtros por período predefinido
    periodo = django_filters.ChoiceFilter(
        choices=[
            ('hoje', 'Hoje'),
            ('semana', 'Última Semana'),
            ('mes', 'Último Mês'),
            ('3meses', 'Últimos 3 Meses'),
        ],
        method='filter_by_periodo'
    )
    
    # Filtro por múltiplos status
    status_list = django_filters.CharFilter(method='filter_status_list')
    
    # Filtro por múltiplos tipos
    tipo_list = django_filters.CharFilter(method='filter_tipo_list')
    
    # Filtro por texto na descrição
    busca = django_filters.CharFilter(method='filter_busca')
    
    # Filtros booleanos
    com_erro = django_filters.BooleanFilter(method='filter_com_erro')
    concluidos = django_filters.BooleanFilter(method='filter_concluidos')
    em_andamento = django_filters.BooleanFilter(method='filter_em_andamento')

    class Meta:
        model = ProcessamentoRPA
        fields = {
            'status': ['exact', 'in'],
            'tipo': ['exact', 'in'],
            'progresso': ['exact', 'gte', 'lte'],
            'tempo_real': ['gte', 'lte'],
            'template': ['exact', 'isnull'],
        }

    def filter_by_periodo(self, queryset, name, value):
        """Filtrar por períodos predefinidos"""
        hoje = datetime.now().date()
        
        if value == 'hoje':
            return queryset.filter(criado_em__date=hoje)
        elif value == 'semana':
            data_inicio = hoje - timedelta(days=7)
            return queryset.filter(criado_em__date__gte=data_inicio)
        elif value == 'mes':
            data_inicio = hoje - timedelta(days=30)
            return queryset.filter(criado_em__date__gte=data_inicio)
        elif value == '3meses':
            data_inicio = hoje - timedelta(days=90)
            return queryset.filter(criado_em__date__gte=data_inicio)
        
        return queryset

    def filter_status_list(self, queryset, name, value):
        """Filtrar por múltiplos status separados por vírgula"""
        if value:
            status_list = [s.strip() for s in value.split(',')]
            return queryset.filter(status__in=status_list)
        return queryset

    def filter_tipo_list(self, queryset, name, value):
        """Filtrar por múltiplos tipos separados por vírgula"""
        if value:
            tipo_list = [t.strip() for t in value.split(',')]
            return queryset.filter(tipo__in=tipo_list)
        return queryset

    def filter_busca(self, queryset, name, value):
        """Buscar texto na descrição ou mensagem de erro"""
        if value:
            return queryset.filter(
                Q(descricao__icontains=value) | 
                Q(mensagem_erro__icontains=value)
            )
        return queryset

    def filter_com_erro(self, queryset, name, value):
        """Filtrar processamentos com erro"""
        if value is True:
            return queryset.filter(status='falha')
        elif value is False:
            return queryset.exclude(status='falha')
        return queryset

    def filter_concluidos(self, queryset, name, value):
        """Filtrar processamentos concluídos"""
        if value is True:
            return queryset.filter(status='concluido')
        elif value is False:
            return queryset.exclude(status='concluido')
        return queryset

    def filter_em_andamento(self, queryset, name, value):
        """Filtrar processamentos em andamento"""
        if value is True:
            return queryset.filter(status__in=['pendente', 'processando'])
        elif value is False:
            return queryset.exclude(status__in=['pendente', 'processando'])
        return queryset


class HistoricoRPAFiltroViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar e filtrar histórico de processamentos RPA do usuário
    
    Filtros disponíveis:
    - status: Status específico do processamento
    - tipo: Tipo de automação
    - data_inicio/data_fim: Intervalo de datas
    - periodo: hoje, semana, mes, 3meses
    - status_list: Múltiplos status (ex: pendente,processando)
    - tipo_list: Múltiplos tipos (ex: planilha,email)
    - busca: Busca por texto na descrição
    - com_erro: true/false para processamentos com falha
    - concluidos: true/false para processamentos concluídos
    - em_andamento: true/false para processamentos ativos
    - progresso__gte/lte: Filtrar por percentual de progresso
    - tempo_real__gte/lte: Filtrar por tempo de execução
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = RPAHistoricoSerializer
    pagination_class = HistoricoPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProcessamentoRPAFilter
    ordering_fields = ['criado_em', 'iniciado_em', 'concluido_em', 'progresso', 'tempo_real']
    ordering = ['-criado_em']  # Ordenação padrão

    def get_queryset(self):
        """Retorna processamentos do usuário autenticado"""
        # Check if this is a schema request
        is_swagger_fake_view = getattr(self, 'swagger_fake_view', False)
        
        if is_swagger_fake_view:
            return ProcessamentoRPA.objects.none()
        
        if not self.request.user.is_authenticated:
            return ProcessamentoRPA.objects.none()
            
        # Base queryset com otimizações
        return ProcessamentoRPA.objects.filter(
            user=self.request.user
        ).select_related('template', 'user').order_by('-criado_em')

    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """
        Endpoint adicional para estatísticas do histórico do usuário
        GET /api/historico-rpa-filtro/estatisticas/
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Aplicar os mesmos filtros da view principal
        total = queryset.count()
        
        estatisticas = {
            'total_processamentos': total,
            'por_status': {},
            'por_tipo': {},
            'tempo_medio': None,
            'taxa_sucesso': 0,
        }
        
        if total > 0:
            # Contagem por status
            for status, _ in ProcessamentoRPA.STATUS_CHOICES:
                count = queryset.filter(status=status).count()
                estatisticas['por_status'][status] = count
            
            # Contagem por tipo
            for tipo, _ in ProcessamentoRPA.TIPO_CHOICES:
                count = queryset.filter(tipo=tipo).count()
                if count > 0:
                    estatisticas['por_tipo'][tipo] = count
            
            # Tempo médio (apenas processamentos concluídos com tempo_real)
            processamentos_com_tempo = queryset.filter(
                status='concluido',
                tempo_real__isnull=False
            )
            if processamentos_com_tempo.exists():
                from django.db.models import Avg
                tempo_medio = processamentos_com_tempo.aggregate(
                    tempo_medio=Avg('tempo_real')
                )['tempo_medio']
                estatisticas['tempo_medio'] = round(tempo_medio, 2) if tempo_medio else None
            
            # Taxa de sucesso
            concluidos = queryset.filter(status='concluido').count()
            estatisticas['taxa_sucesso'] = round((concluidos / total) * 100, 2)
        
        return Response(estatisticas)

    @action(detail=False, methods=['get'])
    def resumo_diario(self, request):
        """
        Endpoint para resumo diário dos últimos 30 dias
        GET /api/historico-rpa-filtro/resumo_diario/
        """
        from django.db.models import Count
        from django.utils import timezone
        
        # Últimos 30 dias
        data_limite = timezone.now() - timedelta(days=30)
        
        queryset = self.get_queryset().filter(criado_em__gte=data_limite)
        
        # Agrupar por data de criação
        resumo = queryset.extra(
            select={'dia': 'DATE(criado_em)'}
        ).values('dia').annotate(
            total=Count('id'),
            concluidos=Count('id', filter=Q(status='concluido')),
            falhas=Count('id', filter=Q(status='falha')),
            pendentes=Count('id', filter=Q(status='pendente')),
            processando=Count('id', filter=Q(status='processando'))
        ).order_by('-dia')
        
        return Response(list(resumo))


# Se você quiser manter a view original também, pode renomear ela
class HistoricoRPAViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet simples para listar histórico (mantém compatibilidade)"""
    permission_classes = [IsAuthenticated]
    serializer_class = RPAHistoricoSerializer
    pagination_class = HistoricoPagination

    def get_queryset(self):
        is_swagger_fake_view = getattr(self, 'swagger_fake_view', False)
        
        if is_swagger_fake_view:
            return ProcessamentoRPA.objects.none()
            
        return ProcessamentoRPA.objects.filter(
            user=self.request.user
        ).order_by('-criado_em')