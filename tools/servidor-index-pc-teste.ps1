# Servidor local de teste do Controle Catedral (Windows PowerShell, sem Python)
# Serve index-pc-teste.html, recebe POST do módulo do Holyrics e faz proxy da API.
# Para o teste no PC, configure no módulo do Holyrics: IP 127.0.0.1 e porta 8766.

$ErrorActionPreference = 'Stop'
$port = 8766
$script:LastPreviewJson = '{"available":false,"message":"Aguardando URL enviada pelo módulo do Holyrics."}'
$indexPath = Join-Path $PSScriptRoot 'index-pc-teste.html'
$crlf = [string][char]13 + [string][char]10

if (-not (Test-Path -LiteralPath $indexPath)) {
    Write-Host 'ERRO: coloque index-pc-teste.html na mesma pasta deste script.' -ForegroundColor Red
    Read-Host 'Pressione Enter para sair'
    exit 1
}

function Decode-QueryValue([string]$value) {
    return [System.Uri]::UnescapeDataString(($value -replace '\+', ' '))
}

function Parse-Query([string]$queryText) {
    $map = @{}
    $queryText = $queryText.TrimStart('?')
    if (-not $queryText) { return $map }
    foreach ($part in $queryText.Split('&')) {
        if (-not $part) { continue }
        $pair = $part.Split('=', 2)
        $key = Decode-QueryValue $pair[0]
        $value = ''
        if ($pair.Length -gt 1) { $value = Decode-QueryValue $pair[1] }
        $map[$key] = $value
    }
    return $map
}

function Read-ExactBytes($stream, [int]$count) {
    $buffer = New-Object byte[] $count
    $offset = 0
    while ($offset -lt $count) {
        $read = $stream.Read($buffer, $offset, $count - $offset)
        if ($read -le 0) { break }
        $offset += $read
    }
    if ($offset -eq $count) { return ,$buffer }
    $partial = New-Object byte[] $offset
    if ($offset -gt 0) { [Array]::Copy($buffer, $partial, $offset) }
    return ,$partial
}

function Read-HttpRequest($stream) {
    $headerMemory = New-Object System.IO.MemoryStream
    $one = New-Object byte[] 1
    $maxHeader = 16384
    while ($headerMemory.Length -lt $maxHeader) {
        $read = $stream.Read($one, 0, 1)
        if ($read -le 0) { break }
        $headerMemory.WriteByte($one[0])
        if ($headerMemory.Length -ge 4) {
            $bytes = $headerMemory.ToArray()
            $n = $bytes.Length
            if ($bytes[$n-4] -eq 13 -and $bytes[$n-3] -eq 10 -and $bytes[$n-2] -eq 13 -and $bytes[$n-1] -eq 10) { break }
        }
    }
    $headerText = [System.Text.Encoding]::ASCII.GetString($headerMemory.ToArray())
    $lines = $headerText -split $crlf
    if (-not $lines[0]) { throw 'Cabeçalho HTTP vazio.' }
    $first = $lines[0] -split ' ', 3
    if ($first.Length -lt 2) { throw 'Linha inicial HTTP inválida.' }
    $headers = @{}
    for ($i = 1; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        if (-not $line) { continue }
        $colon = $line.IndexOf(':')
        if ($colon -gt 0) { $headers[$line.Substring(0,$colon).Trim().ToLowerInvariant()] = $line.Substring($colon+1).Trim() }
    }
    $length = 0
    if ($headers.ContainsKey('content-length')) { [void][int]::TryParse($headers['content-length'], [ref]$length) }
    if ($length -lt 0 -or $length -gt 1048576) { throw 'Corpo HTTP acima do limite permitido.' }
    $bodyBytes = Read-ExactBytes $stream $length
    $body = [System.Text.Encoding]::UTF8.GetString($bodyBytes)
    $uri = [System.Uri]::new(('http://127.0.0.1' + $first[1]))
    return [pscustomobject]@{
        Method = $first[0].ToUpperInvariant()
        Target = $first[1]
        Path = $uri.AbsolutePath
        Query = (Parse-Query $uri.Query)
        Headers = $headers
        Body = $body
    }
}

function Write-HttpResponse($stream, [int]$status, [string]$reason, [string]$body, [string]$contentType = 'application/json; charset=utf-8') {
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($body)
    $headers = 'HTTP/1.1 ' + $status + ' ' + $reason + $crlf +
        'Content-Type: ' + $contentType + $crlf +
        'Content-Length: ' + $bytes.Length + $crlf +
        'Cache-Control: no-store' + $crlf +
        'Connection: close' + $crlf +
        'Access-Control-Allow-Origin: *' + $crlf +
        'Access-Control-Allow-Methods: GET, POST, OPTIONS' + $crlf +
        'Access-Control-Allow-Headers: Content-Type' + $crlf + $crlf
    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($headers)
    $stream.Write($headerBytes, 0, $headerBytes.Length)
    if ($bytes.Length -gt 0) { $stream.Write($bytes, 0, $bytes.Length) }
    $stream.Flush()
}

