from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import os
from datetime import datetime

User = get_user_model()

class ProcessamentoRPATemplate(models.Model):
    """Modelo de template para processamentos de automação RPA"""
    
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('falha', 'Falha'),
    )
    
    TIPO_CHOICES = (
        ('planilha', 'Processamento de Planilha'),
        ('email', 'Automação de Email'),
        ('web', 'Automação Web'),
        ('sistema', 'Interação com Sistema'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    descricao = models.CharField(max_length=200, blank=True)
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
    """Modelo para processamentos de automação RPA específicos de usuário"""
    
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('falha', 'Falha'),
    )
    
    TIPO_CHOICES = (
        ('planilha', 'Processamento de Planilha'),
        ('email', 'Automação de Email'),
        ('web', 'Automação Web'),
        ('sistema', 'Interação com Sistema'),
        ('docker_rpa', 'Processamento Docker RPA'),
        ('selecao_aleatoria', 'Seleção Aleatória'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) 
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processamentos')
    template = models.ForeignKey(
        ProcessamentoRPATemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processamentos'
    )
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    descricao = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', db_index=True)
    dados_entrada = models.JSONField(default=dict, blank=True)
    resultado = models.JSONField(null=True, blank=True)
    mensagem_erro = models.TextField(blank=True, null=True)
    progresso = models.IntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    tempo_estimado = models.IntegerField(default=60, help_text="Tempo estimado em segundos")
    tempo_real = models.IntegerField(null=True, blank=True, help_text="Tempo real em segundos")
    #atualizado_em = models.DateTimeField(auto_now=True, null=True)  # Temporário!

    # Campos para rastreamento de armazenamento S3
    s3_directory = models.CharField(max_length=255, blank=True, null=True, help_text="Diretório S3 para este processamento")
    
    class Meta:
        verbose_name = 'Processamento RPA'
        verbose_name_plural = 'Processamentos RPA'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.tipo} - {self.status} - {self.user.username} ({self.id})"
    
    def iniciar_processamento(self):
        """Inicia o processamento"""
        self.status = 'processando'
        self.iniciado_em = timezone.now()
        self.save()
    
    def concluir(self, resultado):
        """Marca como concluído"""
        self.status = 'concluido'
        self.resultado = resultado
        self.concluido_em = timezone.now()
        self.progresso = 100
        
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
        """Marca como falha"""
        self.status = 'falha'
        self.mensagem_erro = mensagem_erro
        self.concluido_em = timezone.now()
        
        if self.iniciado_em:
            duracao = (self.concluido_em - self.iniciado_em).total_seconds()
            self.tempo_real = int(duracao)
            
        self.save()
    
    def atualizar_progresso(self, progresso):
        """Atualiza o progresso"""
        self.progresso = progresso
        self.save(update_fields=['progresso'])
    
    @property
    def caminho_s3(self):
        """Retorna o caminho S3 baseado nas convenções do sistema"""
        if not self.id or not self.user_id:
            return None
        
        return f"selecao_aleatoria/usuarios/{self.user_id}/resultados/processamento_{self.id}/"
    
    @property
    def resultados(self):
        """Retorna os resultados associados a este processamento"""
        return self.resultados_associados.all()


class ResultadoProcessamento(models.Model):
    """Modelo para armazenar informações sobre resultados de processamento"""
    
    TIPO_CHOICES = (
        ('arquivo_excel', 'Arquivo Excel'),
        ('arquivo_pdf', 'Arquivo PDF'),
        ('arquivo_csv', 'Arquivo CSV'),
        ('imagem', 'Imagem'),
        ('outro', 'Outro'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    processamento = models.ForeignKey(
        ProcessamentoRPA, 
        on_delete=models.CASCADE, 
        related_name='resultados_associados'
    )
    nome_arquivo = models.CharField(max_length=255)
    caminho_s3 = models.CharField(max_length=500, blank=True, null=True)
    arquivo_local = models.FileField(upload_to='resultados/processamentos/%Y/%m/%d/', blank=True, null=True)
    tipo_resultado = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro')
    criado_em = models.DateTimeField(auto_now_add=True)
    tamanho_bytes = models.BigIntegerField(default=0, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Resultado de Processamento'
        verbose_name_plural = 'Resultados de Processamentos'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.processamento.tipo} - {self.nome_arquivo}"
    
    @property
    def extensao(self):
        """Retorna a extensão do arquivo"""
        _, ext = os.path.splitext(self.nome_arquivo)
        return ext.lower()
    
    @property
    def usuario(self):
        """Retorna o usuário associado ao processamento"""
        return self.processamento.user
    
    @property
    def tamanho_formatado(self):
        """Retorna o tamanho do arquivo formatado"""
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
    user_id = models.CharField(max_length=50)
    arquivo = models.FileField(upload_to='resultados/%Y/%m/%d/')

    def __str__(self):
        return f"{self.user_id} – {self.arquivo.name}"