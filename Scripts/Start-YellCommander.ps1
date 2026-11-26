[CmdletBinding()]
param(
    [switch]$Postura,
    [Alias('OnlyService')][switch]$SoloServicio,
    [switch]$Gemma2,
    [switch]$Gemma4,
    [switch]$VozCPU,
    [switch]$Detener,
    [switch]$CerrarLMStudio,
    [int]$CapasGPU,
    [int]$PuertoServicio,
    [string]$UnrealEditor
)

& (Join-Path $PSScriptRoot '../Variantes/SujetoLugar/Iniciar.ps1') @PSBoundParameters
