# users/signals.py
import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.services.s3.manager import S3DirectoryManager

User = get_user_model()

@receiver(post_delete, sender=User)
def remover_pasta_s3_do_usuario(sender, instance, **kwargs):
    # cuidado: operação destrutiva
    bucket = os.getenv("AWS_S3_BUCKET", "appbeta-user-results")
    mgr = S3DirectoryManager(bucket_name=bucket)
    mgr.delete_user_directory(instance.id)
