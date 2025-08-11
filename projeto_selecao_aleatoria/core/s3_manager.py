# core/s3_manager.py - Versão final (ponte)
"""
Gerencia diretórios S3 para resultados de seleção aleatória.

ATENÇÃO: Este arquivo será removido em versões futuras.
Por favor, use 'from core.services.s3 import S3DirectoryManager' em vez disto.
"""

# Agora podemos importar com segurança da nova estrutura
from core.services.s3.manager import S3DirectoryManager

# Re-exportamos a classe para manter compatibilidade com código existente
__all__ = ['S3DirectoryManager']

