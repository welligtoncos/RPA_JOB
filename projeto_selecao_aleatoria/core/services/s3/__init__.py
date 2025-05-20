# core/services/s3/__init__.py
"""
Pacote para interação com o Amazon S3.
"""

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
import logging

# Importação correta - use o caminho relativo
from .manager import S3DirectoryManager

logger = logging.getLogger("docker_rpa")

# Exporta classes importantes para facilitar importações
__all__ = ['S3DirectoryManager']

@receiver(post_save, sender=User)
def create_user_s3_directories(sender, instance, created, **kwargs):
    """Cria diretórios S3 quando um novo usuário é criado."""
    if created:
        try:
            manager = S3DirectoryManager()
            manager.create_user_directory_structure(instance.id)
            logger.info(f"Estrutura S3 criada para usuário {instance.username} (ID: {instance.id})")
        except Exception as e:
            logger.error(f"Erro ao criar diretórios S3 para usuário {instance.username}: {e}")