# core/services/s3/manager.py
"""
Gerenciador de armazenamento no Amazon S3.

Este módulo contém a classe principal para interação com o Amazon S3,
incluindo criação de diretórios e upload de arquivos.
"""

import logging
from datetime import datetime
from botocore.exceptions import ClientError

from .utils import get_s3_client, format_s3_path

logger = logging.getLogger("docker_rpa")

class S3DirectoryManager:
    """
    Gerencia diretórios S3 para resultados de seleção aleatória.
    
    Esta classe encapsula todas as operações relacionadas à interação
    com o bucket S3 para armazenamento de resultados de processamento.
    """
    
    def __init__(self, bucket_name="appbeta-user-results"):
        """
        Inicializa o gerenciador com o bucket S3 especificado.
        
        Args:
            bucket_name: Nome do bucket S3 onde os arquivos serão armazenados
        """
        self.s3_client = get_s3_client()
        self.bucket_name = bucket_name
    
    def create_user_directory_structure(self, user_id):
        """
        Cria a árvore do usuário:
          selecao_aleatoria/usuarios/{user}/
          selecao_aleatoria/usuarios/{user}/input_sa/
          selecao_aleatoria/usuarios/{user}/resultados/
        """
        user_id_str = str(user_id)
        
        # Diretório base no formato solicitado
        base_dir = f"selecao_aleatoria/usuarios/{user_id_str}/"
        input_dir  = f"{base_dir}input_sa/"
        result_dir = f"{base_dir}resultados/"
        
        # Criar diretórios
        for directory in [base_dir, input_dir, result_dir]:
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
        Cria o diretório para um processamento específico e atualiza os metadados.
        
        Args:
            processamento: Instância do modelo ProcessamentoRPA
            
        Returns:
            String com o caminho do diretório criado
            
        Raises:
            ClientError: Se ocorrer um erro ao acessar o S3
        """
        user_id_str = str(processamento.user_id)
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
            result_info['s3_directory'] = format_s3_path(self.bucket_name, process_dir)
            
            # Salvar dados atualizados
            processamento.resultado = result_info
            processamento.save(update_fields=['resultado'])
            
            logger.info(f"Diretório de processamento criado: {format_s3_path(self.bucket_name, process_dir)}")
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
            
        Returns:
            String com o caminho completo do arquivo no S3 ou None em caso de erro
            
        Effects:
            Atualiza o modelo de processamento com informações sobre o arquivo
        """
        user_id_str = str(processamento.user_id)
        process_id_str = str(processamento.id)
        
        # Caminho do arquivo no S3
        s3_key = f"selecao_aleatoria/usuarios/{user_id_str}/resultados/processamento_{process_id_str}/{file_name}"
        
        try:
            # Upload do arquivo
            self.s3_client.upload_file(
                local_file_path, 
                self.bucket_name, 
                s3_key
            )
            
            # Caminho completo S3
            s3_path = format_s3_path(self.bucket_name, s3_key)
            
            # Atualizar informações do processamento
            result_info = processamento.resultado or {}
            
            # Inicializar lista de arquivos ou adicionar a existente
            if 'arquivos' not in result_info:
                result_info['arquivos'] = []
                
            # Adicionar informações sobre o arquivo
            result_info['arquivos'].append({
                'nome': file_name,
                'caminho': s3_path,
                'data_upload': datetime.now().isoformat()
            })
            
            # Salvar dados atualizados
            processamento.resultado = result_info
            processamento.save(update_fields=['resultado'])
            
            logger.info(f"Arquivo enviado: {s3_path}")
            return s3_path
        except ClientError as e:
            logger.error(f"Erro ao enviar arquivo: {e}")
            return None
        
     # --- NOVO: detectar versionamento do bucket
    def _bucket_is_versioned(self) -> bool:
        try:
            resp = self.s3_client.get_bucket_versioning(Bucket=self.bucket_name)
            return resp.get("Status") == "Enabled"
        except ClientError as e:
            logger.warning(f"Não foi possível verificar versionamento do bucket: {e}")
            return False

    # --- NOVO: apagar tudo sob um prefixo (com paginação e batch)
    def _delete_prefix(self, prefix: str):
        versioned = self._bucket_is_versioned()
        if versioned:
            paginator = self.s3_client.get_paginator("list_object_versions")
            page_it = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            batch = []
            for page in page_it:
                for v in page.get("Versions", []):
                    batch.append({"Key": v["Key"], "VersionId": v["VersionId"]})
                    if len(batch) == 1000:
                        self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": batch})
                        batch.clear()
                for d in page.get("DeleteMarkers", []):
                    batch.append({"Key": d["Key"], "VersionId": d["VersionId"]})
                    if len(batch) == 1000:
                        self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": batch})
                        batch.clear()
            if batch:
                self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": batch})
        else:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_it = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            batch = []
            for page in page_it:
                for obj in page.get("Contents", []):
                    batch.append({"Key": obj["Key"]})
                    if len(batch) == 1000:
                        self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": batch})
                        batch.clear()
            if batch:
                self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={"Objects": batch})

        logger.info(f"Prefixo removido: s3://{self.bucket_name}/{prefix}")

    # --- NOVO: apagar toda a “pasta” do usuário (input_sa + resultados + subpastas)
    def delete_user_directory(self, user_id):
        prefix = f"selecao_aleatoria/usuarios/{user_id}/"
        try:
            self._delete_prefix(prefix)
        except ClientError as e:
            logger.error(f"Erro ao remover diretório do usuário {user_id}: {e}")
            raise

    # (opcional) apagar só um processamento específico
    def delete_process_directory(self, processamento):
        prefix = f"selecao_aleatoria/usuarios/{processamento.user_id}/resultados/processamento_{processamento.id}/"
        try:
            self._delete_prefix(prefix)
        except ClientError as e:
            logger.error(f"Erro ao remover diretório do processamento {processamento.id}: {e}")
            raise
    
    def upload_input_fileobj(self, user_id, fileobj, file_name: str, ensure_dirs: bool = True) -> str | None:
        """
        Envia um arquivo (objeto de arquivo seekable) para:
        selecao_aleatoria/usuarios/{user_id}/input_sa/{file_name}
        """
        user_id_str = str(user_id).strip()
        prefix_dir = f"selecao_aleatoria/usuarios/{user_id_str}/input_sa/"
        s3_key = f"{prefix_dir}{file_name}"

        try:
            if ensure_dirs:
                # cria "pasta" (idempotente)
                self.s3_client.put_object(Bucket=self.bucket_name, Key=prefix_dir, Body=b'')

            # garanta que o ponteiro está no início
            try:
                fileobj.seek(0)
            except Exception:
                pass

            self.s3_client.upload_fileobj(fileobj, self.bucket_name, s3_key)
            return format_s3_path(self.bucket_name, s3_key)
        except ClientError as e:
            logger.error(f"[S3 input_sa] Erro ao enviar fileobj: {e}")
            return None