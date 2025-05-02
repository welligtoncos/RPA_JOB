import boto3
import logging
from botocore.exceptions import ClientError
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

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
    
    def create_process_directory(self, user_id, process_id):
        """Cria o diretório específico para um processamento."""
        user_id_str = str(user_id)
        process_id_str = str(process_id)
        
        # Estrutura: selecao_aleatoria/usuarios/{user_id}/resultados/processamento_{process_id}/
        process_dir = f"selecao_aleatoria/usuarios/{user_id_str}/resultados/processamento_{process_id_str}/"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=process_dir,
                Body=''
            )
            logger.info(f"Diretório de processamento criado: s3://{self.bucket_name}/{process_dir}")
            return process_dir
        except ClientError as e:
            logger.error(f"Erro ao criar diretório de processamento: {e}")
            raise
    
    def upload_result_file(self, local_file_path, user_id, process_id, file_name):
        """Faz upload de um arquivo de resultado para a pasta específica."""
        user_id_str = str(user_id)
        process_id_str = str(process_id)
        
        # Caminho do arquivo no S3
        s3_key = f"selecao_aleatoria/usuarios/{user_id_str}/resultados/processamento_{process_id_str}/{file_name}"
        
        try:
            self.s3_client.upload_file(
                local_file_path, 
                self.bucket_name, 
                s3_key
            )
            logger.info(f"Arquivo enviado: s3://{self.bucket_name}/{s3_key}")
            return f"s3://{self.bucket_name}/{s3_key}"
        except ClientError as e:
            logger.error(f"Erro ao enviar arquivo: {e}")
            return None


# Sinal para criar diretório quando um usuário é criado
@receiver(post_save, sender=User)
def create_user_directory(sender, instance, created, **kwargs):
    """Cria a estrutura de diretórios quando um novo usuário é criado."""
    if created:
        try:
            s3_manager = S3DirectoryManager()
            s3_manager.create_user_directory_structure(instance.id)
            logger.info(f"Estrutura de diretórios criada para usuário ID: {instance.id}")
        except Exception as e:
            logger.error(f"Erro ao criar estrutura de diretórios: {e}")