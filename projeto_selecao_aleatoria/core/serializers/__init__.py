# Importações para manter compatibilidade com código existente
from .base import RPASerializer, RPACreateSerializer
from .rpa import RPAHistoricoSerializer
from .docker_rpa import (
    RPADockerSerializer, RPADockerHistoricoSerializer, RPADockerCreateSerializer
)
from .download import ResultadoDownloadSerializer

# Para compatibilidade com código antigo
__all__ = [
    'RPASerializer',
    'RPACreateSerializer',
    'RPAHistoricoSerializer',
    'RPADockerSerializer',
    'RPADockerHistoricoSerializer',
    'RPADockerCreateSerializer',
    'ResultadoDownloadSerializer',
]