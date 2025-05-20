from rest_framework import serializers
from ..models import ProcessamentoRPA

class RPASerializer(serializers.ModelSerializer):
    """Serializer base para processamentos RPA."""
    
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

class RPACreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de processamentos RPA."""
    
    class Meta:
        model = ProcessamentoRPA
        fields = ('tipo', 'dados_entrada')
        extra_kwargs = {
            'tipo': {'default': 'docker_rpa'},
        }