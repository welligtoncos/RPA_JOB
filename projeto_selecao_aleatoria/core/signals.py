# core/signals.py

import logging
import boto3
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_folder(sender, instance, created, **kwargs):
    if not created:
        return

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    if not bucket:
        logger.error("AWS_STORAGE_BUCKET_NAME não está definido em settings.py")
        return

    # Prefixo / diretório baseado no ID do usuário
    prefix = f"{instance.pk}/"
    placeholder_key = prefix + ".keep"

    # Monta kwargs para boto3: região se estiver configurada
    boto3_kwargs = {}
    region = getattr(settings, "AWS_S3_REGION_NAME", None)
    if region:
        boto3_kwargs["region_name"] = region

    # Cria o client S3 usando a cadeia de credenciais padrão
    s3 = boto3.client("s3", **boto3_kwargs)

    try:
        # put_object com Body vazio cria um objeto placeholder no prefixo
        s3.put_object(Bucket=bucket, Key=placeholder_key, Body=b"")
        logger.info(
            "Diretório criado no S3: s3://%s/%s",
            bucket,
            prefix
        )
    except Exception as e:
        logger.error(
            "Falha ao criar diretório para user %s: %s",
            instance.pk,    
            e,
            exc_info=True
        )
