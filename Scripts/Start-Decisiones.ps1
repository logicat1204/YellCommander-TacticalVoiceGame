param(
    [switch]$OnlyService,
    [string]$UnrealEditor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$nlp = Join-Path $root 'AI NLP'
$python = Join-Path $root '.venv-decision/Scripts/python.exe'
if (!(Test-Path $python)) { throw 'Instala el entorno de decisiones según el README.' }
$config = Get-Content (Join-Path $nlp 'yell/dialogue.json') -Raw | ConvertFrom-Json
$endpoint = [uri]$config.endpoint
$api = $endpoint.GetLeftPart([System.UriPartial]::Authority)
if (!$endpoint.IsLoopback) { throw 'Configura LM Studio en loopback.' }
$available = $null
try { $available = Invoke-RestMethod "$api/v1/models" -TimeoutSec 2 } catch {
    & lms server start --port $endpoint.Port
    if ($LASTEXITCODE) { throw 'No se pudo iniciar el servidor de LM Studio.' }
}
if ($config.model -notin @($available.data.id)) {
    if ($config.model -ne 'yell-gemma') { throw "Carga primero $($config.model) en LM Studio." }
    & lms load 'gemma-2-2b-it' --identifier yell-gemma --gpu max --context-length 2048 --parallel 1 -y
    if ($LASTEXITCODE) { throw 'Importa el GGUF en LM Studio según el README.' }
}
$logs = Join-Path $root 'WarCommanderDemo/Saved/Logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
$service = Start-Process $python -WorkingDirectory $nlp -ArgumentList @('-u','-m','yell.service','--decisiones','--no-llm',
    '--whisper','models/whisper-base','--whisper-retry','models/whisper-small') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logs 'Decisiones.out.log') -RedirectStandardError (Join-Path $logs 'Decisiones.err.log')
try {
    $ready = $false
    for ($i=0; $i -lt 100; $i++) {
        if ($service.HasExited) { throw "El servicio salió. Consulta $logs/Decisiones.err.log" }
        $health = $null
        try { $health=Invoke-RestMethod 'http://127.0.0.1:18765/health' -TimeoutSec 1 } catch {}
        if ($health) {
            if ('D' -in $health.models) { $ready=$true; break }
            throw 'Hay otro servicio de partida en el puerto 18765.'
        }
        Start-Sleep -Milliseconds 600
    }
    if (!$ready) { throw 'El servicio de decisiones no está disponible.' }
    if ($OnlyService) { Wait-Process -Id $service.Id }
    else {
        $project = Join-Path $root 'WarCommanderDemo/WarCommanderDemo.uproject'
        $game=Start-Process $UnrealEditor -ArgumentList @(('"'+$project+'"'),'/Game/Yell/ValleAlfa','-game','-windowed','-YellModels=D') -PassThru
        $game.WaitForExit()
    }
} finally {
    if (!$service.HasExited) { Stop-Process -Id $service.Id }
}

