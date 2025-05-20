# models.py
# Este arquivo define os modelos de dados para o sistema de processamento RPA.
# Inclui modelos para templates, processamentos e seus resultados.

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import os
from datetime import datetime

# Obtém o modelo de usuário configurado no projeto
User = get_user_model()

class ProcessamentoRPATemplate(models.Model):
    """
    Modelo de template para processamentos de automação RPA.
    
    Permite definir modelos reutilizáveis para criação de processamentos
    com configurações pré-definidas.
    """
    
    # Opções para o status do processamento
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('falha', 'Falha'),
    )
    
    # Tipos de automação RPA suportados
    TIPO_CHOICES = (
        ('planilha', 'Processamento de Planilha'),
        ('email', 'Automação de Email'),
        ('web', 'Automação Web'),
        ('sistema', 'Interação com Sistema'),
    )
    
    # Identificador único utilizando UUID em vez de números sequenciais
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Classificação do processamento
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    
    # Descrição opcional para identificação do template
    descricao = models.CharField(max_length=200, blank=True)
    
    # Dados de configuração do template em formato JSON
    dados_entrada_template = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Template de Processamento RPA'
        verbose_name_plural = 'Templates de Processamento RPA'
    
    def __str__(self):
        return f"{self.tipo} - Template ({self.id})"
    
    def criar_processamento_para_usuario(self, user, dados_entrada=None):
        """
        Cria uma instância de ProcessamentoRPA para um usuário específico
        baseada neste template.
        
        Args:
            user: Usuário para o qual o processamento será criado
            dados_entrada: Dados específicos para este processamento (opcional)
            
        Returns:
            Instância de ProcessamentoRPA criada
        """
        # Se nenhum dado de entrada for fornecido, usa o template
        dados_entrada = dados_entrada or self.dados_entrada_template
        
        return ProcessamentoRPA.objects.create(
            user=user,
            tipo=self.tipo,
            descricao=self.descricao,
            dados_entrada=dados_entrada
        )

class ProcessamentoRPA(models.Model):
    """
    Modelo para processamentos de automação RPA específicos de usuário.
    
    Cada instância representa um processamento individual, que pode
    ser baseado em um template e pertence a um usuário específico.
    Armazena dados de entrada, resultados e informações de progresso.
    """
    
    # Opções para o status do processamento
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),      # Aguardando processamento
        ('processando', 'Processando'), # Em execução
        ('concluido', 'Concluído'),    # Processamento finalizado com sucesso
        ('falha', 'Falha'),            # Processamento encontrou erro
    )
    
    # Tipos de automação RPA suportados (expandido do template)
    TIPO_CHOICES = (
        ('planilha', 'Processamento de Planilha'),
        ('email', 'Automação de Email'),
        ('web', 'Automação Web'),
        ('sistema', 'Interação com Sistema'),
        ('docker_rpa', 'Processamento Docker RPA'),        # Execução em container Docker
        ('selecao_aleatoria', 'Seleção Aleatória'),        # Processamento específico da aplicação
    )
    
    # Identificador único
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) 
    
    # Relações com usuário e template (opcional)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processamentos')
    template = models.ForeignKey(
        ProcessamentoRPATemplate, 
        on_delete=models.SET_NULL,  # Manter processamento mesmo se template for excluído
        null=True, 
        blank=True, 
        related_name='processamentos'
    )
    
    # Características do processamento
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    descricao = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', db_index=True)
    
    # Dados de entrada e saída
    dados_entrada = models.JSONField(default=dict, blank=True)  # Configurações para o processamento
    resultado = models.JSONField(null=True, blank=True)         # Resultados do processamento
    mensagem_erro = models.TextField(blank=True, null=True)     # Mensagem em caso de falha
    
    # Controle de progresso e tempo
    progresso = models.IntegerField(default=0)                              # Percentual de conclusão (0-100)
    criado_em = models.DateTimeField(auto_now_add=True)                     # Data de criação
    iniciado_em = models.DateTimeField(null=True, blank=True)               # Data de início
    concluido_em = models.DateTimeField(null=True, blank=True)              # Data de conclusão
    tempo_estimado = models.IntegerField(default=60, help_text="Tempo estimado em segundos")
    tempo_real = models.IntegerField(null=True, blank=True, help_text="Tempo real em segundos")
    #atualizado_em = models.DateTimeField(auto_now=True, null=True)  # Temporário!

    # Campos para rastreamento de armazenamento S3
    s3_directory = models.CharField(max_length=255, blank=True, null=True, help_text="Diretório S3 para este processamento")
    
    class Meta:
        verbose_name = 'Processamento RPA'
        verbose_name_plural = 'Processamentos RPA'
        ordering = ['-criado_em']  # Mais recentes primeiro
    
    def __str__(self):
        return f"{self.tipo} - {self.status} - {self.user.username} ({self.id})"
    
    def iniciar_processamento(self):
        """
        Marca o processamento como iniciado.
        Atualiza o status e registra o momento de início.
        """
        self.status = 'processando'
        self.iniciado_em = timezone.now()
        self.save()
    
    def concluir(self, resultado):
        """
        Marca o processamento como concluído.
        
        Args:
            resultado: Dicionário com os resultados do processamento
            
        Efeitos:
            - Atualiza status, resultado e tempo de conclusão
            - Calcula o tempo real de execução
            - Cria registros de ResultadoProcessamento se aplicável
        """
        self.status = 'concluido'
        self.resultado = resultado
        self.concluido_em = timezone.now()
        self.progresso = 100
        
        # Calcula tempo de execução
        if self.iniciado_em:
            duracao = (self.concluido_em - self.iniciado_em).total_seconds()
            self.tempo_real = int(duracao)
        
        self.save()
        
        # Verifica se há resultados para associar
        if resultado and isinstance(resultado, dict):
            arquivo_resultado = resultado.get('resultado_arquivo')
            if arquivo_resultado:
                # Cria um registro de resultado associado
                ResultadoProcessamento.objects.create(
                    processamento=self,
                    nome_arquivo=arquivo_resultado,
                    caminho_s3=resultado.get('caminho_arquivo', ''),
                    tipo_resultado='arquivo_excel'
                )
    
    def falhar(self, mensagem_erro):
        """
        Marca o processamento como falha.
        
        Args:
            mensagem_erro: Descrição do erro ocorrido
            
        Efeitos:
            - Atualiza status, mensagem de erro e tempo de conclusão
            - Calcula o tempo até a falha
        """
        self.status = 'falha'
        self.mensagem_erro = mensagem_erro
        self.concluido_em = timezone.now()
        
        # Calcula tempo até falha
        if self.iniciado_em:
            duracao = (self.concluido_em - self.iniciado_em).total_seconds()
            self.tempo_real = int(duracao)
            
        self.save()
    
    def atualizar_progresso(self, progresso):
        """
        Atualiza o percentual de progresso do processamento.
        
        Args:
            progresso: Valor de 0 a 100 indicando o percentual de conclusão
        """
        self.progresso = progresso
        self.save(update_fields=['progresso'])
    
    @property
    def caminho_s3(self):
        """
        Retorna o caminho S3 baseado nas convenções do sistema.
        Segue o padrão: selecao_aleatoria/usuarios/{user_id}/resultados/processamento_{id}/
        """
        if not self.id or not self.user_id:
            return None
        
        return f"selecao_aleatoria/usuarios/{self.user_id}/resultados/processamento_{self.id}/"
    
    @property
    def resultados(self):
        """
        Retorna os resultados associados a este processamento.
        Utiliza o related_name 'resultados_associados' para acessar os objetos ResultadoProcessamento.
        """
        return self.resultados_associados.all()


