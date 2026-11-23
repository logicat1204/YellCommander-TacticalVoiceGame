param(
    [string] $UnrealEditor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe',
    [switch] $OnlyService,
    [switch] $NoLLM,
    [switch] $NoVoice,
    [switch] $Transfer,
    [switch] $Decisiones
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($Decisiones -or (!$Transfer -and !$NoLLM -and !$NoVoice -and
    (Test-Path -LiteralPath (Join-Path $workspace 'AI NLP/models/decisiones/actual.txt')))) {
    & (Join-Path $PSScriptRoot 'Start-Decisiones.ps1') -OnlyService:$OnlyService -UnrealEditor $UnrealEditor
    return
}
$project = Join-Path $workspace 'WarCommanderDemo/WarCommanderDemo.uproject'
$nlp = Join-Path $workspace 'AI NLP'
$python = Join-Path $workspace '.venv/Scripts/python.exe'
$llama = Join-Path $nlp 'models/llama/llama-server.exe'
$qwen = Join-Path $nlp 'models/llama/qwen2.5-1.5b-instruct-q4_k_m.gguf'
$whisper = Join-Path $nlp 'models/whisper-base'
$transferWeights = Join-Path $nlp 'models/transfer-c'
$logs = Join-Path $workspace 'WarCommanderDemo/Saved/Logs'
New-Item -ItemType Directory -Path $logs -Force | Out-Null

function Wait-LocalService([string] $Url, [Diagnostics.Process] $Process) {
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    do {
        if ($Process -and $Process.HasExited) {
            throw "El proceso local salió con código $($Process.ExitCode). Consulta $logs"
        }
        try {
            return Invoke-RestMethod -Uri $Url -TimeoutSec 2
        } catch {
            Start-Sleep -Milliseconds 800
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "El servicio local no respondió en $Url. Consulta $logs"
}

if (-not (Test-Path -LiteralPath $python)) { throw 'Falta .venv. Consulta README.md para instalar las dependencias.' }
if (-not ((Test-Path -LiteralPath (Join-Path $nlp 'models/scratch-fase1.pt')) -or (Test-Path -LiteralPath (Join-Path $nlp 'models/scratch.pt')))) {
    throw 'Falta el checkpoint del Modelo A. Ejecuta el entrenamiento descrito en README.md.'
}
if (-not $OnlyService -and -not (Test-Path -LiteralPath $UnrealEditor)) { throw "No se encontró Unreal Editor en $UnrealEditor" }
$env:PYTHONUTF8 = '1'
$service = $null
$llamaServer = $null
try {
    if (-not $NoLLM) {
        if (-not (Test-Path -LiteralPath $llama) -or -not (Test-Path -LiteralPath $qwen)) {
            throw 'Faltan llama-server.exe o los pesos Qwen. Consulta README.md o usa -NoLLM.'
        }
        $llamaArgs = @('-m', ('"' + $qwen + '"'), '--alias', 'yell-local', '--host', '127.0.0.1', '--port', '8081',
            '-t', '4', '--threads-batch', '4', '--parallel', '1', '--ctx-size', '3072', '--n-gpu-layers', '0')
        $llamaServer = Start-Process -FilePath $llama -WorkingDirectory (Split-Path -Parent $llama) -ArgumentList $llamaArgs -RedirectStandardOutput (Join-Path $logs 'YellLlama.out.log') -RedirectStandardError (Join-Path $logs 'YellLlama.err.log') -WindowStyle Hidden -PassThru
        Wait-LocalService 'http://127.0.0.1:8081/health' $llamaServer | Out-Null
    }
    $serviceArgs = @('-u', '-m', 'yell.service')
    if (-not $NoVoice) {
        if (-not (Test-Path -LiteralPath (Join-Path $whisper 'model.bin'))) {
            throw 'Faltan los pesos de Whisper Base. Consulta README.md o usa -NoVoice para probar la entrada escrita.'
        }
        $serviceArgs += @('--whisper', ('"' + $whisper + '"'))
        $retry = Join-Path $nlp 'models/whisper-small'
        if (Test-Path -LiteralPath (Join-Path $retry 'model.bin')) {
            $serviceArgs += @('--whisper-retry', ('"' + $retry + '"'))
        }
    }
    if ($NoLLM) { $serviceArgs += '--no-llm' }
    if ($Transfer) {
        if (-not (Test-Path -LiteralPath (Join-Path $transferWeights 'transfer.safetensors'))) {
            throw 'Faltan los pesos del Modelo C. Entrena desde el cuaderno de Fase 1.'
        }
        $serviceArgs += @('--transfer', ('"' + $transferWeights + '"'))
    }
    $service = Start-Process -FilePath $python -WorkingDirectory $nlp -ArgumentList $serviceArgs -RedirectStandardOutput (Join-Path $logs 'YellService.out.log') -RedirectStandardError (Join-Path $logs 'YellService.err.log') -WindowStyle Hidden -PassThru
    $state = Wait-LocalService 'http://127.0.0.1:18765/health' $service
    Write-Host "Radio disponible. Modelos $($state.models -join ', '). Voz $($state.stt_configured)."
    if ($OnlyService) {
        Write-Host 'Mantén esta terminal abierta mientras utilizas el servicio.'
        Wait-Process -Id $service.Id
    } else {
        $game = Start-Process -FilePath $UnrealEditor -ArgumentList @(
            ('"' + $project + '"'), '/Game/Yell/ValleAlfa', '-game', '-windowed', '-ResX=1440', '-ResY=900',
            ('-YellModels=' + ($state.models -join ','))) -PassThru
        Wait-Process -Id $game.Id -ErrorAction SilentlyContinue
    }
} finally {
    foreach ($process in @($service, $llamaServer)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        }
    }
}
