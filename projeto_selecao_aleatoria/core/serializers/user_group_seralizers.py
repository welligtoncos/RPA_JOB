from rest_framework import serializers

class UserGroupSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    tipo_usuario = serializers.CharField(required=False, allow_null=True)
    grupos = serializers.ListField(child=serializers.CharField())
    organizacao = serializers.CharField(required=False, allow_null=True)
    is_admin = serializers.BooleanField(required=False)
    is_admin_tipo1 = serializers.BooleanField(required=False)
    is_usuario_tipo1 = serializers.BooleanField(required=False)
    email = serializers.EmailField(required=False, allow_null=True)
    is_superuser = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
