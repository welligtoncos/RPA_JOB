from django.contrib import admin
from .models import ProcessamentoRPA, ProcessamentoRPATemplate, ResultadoProcessamento, Resultado

@admin.register(ProcessamentoRPA)
class ProcessamentoRPAAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'user', 'status', 'criado_em', 'progresso')
    list_filter = ('status', 'tipo', 'user')
    search_fields = ('id', 'user__username', 'descricao')
    readonly_fields = ('id', 'criado_em', 'iniciado_em', 'concluido_em', 'tempo_real')
    date_hierarchy = 'criado_em'

@admin.register(ProcessamentoRPATemplate)
class ProcessamentoRPATemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'descricao')
    list_filter = ('tipo',)
    search_fields = ('id', 'descricao')

@admin.register(ResultadoProcessamento)
class ResultadoProcessamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'processamento', 'nome_arquivo', 'tipo_resultado', 'usuario', 'criado_em')
    list_filter = ('tipo_resultado', 'processamento__user', 'processamento__tipo')
    search_fields = ('nome_arquivo', 'processamento__id', 'processamento__user__username')
    readonly_fields = ('id', 'criado_em', 'tamanho_formatado')
    
    def usuario(self, obj):
        return obj.processamento.user.username
    
    usuario.short_description = 'Usuário'