# core/serializers/uploadserializer.py
from rest_framework import serializers
import os

class UploadParaInputSASerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True, help_text="ID do usuário (pasta alvo no S3).")
    file = serializers.FileField(required=True, help_text="Arquivo .xlsx para enviar.")
    filename = serializers.CharField(required=False, allow_blank=True,
                                     help_text="Nome final no S3. Se omitir, usa o nome do arquivo.")
    overwrite = serializers.BooleanField(required=False, default=False,
                                         help_text="Se True, não adiciona timestamp.")
    add_timestamp = serializers.BooleanField(required=False, default=True,
                                             help_text="Adiciona timestamp ao nome quando overwrite=False.")

    def validate_file(self, f):
        name = getattr(f, "name", "") or ""
        ext = os.path.splitext(name)[1].lower()
        if ext not in [".xlsx"]:
            raise serializers.ValidationError("Envie um arquivo .xlsx")
        # (Opcional) validar tamanho: if f.size > 20*1024*1024: ...
        return f
