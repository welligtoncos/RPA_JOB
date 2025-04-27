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

class RPAHistoricoSerializer(serializers.ModelSerializer):
    criado_em = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    concluido_em = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)
    
    class Meta:
        model = ProcessamentoRPA
        fields = [
            'id', 
            'tipo', 
            'status', 
            'progresso', 
            'criado_em', 
            'concluido_em', 
            'resultado',
            'mensagem_erro'
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        """
        Personaliza a representação dos dados para garantir 
        compatibilidade com o frontend
        """
        representation = super().to_representation(instance)
        
        # Normaliza o tipo para corresponder ao frontend
        tipos_validos = ['planilha', 'email', 'web', 'sistema']
        if representation['tipo'] not in tipos_validos:
            representation['tipo'] = 'sistema'
        
        return representation