import requests
import json
import time
import argparse
import os
from datetime import datetime
from tabulate import tabulate
from colorama import init, Fore, Style

# Inicializar colorama para saída colorida
init()

API_BASE_URL = "http://localhost:8000/api"

def iniciar_processamento(tipo, descricao=None):
    """Inicia um novo processamento RPA"""
    url = f"{API_BASE_URL}/rpa/"
    
    if descricao is None:
        descricao = f"Teste de {tipo} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    payload = {
        "tipo": tipo,    # ⚡ Corrigido: não tem mais tipo_selecao
        "descricao": descricao,
        "dados_entrada": {
            "teste": True,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    print(f"\n{Fore.CYAN}Iniciando processamento RPA do tipo: {Fore.YELLOW}{tipo}{Style.RESET_ALL}")
    response = requests.post(url, json=payload)
    
    if response.status_code == 201:
        data = response.json()
        processamento_id = data.get('id')
        print(f"{Fore.GREEN}Processamento iniciado com sucesso!{Style.RESET_ALL}")
        print(f"ID: {Fore.YELLOW}{processamento_id}{Style.RESET_ALL}")
        return processamento_id
    else:
        print(f"{Fore.RED}Erro ao iniciar processamento: {response.status_code}{Style.RESET_ALL}")
        print(response.text)
        return None

def monitorar_processamento(processamento_id):
    """Monitora o progresso de um processamento RPA"""
    url = f"{API_BASE_URL}/rpa/{processamento_id}/"
    concluido = False
    ultima_atualizacao = None
    
    # Para cálculo de ETA
    inicio_monitoramento = time.time()
    ultimo_progresso = 0
    taxa_progresso = 0  # progresso por segundo
    
    print(f"\n{Fore.CYAN}Monitorando processamento: {Fore.YELLOW}{processamento_id}{Style.RESET_ALL}")
    print("=" * 80)
    
    while not concluido:
        try:
            response = requests.get(url)
            data = response.json()
            
            status = data['status']
            progresso = data['progresso']
            tipo = data['tipo']
            tempo_estimado = data['tempo_estimado']
            
            # Calcular ETA
            tempo_atual = time.time()
            tempo_decorrido = tempo_atual - inicio_monitoramento
            
            if tempo_decorrido > 0 and progresso > ultimo_progresso:
                delta_progresso = progresso - ultimo_progresso
                delta_tempo = tempo_decorrido
                taxa_progresso = delta_progresso / delta_tempo
                
                if taxa_progresso > 0:
                    eta_segundos = (100 - progresso) / taxa_progresso
                    eta_str = f"{int(eta_segundos)}s"
                else:
                    eta_str = "Calculando..."
            else:
                eta_str = "Calculando..."
            
            # Atualizar último progresso
            ultimo_progresso = progresso
            inicio_monitoramento = tempo_atual
            
            # Exibir barra de progresso
            barra_tamanho = 40
            preenchido = int(barra_tamanho * progresso / 100)
            barra = '█' * preenchido + '░' * (barra_tamanho - preenchido)
            
            status_color = Fore.YELLOW
            if status == 'processando':
                status_color = Fore.BLUE
            elif status == 'concluido':
                status_color = Fore.GREEN
            elif status == 'falha':
                status_color = Fore.RED
            
            status_info = f"{status_color}{status.upper()}{Style.RESET_ALL} - {Fore.YELLOW}{tipo}{Style.RESET_ALL}"
            progresso_info = f"{Fore.GREEN}{progresso}%{Style.RESET_ALL} [{barra}] ETA: {eta_str}"
            
            if ultima_atualizacao != status_info + progresso_info:
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"\n{Fore.CYAN}Monitorando processamento: {Fore.YELLOW}{processamento_id}{Style.RESET_ALL}")
                print("=" * 80)
                print(f"Status: {status_info}")
                print(f"Progresso: {progresso_info}")
                print(f"Tempo estimado total: {tempo_estimado}s")
                print("=" * 80)
                ultima_atualizacao = status_info + progresso_info
            
            if status in ['concluido', 'falha']:
                concluido = True
                
                if status == 'concluido':
                    print(f"\n{Fore.GREEN}Processamento concluído com sucesso!{Style.RESET_ALL}")
                    print(f"Tempo real: {Fore.YELLOW}{data['tempo_real']}s{Style.RESET_ALL} (Estimado: {tempo_estimado}s)")
                    
                    resultado = data['resultado']
                    
                    # Exibir logs
                    if 'logs' in resultado:
                        print(f"\n{Fore.CYAN}Logs de execução:{Style.RESET_ALL}")
                        for log in resultado['logs']:
                            print(f"  {log}")
                    
                    # Exibir detalhes específicos
                    if 'detalhes' in resultado:
                        print(f"\n{Fore.CYAN}Detalhes do processamento:{Style.RESET_ALL}")
                        detalhes = resultado['detalhes']
                        for key, value in detalhes.items():
                            print(f"  {key}: {value}")
                else:
                    print(f"\n{Fore.RED}Processamento falhou!{Style.RESET_ALL}")
                    print(f"Erro: {Fore.RED}{data['mensagem_erro']}{Style.RESET_ALL}")
            else:
                time.sleep(1)  # Verificar a cada segundo
                
        except Exception as e:
            print(f"{Fore.RED}Erro ao monitorar: {str(e)}{Style.RESET_ALL}")
            time.sleep(2)
    
    return data

