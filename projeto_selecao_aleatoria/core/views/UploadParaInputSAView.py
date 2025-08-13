# core/api/views.py
import os
import logging 
import tempfile 
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.services.s3.manager import S3DirectoryManager
from core.serializers.UploadParaInputSASerializer import UploadParaInputSASerializer 
logger = logging.getLogger("docker_rpa")

def _safe_filename(original: str) -> str:
    base = os.path.basename(original or "arquivo.xlsx")
    return base.replace("\\", "_").replace("/", "_")

class UploadParaInputSAView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Upload de .xlsx para input_sa do usuário",
        request_body=UploadParaInputSASerializer,
        responses={201: openapi.Response("Sucesso")},
        consumes=['multipart/form-data'],
        tags=["S3"]
    )
    def post(self, request):
        ser = UploadParaInputSASerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        up_file = ser.validated_data["file"]
        filename = _safe_filename(ser.validated_data.get("filename") or getattr(up_file, "name", "arquivo.xlsx"))

        user_id = str(ser.validated_data["user_id"])  # obrigatório
        overwrite = ser.validated_data.get("overwrite", False)
        add_ts = ser.validated_data.get("add_timestamp", True)

        if not overwrite and add_ts:
            name, ext = os.path.splitext(filename)
            from datetime import datetime
            filename = f"{name}__{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

        s3_manager = S3DirectoryManager(bucket_name="appbeta-user-results")

        # Escreve em arquivo temporário, fecha, reabre em 'rb' (seekable)
        tmp_path = None
        try:
            # delete=False por causa do Windows lock
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
                for chunk in up_file.chunks():
                    tmp.write(chunk)

            with open(tmp_path, "rb") as f:  # seekable
                s3_path = s3_manager.upload_input_fileobj(
                    user_id=user_id,
                    fileobj=f,
                    file_name=filename,
                    ensure_dirs=True
                )
        except Exception as e:
            logger.exception("Falha no upload para input_sa")
            return Response({"detail": f"Erro no upload: {e}"}, status=status.HTTP_502_BAD_GATEWAY)
        finally:
            # limpa o temp
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        if not s3_path:
            return Response({"detail": "Não foi possível enviar o arquivo ao S3."},
                            status=status.HTTP_502_BAD_GATEWAY)

        s3_key = f"selecao_aleatoria/usuarios/{user_id}/input_sa/{filename}"
        return Response({
            "bucket": s3_manager.bucket_name,
            "s3_key": s3_key,
            "s3_path": s3_path,
            "filename": filename,
            "user_id": user_id,
        }, status=status.HTTP_201_CREATED)