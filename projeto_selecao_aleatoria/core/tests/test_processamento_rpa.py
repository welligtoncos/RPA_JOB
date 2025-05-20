from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import ProcessamentoRPA
import json
import time

class ProcessamentoRPAModelTest(TestCase):
    def test_criar_processamento(self):
        """Teste de criação de um processamento"""
        processamento = ProcessamentoRPA.objects.create(
            tipo='planilha',
            dados_entrada={'seed': 42}
        )
        self.assertEqual(processamento.status, 'pendente')
        self.assertEqual(processamento.progresso, 0)
        
    def test_ciclo_vida_processamento(self):
        """Teste do ciclo de vida de um processamento"""
        processamento = ProcessamentoRPA.objects.create(tipo='email')
        self.assertEqual(processamento.status, 'pendente')
        
        processamento.iniciar_processamento()
        self.assertEqual(processamento.status, 'processando')
        self.assertIsNotNone(processamento.iniciado_em)
        
        processamento.atualizar_progresso(50)
        self.assertEqual(processamento.progresso, 50)
        
        resultado = {'itens_processados': [1, 2, 3]}
        processamento.concluir(resultado)
        self.assertEqual(processamento.status, 'concluido')
        self.assertEqual(processamento.progresso, 100)
        self.assertEqual(processamento.resultado, resultado)
        self.assertIsNotNone(processamento.concluido_em)
        
    def test_falha_processamento(self):
        """Teste de falha em um processamento"""
        processamento = ProcessamentoRPA.objects.create(tipo='web')
        processamento.iniciar_processamento()
        processamento.falhar("Erro simulado")
        
        self.assertEqual(processamento.status, 'falha')
        self.assertEqual(processamento.mensagem_erro, "Erro simulado")
        self.assertIsNotNone(processamento.concluido_em)


class ProcessamentoRPAAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
    def test_criar_processamento_api(self):
        """Teste de criação via API"""
        data = {
            'tipo': 'planilha',
            'descricao': 'Teste via API',
            'dados_entrada': {'seed': 42}
        }
        response = self.client.post(
            '/api/processamentos/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        
        processamento_id = response.data['id']
        processamento = ProcessamentoRPA.objects.get(id=processamento_id)
        self.assertEqual(processamento.tipo, 'planilha')
        
    def test_listar_processamentos_api(self):
        """Teste de listagem de processamentos"""
        ProcessamentoRPA.objects.create(tipo='email')
        ProcessamentoRPA.objects.create(tipo='web')
        
        response = self.client.get('/api/processamentos/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_reiniciar_processamento_api(self):
        """Teste de reinício"""
        processamento = ProcessamentoRPA.objects.create(tipo='sistema')
        processamento.status = 'concluido'
        processamento.progresso = 100
        processamento.save()
        
        response = self.client.post(f'/api/processamentos/{processamento.id}/reiniciar/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        processamento.refresh_from_db()
        self.assertEqual(processamento.status, 'pendente')
        self.assertEqual(processamento.progresso, 0)
