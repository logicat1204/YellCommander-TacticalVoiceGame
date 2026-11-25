$ErrorActionPreference = 'Stop'
$name = 'gemma-4-E2B-it-Q4_K_M.gguf'
$folder = Join-Path $PSScriptRoot 'modelos'
New-Item -ItemType Directory -Force $folder | Out-Null
$dest = Join-Path $folder $name
$partial = "$dest.part"
$sha = '71e6e8cb64a76da1a734fb8f6ba389d2784950d9902f5e87244fca0a15190c94'
if (Test-Path $dest) {
    if ((Get-FileHash $dest -Algorithm SHA256).Hash -eq $sha) { return }
    throw "El archivo $dest no coincide con el modelo publicado."
}
$url = "https://huggingface.co/lmstudio-community/gemma-4-E2B-it-GGUF/resolve/eed445ccfb8aef2e279df1a97e133baf06e443b4/$name"
if (!(Test-Path $partial) -or (Get-FileHash $partial -Algorithm SHA256).Hash -ne $sha) {
    & curl.exe -fL -C - --connect-timeout 15 --speed-time 45 --speed-limit 1024 --retry 2 -o $partial $url
    if ($LASTEXITCODE) { throw 'Descarga incompleta. Puedes reanudarla con este mismo script.' }
}
if ((Get-FileHash $partial -Algorithm SHA256).Hash -ne $sha) { throw 'El GGUF descargado no coincide con el SHA256 publicado.' }
Move-Item -LiteralPath $partial -Destination $dest
