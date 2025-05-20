# core/services/s3/utils.py
"""
Utilitários para interação com o Amazon S3.

Este módulo contém funções auxiliares para facilitar o trabalho com o S3,
fornecendo métodos para obter clientes, formatar caminhos e outras operações comuns.
"""

import boto3
import os
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger("docker_rpa")

def get_s3_client(profile_name=None, region_name='us-east-2'):
    """
    Cria um cliente S3 com as credenciais apropriadas.
    
    Args:
        profile_name: Nome do perfil AWS (opcional)
        region_name: Nome da região AWS (padrão: us-east-2)
        
    Returns:
        Um cliente boto3 S3 configurado
        
    Raises:
        Exception: Se ocorrer um erro ao criar o cliente
    """
    try:
        if profile_name:
            # Usar perfil específico
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
            return session.client('s3')
        else:
            # Usar credenciais padrão
            return boto3.client('s3', region_name=region_name)
    except Exception as e:
        logger.error(f"Erro ao criar cliente S3: {e}")
        # Fallback para cliente básico em caso de erro
        return boto3.client('s3')

def format_s3_path(bucket, key):
    """
    Formata um caminho S3 no padrão s3://bucket/key.
    
    Args:
        bucket: Nome do bucket
        key: Chave/caminho do objeto
        
    Returns:
        String formatada como s3://bucket/key
    """
    return f"s3://{bucket}/{key}"

def parse_s3_path(s3_path):
    """
    Analisa um caminho S3 no formato s3://bucket/key.
    
    Args:
        s3_path: String no formato s3://bucket/key
        
    Returns:
        Tupla (bucket, key) ou None se o formato for inválido
    """
    if not s3_path or not s3_path.startswith('s3://'):
        return None
    
    # Remove o prefixo 's3://'
    s3_path = s3_path[5:]
    
    # Divide em bucket e key
    parts = s3_path.split('/', 1)
    if len(parts) < 2:
        return (parts[0], '')
    
    return (parts[0], parts[1])

def check_file_exists(bucket, key):
    """
    Verifica se um arquivo existe no S3.
    
    Args:
        bucket: Nome do bucket
        key: Chave/caminho do objeto
        
    Returns:
        Boolean indicando se o arquivo existe
    """
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        # Se o erro for 404, o arquivo não existe
        if e.response['Error']['Code'] == '404':
            return False
        # Outros erros
        logger.error(f"Erro ao verificar arquivo: {e}")
        return False