function Invoke-HolyricsApiProxy($request) {
    $action = $request.Path.Substring('/__proxy/api/'.Length)
    if ($action -notmatch '^[A-Za-z0-9_-]{1,80}$') {
        return @{ Status = 400; Reason = 'Bad Request'; Body = '{"status":"error","error":"Ação inválida."}' }
    }
    $hostValue = [string]$request.Query['host']
    $token = [string]$request.Query['token']
    if ($hostValue -notmatch '^[A-Za-z0-9.-]{1,253}$' -or -not $token) {
        return @{ Status = 400; Reason = 'Bad Request'; Body = '{"status":"error","error":"IP ou token inválido."}' }
    }

    $escapedToken = [System.Uri]::EscapeDataString($token)
    $url = 'http://' + $hostValue + ':4545/api/' + $action + '?token=' + $escapedToken
    $upstream = [System.Net.HttpWebRequest]::Create($url)
    $upstream.Method = 'POST'
    $upstream.ContentType = 'application/json'
    $upstream.Accept = 'application/json'
    $upstream.Timeout = 8000
    $upstream.ReadWriteTimeout = 8000
    $payload = [System.Text.Encoding]::UTF8.GetBytes($request.Body)
    $upstream.ContentLength = $payload.Length
    $outStream = $upstream.GetRequestStream()
    try { $outStream.Write($payload, 0, $payload.Length) } finally { $outStream.Dispose() }

    try {
        $response = $upstream.GetResponse()
    } catch [System.Net.WebException] {
        $response = $_.Exception.Response
        if (-not $response) { throw }
    }
    try {
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream(), [System.Text.Encoding]::UTF8)
        try { $body = $reader.ReadToEnd() } finally { $reader.Dispose() }
        $status = [int]$response.StatusCode
        $reason = $response.StatusDescription
    } finally {
        $response.Close()
    }
    return @{ Status = $status; Reason = $reason; Body = $body }
}

function Handle-Request($client) {
    $stream = $client.GetStream()
    $stream.ReadTimeout = 12000
    $stream.WriteTimeout = 12000
    try {
        $request = Read-HttpRequest $stream
        if ($request.Method -eq 'OPTIONS') {
            Write-HttpResponse $stream 204 'No Content' '' 'text/plain; charset=utf-8'
            return
        }

        if ($request.Method -eq 'POST' -and $request.Path -eq '/api/video-preview') {
            try {
                $payload = $request.Body | ConvertFrom-Json
                if (-not $payload.url -or ($payload.url -notmatch '^https?://')) {
                    Write-HttpResponse $stream 400 'Bad Request' '{"status":"error","error":"O corpo precisa conter uma URL HTTP(S)."}'
                    return
                }
                $script:LastPreviewJson = $request.Body
                Write-Host ((Get-Date -Format 'HH:mm:ss') + ' URL recebida do módulo: ' + [string]$payload.name) -ForegroundColor Green
                Write-HttpResponse $stream 200 'OK' '{"status":"ok","received":true}'
                return
            } catch {
                Write-HttpResponse $stream 400 'Bad Request' '{"status":"error","error":"JSON inválido."}'
                return
            }
        }

        if ($request.Method -eq 'GET' -and $request.Path -eq '/__receiver/video-preview/latest') {
            Write-HttpResponse $stream 200 'OK' $script:LastPreviewJson
            return
        }

        if ($request.Method -eq 'POST' -and $request.Path.StartsWith('/__proxy/api/')) {
            try {
                $result = Invoke-HolyricsApiProxy $request
                Write-HttpResponse $stream $result.Status $result.Reason $result.Body
                return
            } catch {
                Write-Host ((Get-Date -Format 'HH:mm:ss') + ' Erro no proxy da API: ' + $_.Exception.Message) -ForegroundColor Red
                Write-HttpResponse $stream 502 'Bad Gateway' '{"status":"error","error":"Falha no proxy local da API Holyrics."}'
                return
            }
        }

        if ($request.Method -eq 'GET' -and ($request.Path -eq '/' -or $request.Path -eq '/index-pc-teste.html')) {
            $html = [System.IO.File]::ReadAllText($indexPath, [System.Text.Encoding]::UTF8)
            Write-HttpResponse $stream 200 'OK' $html 'text/html; charset=utf-8'
            return
        }

        Write-HttpResponse $stream 404 'Not Found' '{"status":"error","error":"Endpoint local não encontrado."}'
    } catch {
        try { Write-HttpResponse $stream 400 'Bad Request' '{"status":"error","error":"Requisição HTTP inválida."}' } catch {}
    } finally {
        $stream.Dispose()
        $client.Close()
    }
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
try {
    $listener.Start()
} catch {
    Write-Host ('Não foi possível abrir a porta ' + $port + '. Feche outra instância do servidor e tente novamente.') -ForegroundColor Red
    Read-Host 'Pressione Enter para sair'
    exit 1
}

Write-Host ''
Write-Host 'Servidor de teste do Controle Catedral iniciado.' -ForegroundColor Cyan
Write-Host 'Página: http://127.0.0.1:8766/index-pc-teste.html'
Write-Host 'Endpoint de recebimento: http://127.0.0.1:8766/api/video-preview'
Write-Host 'No módulo Holyrics, configure IP 127.0.0.1 e porta 8766 para o teste no PC.'
Write-Host 'A API do Holyrics é consultada pela porta 4545. Mantenha esta janela aberta.'
Write-Host 'Pressione Ctrl+C para encerrar.'
Write-Host ''

Start-Process 'http://127.0.0.1:8766/index-pc-teste.html'
try {
    while ($true) {
        $client = $listener.AcceptTcpClient()
        Handle-Request $client
    }
} finally {
    $listener.Stop()
}
