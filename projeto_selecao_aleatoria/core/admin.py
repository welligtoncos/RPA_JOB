# Se você apenas tem ProcessamentoRPA no seu models.py
from django.contrib import admin
from .models import ProcessamentoRPA

@admin.register(ProcessamentoRPA)
class ProcessamentoRPAAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'status', 'progresso', 'tempo_estimado', 'tempo_real', 'criado_em')
    list_filter = ('status', 'tipo')
    search_fields = ('id', 'descricao')
    readonly_fields = ('id', 'criado_em', 'iniciado_em', 'concluido_em', 'tempo_real')
    fieldsets = (
        (None, {
            'fields': ('id', 'tipo', 'descricao', 'status', 'progresso')
        }),
        ('Tempos', {
            'fields': ('tempo_estimado', 'tempo_real', 'criado_em', 'iniciado_em', 'concluido_em')
        }),
        ('Dados', {
            'fields': ('dados_entrada', 'resultado', 'mensagem_erro')
        }),
    )