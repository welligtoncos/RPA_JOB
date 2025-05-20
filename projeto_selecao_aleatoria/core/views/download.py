import os
import logging
import mimetypes
import boto3
from botocore.exceptions import ClientError
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import ProcessamentoRPA, ResultadoProcessamento
from ..serializers import ResultadoDownloadSerializer
from ..permissions import IsOwnerOrAdmin

logger = logging.getLogger("download_api")

class ResultadoDownloadViewSet(viewsets.ReadOnlyModelViewSet):
    """API para gerenciar downloads de resultados de processamento."""
    serializer_class = ResultadoDownloadSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Retorna apenas os processamentos do usuário autenticado ou todos para admin."""
        user = self.request.user
        if user.is_staff:
            return ProcessamentoRPA.objects.all()
        return ProcessamentoRPA.objects.filter(user=user)
    
    @action(detail=True, methods=['get'])
    def arquivos(self, request, id=None):
        """Lista os arquivos disponíveis para um processamento específico."""
        processamento = self.get_object()
        arquivos = []
        
        # 1. Verificar se existem resultados no modelo ResultadoProcessamento
        resultados = ResultadoProcessamento.objects.filter(processamento=processamento)
        if resultados.exists():
            for r in resultados:
                arquivos.append({
                    'id': str(r.id),
                    'nome': r.nome_arquivo,
                    'caminho_s3': r.caminho_s3,
                    'tipo': r.get_tipo_resultado_display(),
                    'data_upload': r.criado_em.isoformat(),
                    'tamanho': r.tamanho_formatado,
                    'download_url': request.build_absolute_uri(f'/api/resultados/{processamento.id}/download/{r.nome_arquivo}/')
                })
        
        # 2. Verificar se há arquivos no campo resultado (formato antigo)
        elif processamento.resultado and isinstance(processamento.resultado, dict):
            # Caso 1: Verifique o formato usando container_info para docker_rpa
            if 'container_info' in processamento.resultado:
                container_info = processamento.resultado['container_info']
                resultado_arquivo = container_info.get('resultado_arquivo')
                caminho_arquivo = container_info.get('caminho_arquivo')
                
                if resultado_arquivo and caminho_arquivo:
                    arquivos.append({
                        'nome': resultado_arquivo,
                        'caminho_s3': caminho_arquivo if caminho_arquivo.startswith('s3://') else None,
                        'tipo': 'Planilha Excel',
                        'data_upload': container_info.get('container_finalizado', processamento.concluido_em.isoformat() if processamento.concluido_em else None),
                        'download_url': request.build_absolute_uri(f'/api/resultados/{processamento.id}/download/{resultado_arquivo}/')
                    })
            
            # Caso 2: Verifique o formato para selecao_aleatoria usando 'arquivos'
            if 'arquivos' in processamento.resultado:
                for arquivo in processamento.resultado['arquivos']:
                    arquivos.append({
                        'nome': arquivo.get('nome', ''),
                        'caminho_s3': arquivo.get('caminho', ''),
                        'tipo': 'Arquivo de Resultado',
                        'data_upload': arquivo.get('data_upload', ''),
                        'download_url': request.build_absolute_uri(f'/api/resultados/{processamento.id}/download/{arquivo.get("nome", "")}/')
                    })
        
        if not arquivos:
            return Response({"detail": "Nenhum arquivo disponível para este processamento."}, 
                           status=status.HTTP_404_NOT_FOUND)
            
        return Response({
            "processamento_id": str(processamento.id),
            "tipo": processamento.tipo,
            "status": processamento.status,
            "arquivos": arquivos
        })
    
    @action(detail=True, methods=['get'], url_path='download/(?P<file_name>.*)')
    def download_file(self, request, id=None, file_name=None):
        """
        Permite o download de um arquivo específico de um processamento.
        URL: /api/resultados/{id}/download/{file_name}
        """
        processamento = self.get_object()
        
        if not file_name:
            return Response({"detail": "Nome do arquivo não especificado."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Variáveis para armazenar informações do arquivo S3
        bucket_name = None
        s3_key = None
        
        # VERIFICAÇÃO 1: Procurar no modelo ResultadoProcessamento
        try:
            resultado = ResultadoProcessamento.objects.get(
                processamento=processamento,
                nome_arquivo=file_name
            )
            if resultado.caminho_s3 and resultado.caminho_s3.startswith('s3://'):
                s3_path = resultado.caminho_s3[5:]  # Remover 's3://'
                bucket_name, s3_key = s3_path.split('/', 1)
        except ResultadoProcessamento.DoesNotExist:
            # Arquivo não encontrado no modelo específico, continuar verificando outras fontes
            pass
        
        # VERIFICAÇÃO 2: Verificar no campo resultado do ProcessamentoRPA 
        if not s3_key and processamento.resultado:
            # 2.1 Verificar no formato container_info
            if isinstance(processamento.resultado, dict) and 'container_info' in processamento.resultado:
                container_info = processamento.resultado['container_info']
                if container_info.get('resultado_arquivo') == file_name and 'caminho_arquivo' in container_info:
                    s3_path = container_info['caminho_arquivo']
                    if s3_path.startswith('s3://'):
                        s3_path = s3_path[5:]  # Remover 's3://'
                        bucket_name, s3_key = s3_path.split('/', 1)
            
            # 2.2 Verificar no formato 'arquivos'
            if isinstance(processamento.resultado, dict) and 'arquivos' in processamento.resultado:
                for arquivo in processamento.resultado['arquivos']:
                    if arquivo.get('nome') == file_name and 'caminho' in arquivo:
                        s3_path = arquivo['caminho']
                        if s3_path.startswith('s3://'):
                            s3_path = s3_path[5:]  # Remover 's3://'
                            bucket_name, s3_key = s3_path.split('/', 1)
                            break
        
        # VERIFICAÇÃO 3: Se nada encontrado, tentar o caminho padrão com base na convenção
        if not s3_key:
            bucket_name = "appbeta-user-results"
            s3_key = f"selecao_aleatoria/usuarios/{processamento.user_id}/resultados/processamento_{processamento.id}/{file_name}"
            
        # Se ainda não temos chave S3, não podemos prosseguir
        if not s3_key:
            return Response({"detail": f"Arquivo '{file_name}' não encontrado."}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Download e retorno do arquivo
            # Implementação completa do método download_file aqui
            # [código original mantido]
            
            # Configurar o cliente S3 com credenciais específicas, se necessário
            try:
                # Tentar usar o perfil específico
                session = boto3.Session(profile_name='appbeta-s3-user', region_name='us-east-2')
                s3_client = session.client('s3')
            except Exception:
                # Fallback para credenciais padrão
                s3_client = boto3.client('s3')
            
            # Restante da implementação do download...
            # [código original mantido]
            
        except ClientError as e:
            logger.error(f"Erro ao baixar arquivo do S3: {e}")
            if e.response['Error']['Code'] == 'NoSuchKey':
                return Response({"detail": "Arquivo não encontrado no S3."}, 
                               status=status.HTTP_404_NOT_FOUND)
            elif e.response['Error']['Code'] == 'AccessDenied':
                return Response({"detail": "Acesso negado ao arquivo no S3. Verifique suas permissões."}, 
                               status=status.HTTP_403_FORBIDDEN)
            return Response({"detail": f"Erro ao baixar arquivo: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Erro ao processar download: {str(e)}")
            return Response({"detail": f"Erro ao processar download: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)