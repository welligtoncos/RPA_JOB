# teste_rpa_docker.py
import subprocess
import shlex
import threading
import time

def executar_docker_rpa():
    """Função para testar a execução do RPA via Docker"""
    
    # Parâmetros do teste
    imagem_docker = "rpa-test:1.0"
    comando = "10"  # Executar 10 passos
    
    # Comando Docker completo
    docker_comando = f"docker run --rm {imagem_docker} {comando}"
    print(f"Executando: {docker_comando}")
    
    # Iniciar o processo
    processo = subprocess.Popen(
        shlex.split(docker_comando),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Monitorar a saída em tempo real
    while True:
        output_line = processo.stdout.readline()
        if output_line == '' and processo.poll() is not None:
            break
        if output_line:
            linha = output_line.strip()
            print(f"Saída: {linha}")
            
            # Capturar progresso
            if "progresso:" in linha.lower():
                try:
                    valor_progresso = int(linha.split(':')[1].strip().replace('%', ''))
                    print(f"Progresso capturado: {valor_progresso}%")
                except (ValueError, IndexError):
                    pass
    
    # Capturar erros
    erro = processo.stderr.read()
    if erro:
        print(f"Erro: {erro}")
    
    # Código de retorno
    retorno = processo.wait()
    print(f"Processo concluído com código de retorno: {retorno}")
    
    return retorno

# Executar o teste em uma thread para simular o comportamento do Django
def teste_thread():
    print("Iniciando teste em thread...")
    thread = threading.Thread(target=executar_docker_rpa)
    thread.start()
    
    # Simular outras operações enquanto o Docker executa
    for i in range(5):
        print(f"Aplicação principal continua rodando... ({i+1}/5)")
        time.sleep(2)
    
    # Aguardar a thread terminar
    thread.join()
    print("Teste concluído!")

# Executar o teste
if __name__ == "__main__":
    teste_thread()