from rest_framework import serializers
from ..models import ProcessamentoRPA
from .base import RPASerializer

class RPAHistoricoSerializer(serializers.ModelSerializer):
    """Serializer para visualização de histórico de processamentos RPA."""
    
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