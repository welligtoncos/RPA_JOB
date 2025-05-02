import boto3
import logging
import json
from botocore.exceptions import ClientError
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from datetime import datetime

# Logger
logger = logging.getLogger("docker_rpa")

class S3DirectoryManager:
    """Gerencia diretórios S3 para resultados de seleção aleatória."""
    
    def __init__(self, bucket_name="appbeta-user-results"):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
    
    def create_user_directory_structure(self, user_id):
        """Cria a estrutura de diretórios para um usuário."""
        user_id_str = str(user_id)
        
        # Diretório base no formato solicitado
        base_dir = f"selecao_aleatoria/usuarios/{user_id_str}/"
        result_dir = f"{base_dir}resultados/"
        
        # Criar diretórios
        for directory in [base_dir, result_dir]:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=directory,
                    Body=''
                )
                logger.info(f"Diretório criado: s3://{self.bucket_name}/{directory}")
            except ClientError as e:
                logger.error(f"Erro ao criar diretório: {e}")
                raise
        
        return base_dir
    
    def create_process_directory(self, processamento):
        """
        Cria o diretório para um processamento específico.
        
        Args:
            processamento: Instância do modelo ProcessamentoRPA
        """
        user_id_str = str(processamento.user_id)  # Corrigido para usar user_id
        process_id_str = str(processamento.id)
        
        # Diretório para este processamento específico
        process_dir = f"selecao_aleatoria/usuarios/{user_id_str}/resultados/processamento_{process_id_str}/"
        
        try:
            # Criar diretório do processamento
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=process_dir,
                Body=''
            )
            
            # Atualizar informações do processamento
            result_info = processamento.resultado or {}
            result_info['s3_directory'] = f"s3://{self.bucket_name}/{process_dir}"
            
            # Salvar dados atualizados
            processamento.resultado = result_info
            processamento.save(update_fields=['resultado'])
            
            logger.info(f"Diretório de processamento criado: s3://{self.bucket_name}/{process_dir}")
            return process_dir
        except ClientError as e:
            logger.error(f"Erro ao criar diretório de processamento: {e}")
            raise
    
    def upload_result_file(self, local_file_path, processamento, file_name):
        """
        Faz upload de um arquivo de resultado para o diretório do processamento.
        
        Args:
            local_file_path: Caminho local do arquivo
            processamento: Instância do modelo ProcessamentoRPA
            file_name: Nome do arquivo
        """
        user_id_str = str(processamento.user_id)  # Corrigido para usar user_id
        process_id_str = str(processamento.id)
        
        # Caminho do arquivo no S3
        s3_key = f"selecao_aleatoria/usuarios/{user_id_str}/resultados/processamento_{process_id_str}/{file_name}"
        
        try:
            self.s3_client.upload_file(
                local_file_path, 
                self.bucket_name, 
                s3_key
            )
            
            # Atualizar informações do processamento
            result_info = processamento.resultado or {}
            
            # Inicializar lista de arquivos ou adicionar a existente
            if 'arquivos' not in result_info:
                result_info['arquivos'] = []
                
            # Adicionar informações sobre o arquivo
            result_info['arquivos'].append({
                'nome': file_name,
                'caminho': f"s3://{self.bucket_name}/{s3_key}",
                'data_upload': datetime.now().isoformat()
            })
            
            # Salvar dados atualizados
            processamento.resultado = result_info
            processamento.save(update_fields=['resultado'])
            
            logger.info(f"Arquivo enviado: s3://{self.bucket_name}/{s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
        except ClientError as e:
            logger.error(f"Erro ao enviar arquivo: {e}")
            return None