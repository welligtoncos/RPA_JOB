import logging
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

class HistoricoPagination(PageNumberPagination):
    """Paginação para históricos de processamento."""
    page_size = 10  # Número de itens por página
    page_size_query_param = 'page_size'
    max_page_size = 100
    
# Outras classes base como mixins podem ser adicionadas aqui