class ResultadoProcessamento(models.Model):
    """
    Modelo para armazenar informações sobre resultados de processamento.
    
    Cada instância representa um arquivo ou output gerado por um ProcessamentoRPA,
    com informações sobre localização, tipo e tamanho.
    """
    
    # Tipos de resultado suportados
    TIPO_CHOICES = (
        ('arquivo_excel', 'Arquivo Excel'),
        ('arquivo_pdf', 'Arquivo PDF'),
        ('arquivo_csv', 'Arquivo CSV'),
        ('imagem', 'Imagem'),
        ('outro', 'Outro'),
    )
    
    # Identificador único
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relação com o processamento que gerou este resultado
    processamento = models.ForeignKey(
        ProcessamentoRPA, 
        on_delete=models.CASCADE, 
        related_name='resultados_associados'
    )
    
    # Informações sobre o arquivo
    nome_arquivo = models.CharField(max_length=255)
    caminho_s3 = models.CharField(max_length=500, blank=True, null=True)  # Caminho completo no S3
    arquivo_local = models.FileField(upload_to='resultados/processamentos/%Y/%m/%d/', blank=True, null=True)
    tipo_resultado = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro')
    criado_em = models.DateTimeField(auto_now_add=True)
    tamanho_bytes = models.BigIntegerField(default=0, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Resultado de Processamento'
        verbose_name_plural = 'Resultados de Processamentos'
        ordering = ['-criado_em']  # Mais recentes primeiro
    
    def __str__(self):
        return f"{self.processamento.tipo} - {self.nome_arquivo}"
    
    @property
    def extensao(self):
        """
        Retorna a extensão do arquivo.
        Extrai a extensão do nome do arquivo e converte para minúsculas.
        """
        _, ext = os.path.splitext(self.nome_arquivo)
        return ext.lower()
    
    @property
    def usuario(self):
        """
        Retorna o usuário associado ao processamento.
        Facilita o acesso ao usuário proprietário do resultado.
        """
        return self.processamento.user
    
    @property
    def tamanho_formatado(self):
        """
        Retorna o tamanho do arquivo formatado em unidades legíveis (KB, MB, GB).
        Converte o tamanho em bytes para a unidade mais apropriada.
        """
        if not self.tamanho_bytes:
            return "Desconhecido"
        
        # Converter bytes para KB, MB, etc.
        bytes = self.tamanho_bytes
        if bytes < 1024:
            return f"{bytes} bytes"
        elif bytes < 1024 * 1024:
            return f"{bytes/1024:.1f} KB"
        elif bytes < 1024 * 1024 * 1024:
            return f"{bytes/(1024*1024):.1f} MB"
        else:
            return f"{bytes/(1024*1024*1024):.1f} GB"


# Modelo antigo para compatibilidade, pode ser removido após migração
class Resultado(models.Model):
    """
    Modelo antigo para resultados de processamento.
    Mantido temporariamente para compatibilidade com código existente.
    Deve ser removido após completa migração para ResultadoProcessamento.
    """
    user_id = models.CharField(max_length=50)
    arquivo = models.FileField(upload_to='resultados/%Y/%m/%d/')

    def __str__(self):
        return f"{self.user_id} – {self.arquivo.name}"