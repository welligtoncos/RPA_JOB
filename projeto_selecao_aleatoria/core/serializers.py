# serializers.py
from rest_framework import serializers
from .models import ProcessamentoRPA

class RPACreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessamentoRPA
        fields = [
            'id', 
            'tipo', 
            'descricao', 
            'dados_entrada'
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'descricao': {'required': False},
            'dados_entrada': {'required': False}
        }

    def validate_tipo(self, value):
        # Validar se o tipo é um dos permitidos
        tipos_validos = ['planilha', 'email', 'web', 'sistema']
        if value not in tipos_validos:
            raise serializers.ValidationError(f"Tipo inválido. Escolha entre: {', '.join(tipos_validos)}")
        return value

class RPASerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessamentoRPA
        fields = [
            'id', 
            'tipo', 
            'status', 
            'progresso', 
            'criado_em', 
            'iniciado_em', 
            'concluido_em',
            'descricao',
            'resultado'
        ]
        read_only_fields = [
            'id', 
            'status', 
            'progresso', 
            'criado_em', 
            'iniciado_em', 
            'concluido_em',
            'resultado'
        ]