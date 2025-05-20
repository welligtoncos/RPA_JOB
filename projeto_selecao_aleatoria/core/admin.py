# admin.py
# Este arquivo configura o painel administrativo Django para os modelos relacionados a processamentos RPA.
# Cada classe define como um modelo específico é exibido e gerenciado no painel admin.

from django.contrib import admin
from .models import ProcessamentoRPA, ProcessamentoRPATemplate, ResultadoProcessamento, Resultado

# Configuração do admin para ProcessamentoRPA
# Exibe e gerencia os processamentos RPA, permitindo filtrar por status, tipo e usuário
@admin.register(ProcessamentoRPA)
class ProcessamentoRPAAdmin(admin.ModelAdmin):
    # Colunas exibidas na listagem
    list_display = ('id', 'tipo', 'user', 'status', 'criado_em', 'progresso')
    
    # Filtros disponíveis na barra lateral
    list_filter = ('status', 'tipo', 'user')
    
    # Campos pesquisáveis
    search_fields = ('id', 'user__username', 'descricao')
    
    # Campos que não podem ser editados
    readonly_fields = ('id', 'criado_em', 'iniciado_em', 'concluido_em', 'tempo_real')
    
    # Navegação hierárquica por data
    date_hierarchy = 'criado_em'

# Configuração do admin para Templates de ProcessamentoRPA
# Gerencia modelos de processamento que podem ser reutilizados
@admin.register(ProcessamentoRPATemplate)
class ProcessamentoRPATemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'descricao')
    list_filter = ('tipo',)
    search_fields = ('id', 'descricao')

# Configuração do admin para ResultadoProcessamento
# Exibe e gerencia os arquivos de resultado gerados pelos processamentos
@admin.register(ResultadoProcessamento)
class ResultadoProcessamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'processamento', 'nome_arquivo', 'tipo_resultado', 'usuario', 'criado_em')
    list_filter = ('tipo_resultado', 'processamento__user', 'processamento__tipo')
    search_fields = ('nome_arquivo', 'processamento__id', 'processamento__user__username')
    readonly_fields = ('id', 'criado_em', 'tamanho_formatado')
    
    # Método para exibir o nome do usuário a partir do processamento relacionado
    def usuario(self, obj):
        return obj.processamento.user.username
    
    # Texto de cabeçalho para a coluna "usuario"
    usuario.short_description = 'Usuário'