from rest_framework import serializers
from ..models import ProcessamentoRPA, ResultadoProcessamento

class ResultadoDownloadSerializer(serializers.ModelSerializer):
    """Serializer para downloads de resultados."""
    
    arquivos_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessamentoRPA
        fields = ['id', 'tipo', 'status', 'criado_em', 'concluido_em', 'arquivos_count']
        read_only_fields = fields
    
    def get_arquivos_count(self, obj):
        """Retorna o número de arquivos disponíveis para este processamento."""
        # Verificar contagem no modelo ResultadoProcessamento
        count_resultados = ResultadoProcessamento.objects.filter(processamento=obj).count()
        if count_resultados > 0:
            return count_resultados
        
        # Verificar formato baseado em container_info
        if obj.resultado and isinstance(obj.resultado, dict):
            if 'container_info' in obj.resultado:
                container_info = obj.resultado['container_info']
                if container_info.get('resultado_arquivo'):
                    return 1
            
            # Verificar formato baseado em 'arquivos'
            if 'arquivos' in obj.resultado:
                return len(obj.resultado['arquivos'])
        
        return 0