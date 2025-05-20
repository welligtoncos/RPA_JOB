# Importações para manter compatibilidade
from .base import HistoricoPagination
from .rpa import RPAViewSet
from .docker_rpa import RPADockerViewSet, DockerHistoricoViewSet
from .historico import HistoricoRPAViewSet
from .admin import UserProcessamentoViewSet, UserDockerProcessamentoViewSet
from .download import ResultadoDownloadViewSet
from .processors.rpa_processor import RPAProcessor
from .processors.docker_processor import RPADockerProcessor

# Para compatibilidade com código antigo
__all__ = [
    'RPAProcessor', 'RPAViewSet', 'HistoricoPagination', 'HistoricoRPAViewSet',
    'RPADockerProcessor', 'RPADockerViewSet', 'DockerHistoricoViewSet',
    'UserProcessamentoViewSet', 'UserDockerProcessamentoViewSet', 
    'ResultadoDownloadViewSet'
]