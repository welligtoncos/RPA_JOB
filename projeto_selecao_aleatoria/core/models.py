from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class ProcessamentoRPA(models.Model):
    """Modelo para processamentos de automação RPA"""
    
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
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
    
    class Meta:
        verbose_name = 'Processamento RPA'
        verbose_name_plural = 'Processamentos RPA'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.tipo} - {self.status} ({self.id})"
    
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
