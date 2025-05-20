import logging
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from ..models import ProcessamentoRPA, ResultadoProcessamento
from ..serializers import RPAHistoricoSerializer, RPADockerHistoricoSerializer
from .base import HistoricoPagination

User = get_user_model()
logger = logging.getLogger(__name__)

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