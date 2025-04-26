# core/serializers.py

from rest_framework import serializers
from .models import ProcessamentoRPA

class RPASerializer(serializers.ModelSerializer):
    """Serializador completo para o modelo ProcessamentoRPA"""

    class Meta:
        model = ProcessamentoRPA
        fields = '__all__'
        read_only_fields = [
            'id', 'status', 'resultado', 'mensagem_erro',
            'progresso', 'criado_em', 'iniciado_em', 'concluido_em',
            'tempo_real', 'user'  # ✅ deixa user como somente leitura!
        ]

class RPACreateSerializer(serializers.ModelSerializer):
    """Serializador para criação de novos processamentos RPA"""

    class Meta:
        model = ProcessamentoRPA
        fields = ['tipo', 'descricao', 'dados_entrada']

    def validate_tipo(self, value):
        """Valida se o tipo enviado é válido"""
        valid_tipos = dict(ProcessamentoRPA.TIPO_CHOICES).keys()
        if value not in valid_tipos:
            raise serializers.ValidationError(
                f"Tipo deve ser um dos seguintes: {', '.join(valid_tipos)}"
            )
        return value
