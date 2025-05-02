# test_processamentos_api.ps1 - Script para testar a API de processamentos de usuário

# Configuração
$API_BASE = "http://localhost:8000/api"
$USER_ID = "18"
$USERNAME = "teste_4"
$PASSWORD = "@Well123"

Write-Host "============================================================="
Write-Host "   Teste da API de Processamentos - Usuário ID: $USER_ID"
Write-Host "============================================================="

# Obter um novo token JWT
Write-Host "`nObtendo token JWT..."
$tokenResponse = Invoke-RestMethod -Uri "$API_BASE/token/" -Method Post -Body @{
    username = $USERNAME
    password = $PASSWORD
} -ContentType "application/x-www-form-urlencoded"

$ACCESS_TOKEN = $tokenResponse.access
Write-Host "Token obtido com sucesso!"

# Cabeçalho para todas as requisições
$AUTH_HEADER = @{
    "Authorization" = "Bearer $ACCESS_TOKEN"
}

# Testar endpoint de listagem de processamentos
Write-Host "`n1. Listando todos os processamentos do usuário $USER_ID..."
Write-Host "-------------------------------------------------------------"
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/usuarios/$USER_ID/processamentos/" -Headers $AUTH_HEADER -Method Get
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Erro: $_"
    Write-Host $_.Exception.Response.StatusCode.value__
    Write-Host $_.ErrorDetails.Message
}

# Testar endpoint de estatísticas
Write-Host "`n2. Obtendo estatísticas dos processamentos do usuário $USER_ID..."
Write-Host "-------------------------------------------------------------"
try {
    $stats = Invoke-RestMethod -Uri "$API_BASE/usuarios/$USER_ID/processamentos/estatisticas/" -Headers $AUTH_HEADER -Method Get
    $stats | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Erro: $_"
}

# Testar endpoint de processamentos Docker
Write-Host "`n3. Listando processamentos Docker do usuário $USER_ID..."
Write-Host "-------------------------------------------------------------"
try {
    $docker = Invoke-RestMethod -Uri "$API_BASE/usuarios/$USER_ID/docker-processamentos/" -Headers $AUTH_HEADER -Method Get
    $docker | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Erro: $_"
}

# Buscar o ID do primeiro processamento retornado para testar endpoints detalhados
Write-Host "`n4. Buscando ID de um processamento para testar detalhes..."
if ($response -and $response.Count -gt 0) {
    $PROC_ID = $response[0].id
    Write-Host "Processamento encontrado: $PROC_ID"
    
    # Testar endpoint de detalhes do processamento
    Write-Host "`n5. Obtendo detalhes do processamento $PROC_ID..."
    Write-Host "-------------------------------------------------------------"
    try {
        $details = Invoke-RestMethod -Uri "$API_BASE/usuarios/$USER_ID/processamentos/$PROC_ID/" -Headers $AUTH_HEADER -Method Get
        $details | ConvertTo-Json -Depth 10
    } catch {
        Write-Host "Erro: $_"
    }
    
    # Testar endpoint de resultados do processamento
    Write-Host "`n6. Obtendo resultados do processamento $PROC_ID..."
    Write-Host "-------------------------------------------------------------"
    try {
        $results = Invoke-RestMethod -Uri "$API_BASE/usuarios/$USER_ID/processamentos/$PROC_ID/resultados/" -Headers $AUTH_HEADER -Method Get
        $results | ConvertTo-Json -Depth 10
    } catch {
        Write-Host "Erro: $_"
    }
}
else {
    Write-Host "Nenhum processamento encontrado para este usuário."
}

Write-Host "`n============================================================="
Write-Host "                Testes concluídos!"
Write-Host "============================================================="