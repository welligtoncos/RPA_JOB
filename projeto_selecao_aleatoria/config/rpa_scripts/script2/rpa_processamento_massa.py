# teste_processamento_massa.py
import subprocess
import shlex
import threading
import time
import json
import re
import concurrent.futures

class DockerRPAProcessor:
    """Classe para gerenciar RPAs Docker para processamento em massa"""
    
    def __init__(self, imagem_docker):
        self.imagem_docker = imagem_docker
        self.progresso_geral = 0
        self.itens_processados = 0
        self.total_itens = 0
        self.resultados = []
    
    def processar_lote(self, start_id, quantidade, complexidade=1):
        """Processa um lote de itens via Docker"""
        comando = f"{start_id} {quantidade} {complexidade}"
        docker_comando = f"docker run --rm {self.imagem_docker} {comando}"
        
        print(f"Executando lote {start_id}-{start_id+quantidade-1}: {docker_comando}")
        
        # Iniciar o processo Docker
        processo = subprocess.Popen(
            shlex.split(docker_comando),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Processar a saída em tempo real
        resultados_lote = []
        while True:
            output_line = processo.stdout.readline()
            if output_line == '' and processo.poll() is not None:
                break
            if output_line:
                linha = output_line.strip()
                print(f"Lote {start_id}: {linha}")
                
                # Extrair informações de progresso
                if "progresso_geral:" in linha:
                    match = re.search(r'progresso_geral:(\d+)%', linha)
                    if match:
                        progresso_lote = int(match.group(1))
                        print(f"Lote {start_id}: Progresso {progresso_lote}%")
                
                # Extrair resultados de itens individuais
                if "resultado:" in linha:
                    try:
                        resultado_json = linha.split('resultado:')[1]
                        resultado = json.loads(resultado_json)
                        resultados_lote.append(resultado)
                    except (json.JSONDecodeError, IndexError) as e:
                        print(f"Erro ao processar resultado: {e}")
        
        # Capturar erros
        erro = processo.stderr.read()
        if erro:
            print(f"Erro no lote {start_id}: {erro}")
        
        # Código de retorno
        retorno = processo.wait()
        print(f"Lote {start_id} concluído com código de retorno: {retorno}")
        
        return resultados_lote
    
    def processar_muitos(self, total_itens, itens_por_lote=10, workers=3, complexidade=1):
        """Processa muitos itens dividindo em lotes e usando múltiplos workers"""
        self.total_itens = total_itens
        
        # Calcular número de lotes
        num_lotes = (total_itens + itens_por_lote - 1) // itens_por_lote  # Arredonda para cima
        
        print(f"Iniciando processamento de {total_itens} itens em {num_lotes} lotes usando {workers} workers")
        
        # Criar os lotes
        lotes = []
        for i in range(num_lotes):
            start_id = i * itens_por_lote + 1
            quant = min(itens_por_lote, total_itens - (i * itens_por_lote))
            lotes.append((start_id, quant, complexidade))
        
        # Processar lotes em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # Mapear os lotes para a função de processamento
            future_to_lote = {executor.submit(self.processar_lote, *lote): lote for lote in lotes}
            
            # Processar os resultados conforme eles são concluídos
            for future in concurrent.futures.as_completed(future_to_lote):
                lote = future_to_lote[future]
                try:
                    resultados_lote = future.result()
                    self.resultados.extend(resultados_lote)
                    self.itens_processados += lote[1]
                    self.progresso_geral = int((self.itens_processados / self.total_itens) * 100)
                    print(f"Progresso geral: {self.progresso_geral}% ({self.itens_processados}/{self.total_itens})")
                except Exception as e:
                    print(f"Lote {lote[0]} gerou uma exceção: {e}")
        
        print("Processamento em massa concluído!")
        print(f"Total de itens processados: {self.itens_processados}")
        
        # Análise dos resultados
        sucessos = sum(1 for r in self.resultados if r.get('sucesso', False))
        falhas = len(self.resultados) - sucessos
        
        print(f"Itens processados com sucesso: {sucessos}")
        print(f"Itens com falha: {falhas}")
        
        return self.resultados

# Teste principal
if __name__ == "__main__":
    # Configurações do teste
    IMAGEM_DOCKER = "rpa-massa:1.0"
    TOTAL_ITENS = 50
    ITENS_POR_LOTE = 5
    WORKERS = 3
    COMPLEXIDADE = 0.5  # Tempo menor para teste
    
    # Criar o processador
    processador = DockerRPAProcessor(IMAGEM_DOCKER)
    
    # Iniciar o teste em thread separada para simular o comportamento do Django
    def executar_teste():
        processador.processar_muitos(
            total_itens=TOTAL_ITENS,
            itens_por_lote=ITENS_POR_LOTE,
            workers=WORKERS,
            complexidade=COMPLEXIDADE
        )
    
    # Iniciar o teste
    thread_teste = threading.Thread(target=executar_teste)
    thread_teste.start()
    
    # Simular aplicação principal continua funcionando
    for i in range(15):
        print(f"Aplicação principal continua rodando... ({i+1}/15)")
        time.sleep(2)
        print(f"Status atual: {processador.progresso_geral}% concluído")
    
    # Aguardar o término do processamento
    thread_teste.join()
    print("Teste de processamento em massa concluído!")