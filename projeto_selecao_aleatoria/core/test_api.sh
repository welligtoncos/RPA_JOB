#!/bin/bash
# test_processamentos_api.sh - Script para testar a API de processamentos de usuário

# Configuração
API_BASE="http://localhost:8000/api"
USER_ID="18"

# Token JWT (substitua pelo seu token válido quando for executar)
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzQ2MjE3NzcwLCJpYXQiOjE3NDYyMTc0NzAsImp0aSI6IjgyZWU4MTlmNzNiNjRhNzE5NTljMDYyODhjMmExZjU2IiwidXNlcl9pZCI6MTh9.S9r4y8G1vZZmFIGIRENcWtg_Wv4qL9v17Id9SRk8KOA"

# Cabeçalho para todas as requisições
AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

echo "============================================================="
echo "   Teste da API de Processamentos - Usuário ID: $USER_ID"
echo "============================================================="

# Testar endpoint de listagem de processamentos
echo -e "\n1. Listando todos os processamentos do usuário $USER_ID..."
echo "-------------------------------------------------------------"
curl -s -H "$AUTH_HEADER" "$API_BASE/usuarios/$USER_ID/processamentos/"
echo -e "\n"

# Testar endpoint de estatísticas
echo -e "\n2. Obtendo estatísticas dos processamentos do usuário $USER_ID..."
echo "-------------------------------------------------------------"
curl -s -H "$AUTH_HEADER" "$API_BASE/usuarios/$USER_ID/processamentos/estatisticas/"
echo -e "\n"

# Testar endpoint de processamentos Docker
echo -e "\n3. Listando processamentos Docker do usuário $USER_ID..."
echo "-------------------------------------------------------------"
curl -s -H "$AUTH_HEADER" "$API_BASE/usuarios/$USER_ID/docker-processamentos/"
echo -e "\n"

# Buscar o ID do primeiro processamento retornado para testar endpoints detalhados
echo -e "\n4. Buscando ID de um processamento para testar detalhes..."
PROC_RESPONSE=$(curl -s -H "$AUTH_HEADER" "$API_BASE/usuarios/$USER_ID/processamentos/")
PROC_ID=$(echo $PROC_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -n "$PROC_ID" ]; then
    echo "Processamento encontrado: $PROC_ID"
    
    # Testar endpoint de detalhes do processamento
    echo -e "\n5. Obtendo detalhes do processamento $PROC_ID..."
    echo "-------------------------------------------------------------"
    curl -s -H "$AUTH_HEADER" "$API_BASE/usuarios/$USER_ID/processamentos/$PROC_ID/"
    echo -e "\n"
    
    # Testar endpoint de resultados do processamento
    echo -e "\n6. Obtendo resultados do processamento $PROC_ID..."
    echo "-------------------------------------------------------------"
    curl -s -H "$AUTH_HEADER" "$API_BASE/usuarios/$USER_ID/processamentos/$PROC_ID/resultados/"
    echo -e "\n"
else
    echo "Nenhum processamento encontrado para este usuário."
fi

echo -e "\n============================================================="
echo "                Testes concluídos!"
echo "============================================================="