def listar_processamentos():
    """Lista todos os processamentos RPA no sistema"""
    url = f"{API_BASE_URL}/rpa/"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'results' in data:
            processamentos = data['results']
            
            if len(processamentos) == 0:
                print(f"{Fore.YELLOW}Nenhum processamento encontrado.{Style.RESET_ALL}")
                return
            
            tabela = []
            for p in processamentos:
                status_color = Fore.YELLOW
                if p['status'] == 'processando':
                    status_color = Fore.BLUE
                elif p['status'] == 'concluido':
                    status_color = Fore.GREEN
                elif p['status'] == 'falha':
                    status_color = Fore.RED
                
                status_formatado = f"{status_color}{p['status'].upper()}{Style.RESET_ALL}"
                
                tempo = p['tempo_real'] if p['tempo_real'] is not None else p['tempo_estimado']
                
                tabela.append([
                    p['id'],
                    p['tipo'],
                    status_formatado,
                    f"{p['progresso']}%",
                    tempo,
                    p['criado_em']
                ])
            
            print(tabulate(tabela, headers=["ID", "Tipo", "Status", "Progresso", "Tempo (s)", "Criado em"]))
            
        else:
            print(f"{Fore.RED}Formato de resposta inesperado.{Style.RESET_ALL}")
            
    except Exception as e:
        print(f"{Fore.RED}Erro ao listar processamentos: {str(e)}{Style.RESET_ALL}")

def reiniciar_processamento(processamento_id):
    """Reinicia um processamento existente"""
    url = f"{API_BASE_URL}/rpa/{processamento_id}/reiniciar/"
    
    try:
        print(f"\n{Fore.CYAN}Reiniciando processamento: {Fore.YELLOW}{processamento_id}{Style.RESET_ALL}")
        response = requests.post(url)
        
        if response.status_code == 200:
            print(f"{Fore.GREEN}Processamento reiniciado com sucesso!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}Erro ao reiniciar: {response.status_code}{Style.RESET_ALL}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"{Fore.RED}Erro ao reiniciar processamento: {str(e)}{Style.RESET_ALL}")
        return False

def executar_testes():
    """Executa testes em todos os tipos de processamento RPA"""
    tipos = ['planilha', 'email', 'web', 'sistema']
    resultados = []
    
    print(f"{Fore.CYAN}Iniciando testes de processamento RPA{Style.RESET_ALL}")
    print(f"Serão executados {len(tipos)} tipos diferentes de processamento")
    
    for tipo in tipos:
        print(f"\n{Fore.CYAN}======== Testando tipo: {Fore.YELLOW}{tipo}{Style.RESET_ALL} ========")
        
        # Iniciar processamento
        processamento_id = iniciar_processamento(tipo)
        
        if not processamento_id:
            print(f"{Fore.RED}Falha ao iniciar processamento do tipo {tipo}{Style.RESET_ALL}")
            continue
        
        # Monitorar processamento
        resultado = monitorar_processamento(processamento_id)
        
        # Armazenar resultado para resumo
        resultados.append({
            'id': processamento_id,
            'tipo': tipo,
            'status': resultado['status'],
            'tempo_real': resultado.get('tempo_real', 0),
            'tempo_estimado': resultado.get('tempo_estimado', 0)
        })
    
    # Exibir resumo
    print(f"\n{Fore.CYAN}======== Resumo dos Testes ========{Style.RESET_ALL}")
    tabela = []
    for r in resultados:
        status_color = Fore.GREEN if r['status'] == 'concluido' else Fore.RED
        status_formatado = f"{status_color}{r['status'].upper()}{Style.RESET_ALL}"
        
        tabela.append([
            r['tipo'],
            status_formatado,
            r['tempo_real'],
            r['tempo_estimado']
        ])
    
    print(tabulate(tabela, headers=["Tipo", "Status", "Tempo Real (s)", "Tempo Estimado (s)"]))

def main():
    parser = argparse.ArgumentParser(description='Testador de Processamento RPA')
    parser.add_argument('--listar', action='store_true', help='Listar todos os processamentos')
    parser.add_argument('--iniciar', choices=['planilha', 'email', 'web', 'sistema'], help='Iniciar um novo processamento')
    parser.add_argument('--monitorar', type=str, help='Monitorar um processamento existente (ID)')
    parser.add_argument('--reiniciar', type=str, help='Reiniciar um processamento existente (ID)')
    parser.add_argument('--teste-completo', action='store_true', help='Executar testes com todos os tipos')
    
    args = parser.parse_args()
    
    if args.listar:
        listar_processamentos()
    elif args.iniciar:
        processamento_id = iniciar_processamento(args.iniciar)
        if processamento_id:
            monitorar_processamento(processamento_id)
    elif args.monitorar:
        monitorar_processamento(args.monitorar)
    elif args.reiniciar:
        if reiniciar_processamento(args.reiniciar):
            monitorar_processamento(args.reiniciar)
    elif args.teste_completo:
        executar_testes()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()