from rest_framework import serializers
from ..models import ProcessamentoRPA

class RPADockerSerializer(serializers.ModelSerializer):
    """Serializer para visualização de processamentos Docker RPA."""
    
    tipo = serializers.CharField(read_only=True, default='docker_rpa')
    parametros = serializers.JSONField(write_only=True)

    class Meta:
        model = ProcessamentoRPA
        fields = ['tipo', 'parametros']

    def create(self, validated_data):
        # Tira 'parametros' do payload e joga em 'dados_entrada'
        params = validated_data.pop('parametros', {})
        validated_data['dados_entrada'] = params
        # 'tipo' já foi preenchido com default acima
        return super().create(validated_data)

class RPADockerHistoricoSerializer(serializers.ModelSerializer):
    """Serializer para visualização do histórico de processamentos Docker RPA."""
    
    container_id = serializers.SerializerMethodField()
    imagem = serializers.SerializerMethodField()
    tempo_execucao = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessamentoRPA
        fields = [
            'id', 
            'tipo', 
            'status', 
            'progresso', 
            'criado_em', 
            'concluido_em',
            'container_id',
            'imagem',
            'tempo_execucao',
            'resultado',
            'mensagem_erro'
        ]
        read_only_fields = fields
    
    def get_container_id(self, obj):
        if obj.resultado and isinstance(obj.resultado, dict) and 'container_info' in obj.resultado:
            return obj.resultado['container_info'].get('container_id', 'N/A')
        return 'N/A'
    
    def get_imagem(self, obj):
        if obj.resultado and isinstance(obj.resultado, dict) and 'container_info' in obj.resultado:
            return obj.resultado['container_info'].get('imagem', 'N/A')
        return 'N/A'
    
    def get_tempo_execucao(self, obj):
        if obj.resultado and isinstance(obj.resultado, dict) and 'container_info' in obj.resultado:
            return obj.resultado['container_info'].get('duracao_segundos', 0)
        return 0

class RPADockerCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de processamentos Docker RPA."""
    
    # preenche automaticamente o tipo como 'docker_rpa'
    tipo = serializers.HiddenField(default='docker_rpa')
    # usa o mesmo nome do model
    dados_entrada = serializers.JSONField()

    class Meta:
        model = ProcessamentoRPA
        fields = ['tipo', 'dados_entrada']