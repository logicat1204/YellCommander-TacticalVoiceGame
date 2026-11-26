param([switch]$Postura, [switch]$SoloServicio, [switch]$Gemma2, [switch]$Gemma4, [switch]$VozCPU,
      [switch]$Detener, [switch]$CerrarLMStudio,
      [ValidateRange(0,32)][int]$CapasGPU = 15,
      [ValidateRange(1,65535)][int]$PuertoServicio = 18766,
      [string]$UnrealEditor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe')
$ErrorActionPreference = 'Stop'
if ($Gemma2 -and $Gemma4) { throw 'Elige un solo modelo de charla.' }
if ($CerrarLMStudio -and !$Detener) { throw 'Usa -CerrarLMStudio junto a -Detener.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $root '.venv-decision/Scripts/python.exe'
$logs = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$runtime = Join-Path $PSScriptRoot '.runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
$sessionPath = Join-Path $runtime "sesion-$PuertoServicio.lock"

function Test-SessionActive {
    try {
        $probe = [IO.File]::Open($sessionPath, 'Open', 'ReadWrite', 'None')
        $probe.Dispose()
        return $false
    } catch [IO.FileNotFoundException] {
        return $false
    } catch [IO.IOException] {
        return $true
    }
}

function Get-SessionToken {
    $stream = [IO.File]::Open($sessionPath, 'Open', 'Read', 'ReadWrite')
    $reader = [IO.StreamReader]::new($stream)
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Stop-LMStudioServer {
    if (!(Get-Command lms -ErrorAction SilentlyContinue)) { throw 'No se encuentra la CLI lms de LM Studio.' }
    $status = & lms server status --json
    if ($LASTEXITCODE) { throw 'No se pudo consultar el servidor de LM Studio.' }
    $server = $status | ConvertFrom-Json
    if (!$server.running) { return }
    try {
        $models = Invoke-RestMethod "http://127.0.0.1:$($server.port)/v1/models" -TimeoutSec 3
        if ('yell-gemma' -in @($models.data.id)) {
            & lms unload yell-gemma
            if ($LASTEXITCODE) { Write-Warning 'No se pudo descargar yell-gemma.' }
        }
    } catch {
        Write-Warning "No se pudo consultar el modelo de LM Studio. $($_.Exception.Message)"
    }
    & lms server stop
    if ($LASTEXITCODE) { throw 'No se pudo detener el servidor de LM Studio.' }
}

if ($Detener) {
    if (Test-SessionActive) {
        $token = Get-SessionToken
        if ($token -notmatch '^[a-f0-9]{32}$') { throw 'El lanzador está iniciando. Intenta detenerlo de nuevo.' }
        [IO.File]::WriteAllText((Join-Path $runtime "detener-$token"), '')
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        while ((Test-SessionActive) -and (Get-SessionToken) -eq $token) {
            if ([DateTime]::UtcNow -ge $deadline) { throw 'El cierre quedó solicitado. Revisa la consola del lanzador.' }
            Start-Sleep -Milliseconds 200
        }
        Write-Host "Servicios de SujetoLugar detenidos en el puerto $PuertoServicio."
    } else {
        Write-Host "No hay una sesión de SujetoLugar registrada en el puerto $PuertoServicio."
    }
    if ($CerrarLMStudio) {
        Stop-LMStudioServer
        Write-Host 'Servidor local de LM Studio cerrado.'
    }
    return
}

function Assert-SessionRunning {
    if (Test-Path -LiteralPath $stopRequest) {
        throw [OperationCanceledException]::new('Cierre solicitado desde el lanzador.')
    }
}

function Wait-Ready($process, $url) {
    for ($i = 0; $i -lt 180; $i++) {
        Assert-SessionRunning
        if ($process.HasExited) { throw "El proceso terminó. Revisa $logs" }
        try { return Invoke-RestMethod $url -TimeoutSec 2 } catch { Start-Sleep -Milliseconds 500 }
    }
    throw "Sin respuesta en $url. Revisa $logs"
}
function Check-Port($port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        try { $client.Connect('127.0.0.1', $port) } catch { return }
        throw "El puerto $port ya está ocupado."
    } finally { $client.Dispose() }
}
$llm = $null
$service = $null
$startedLMStudio = $false
$loadedGemma2 = $false
$session = $null
$stopRequest = $null
try {
    if (!$SoloServicio -and $PuertoServicio -ne 18766) { throw 'La partida usa el puerto 18766.' }
    if (!(Test-Path -LiteralPath $python -PathType Leaf)) {
        throw 'Falta el entorno .venv-decision. Sigue la sección de instalación del README principal.'
    }
    $session = [IO.File]::Open($sessionPath, 'OpenOrCreate', 'ReadWrite', 'Read')
    $token = [Guid]::NewGuid().ToString('N')
    $stopRequest = Join-Path $runtime "detener-$token"
    $session.SetLength(0)
    $tokenBytes = [Text.Encoding]::ASCII.GetBytes($token)
    $session.Write($tokenBytes, 0, $tokenBytes.Length)
    $session.Flush()
    $modelo = if ($Gemma2) { 'gemma2' } elseif ($Gemma4) { 'gemma4' } else {
        (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'configuracion.json') -Raw -Encoding UTF8 | ConvertFrom-Json).modelo_charla
    }
    if ($modelo -isnot [string] -or $modelo -notin @('gemma2','gemma4')) {
        throw 'En configuracion.json, modelo_charla debe ser gemma2 o gemma4.'
    }
    Write-Host "Modelo local de charla: $modelo"
    Check-Port $PuertoServicio
    Assert-SessionRunning
    $options = @('-u','servir.py','--port',"$PuertoServicio")
    if ($VozCPU) { $options += '--stt-cpu' }
    if ($Postura) { $options += '--postura' }
    if ($modelo -eq 'gemma2') {
        $api = 'http://127.0.0.1:1234/v1/models'
        try { $available = Invoke-RestMethod $api -TimeoutSec 3 } catch {
            Write-Host 'Iniciando el servidor local de LM Studio...'
            & lms server start --port 1234
            if ($LASTEXITCODE) { throw 'LM Studio no pudo iniciar el servidor en el puerto 1234.' }
            $startedLMStudio = $true
            $available = $null
            for ($i = 0; $i -lt 15 -and !$available; $i++) {
                Assert-SessionRunning
                try { $available = Invoke-RestMethod $api -TimeoutSec 2 } catch { Start-Sleep -Milliseconds 500 }
            }
            if (!$available) { throw 'LM Studio sigue sin responder en el puerto 1234.' }
        }
        Assert-SessionRunning
        if ('yell-gemma' -notin @($available.data.id)) {
            Write-Host 'Cargando Gemma 2 para la charla...'
            & lms load 'gemma-2-2b-it' --identifier yell-gemma --gpu max --context-length 2048 --parallel 1 -y
            if ($LASTEXITCODE) { throw 'LM Studio no pudo cargar gemma-2-2b-it como yell-gemma.' }
            $loadedGemma2 = $true
        }
        $options += '--gemma2'
    } else {
        Check-Port 18767
        $weights = 'modelos/gemma-4-E2B-it-Q4_K_M.gguf'
        if (!(Test-Path (Join-Path $PSScriptRoot $weights))) { & (Join-Path $PSScriptRoot 'Descargar-Gemma.ps1') }
        Assert-SessionRunning
        $argsLLM = @('-m', $weights, '--host', '127.0.0.1', '--port', '18767', '--alias', 'gemma-4-e2b-texto',
                     '-c', '2048', '-ngl', $CapasGPU, '-fa', 'on', '-ctk', 'q8_0', '-ctv', 'q8_0',
                     '-np', '1', '--jinja', '--chat-template-file', 'gemma4-charla.jinja')
        $engine = Join-Path $root 'AI NLP/models/llama/llama-server.exe'
        if ($CapasGPU -gt 0) {
            $backends = Join-Path $env:USERPROFILE '.lmstudio/extensions/backends'
            $cuda = Get-ChildItem $backends -Directory -Filter 'llama.cpp-win-x86_64-nvidia-cuda12-avx2-*' |
                Where-Object { Test-Path (Join-Path $_.FullName 'llama-server.exe') } |
                Sort-Object { [version]($_.Name.Split('-')[-1]) } -Descending | Select-Object -First 1
            if (!$cuda) { throw 'Instala el runtime de LM Studio llama.cpp CUDA 12 o indica -CapasGPU 0 para CPU.' }
            $manifest = Get-Content (Join-Path $cuda.FullName 'backend-manifest.json') -Raw | ConvertFrom-Json
            $engine = Join-Path $cuda.FullName 'llama-server.exe'
        }
        $priorPath = $env:Path
        try {
            if ($CapasGPU -gt 0) {
                foreach ($vendor in $manifest.vendor_lib_package_names) {
                    $env:Path = (Join-Path $backends "vendor/$vendor") + ';' + $env:Path
                }
                $devices = & $engine --list-devices 2>&1
                if ($LASTEXITCODE -or "$devices" -notmatch 'CUDA\d+:') { throw 'El runtime no pudo abrir la GPU CUDA.' }
            }
            $llm = Start-Process $engine -WorkingDirectory $PSScriptRoot -ArgumentList $argsLLM -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $logs 'gemma.err') -RedirectStandardOutput (Join-Path $logs 'gemma.out')
        } finally { $env:Path = $priorPath }
        $null = Wait-Ready $llm 'http://127.0.0.1:18767/health'
    }
    Assert-SessionRunning
    $service = Start-Process $python -WorkingDirectory $PSScriptRoot -ArgumentList $options -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $logs 'servicio.err') -RedirectStandardOutput (Join-Path $logs 'servicio.out')
    $health = Wait-Ready $service "http://127.0.0.1:$PuertoServicio/health"
    if ($health.profile -notin @('sujeto_lugar', 'sujeto_lugar_postura') -or 'D' -notin @($health.models)) {
        throw 'El servicio activo no corresponde a SujetoLugar.'
    }
    Assert-SessionRunning
    Write-Host "Para detener los servicios desde otra consola: Jugar.cmd -Detener -PuertoServicio $PuertoServicio"
    $watched = $service
    if (!$SoloServicio) {
        $project = Join-Path $root 'WarCommanderDemo/WarCommanderDemo.uproject'
        $game = Start-Process $UnrealEditor -ArgumentList @(('"'+$project+'"'), '/Game/Yell/ValleAlfa?YellMenu=1', '-game', '-windowed') -PassThru
        $watched = $game
    }
    while (!$watched.WaitForExit(250)) { Assert-SessionRunning }
    if ($null -ne $watched.ExitCode -and $watched.ExitCode -ne 0) {
        throw "El proceso terminó con código $($watched.ExitCode). Revisa $logs."
    }
} catch [OperationCanceledException] {
    Write-Host $_.Exception.Message
} catch {
    "$(Get-Date -Format o) $($_.Exception.Message)" | Add-Content -LiteralPath (Join-Path $logs 'inicio.log') -Encoding utf8
    throw
} finally {
    try {
        foreach ($proc in @($service, $llm)) {
            if ($proc -and !$proc.HasExited) {
                & taskkill.exe /PID $proc.Id /T /F | Out-Null
                if (!$proc.WaitForExit(3000)) { Write-Warning "El proceso $($proc.Id) sigue activo." }
            }
        }
        if ($loadedGemma2) {
            & lms unload yell-gemma
            if ($LASTEXITCODE) { Write-Warning 'No se pudo descargar yell-gemma.' }
        }
        if ($startedLMStudio) {
            & lms server stop
            if ($LASTEXITCODE) { Write-Warning 'No se pudo detener el servidor de LM Studio.' }
        }
    } finally {
        if ($session) { $session.Dispose() }
        if ($stopRequest) { [IO.File]::Delete($stopRequest) }
    }
}
