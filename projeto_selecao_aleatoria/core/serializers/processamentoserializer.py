from rest_framework import serializers
from core.models import ProcessamentoRPA

class ProcessamentoRPASerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='user.username', read_only=True)
    tempo_formatado = serializers.SerializerMethodField()

    class Meta:
        model = ProcessamentoRPA
        fields = [
            'id',
            'tipo',
            'descricao',
            'status',
            'progresso',
            'criado_em',
            'iniciado_em',
            'concluido_em',
            'tempo_real',
            'tempo_formatado',
            'usuario',
        ]

    def get_tempo_formatado(self, obj):
        if obj.tempo_real is None:
            return "—"
        minutos = obj.tempo_real // 60
        segundos = obj.tempo_real % 60
        return f"{minutos}m {segundos}s" if minutos else f"{segundos}s"
