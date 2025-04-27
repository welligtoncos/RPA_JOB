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
    

# Adicione ao arquivo serializers.py 
class RPADockerSerializer(serializers.ModelSerializer):
    imagem_docker = serializers.CharField(max_length=255)
    comando = serializers.CharField(max_length=1000, required=False, default="")
    
    class Meta:
        model = ProcessamentoRPA
        fields = ['imagem_docker', 'comando']
        
    def create(self, validated_data):
        # Extrair campos específicos
        imagem_docker = validated_data.pop('imagem_docker')
        comando = validated_data.pop('comando', "")
        
        # Criar parâmetros
        parametros = {
            'imagem_docker': imagem_docker,
            'comando': comando
        }
        
        return ProcessamentoRPA.objects.create(
            tipo='docker_rpa',
            parametros=parametros,
            **validated_data
        )

class RPADockerHistoricoSerializer(serializers.ModelSerializer):
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