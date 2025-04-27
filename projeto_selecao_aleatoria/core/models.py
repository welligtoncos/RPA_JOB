from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid
import threading
import time
import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

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
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False) 
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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