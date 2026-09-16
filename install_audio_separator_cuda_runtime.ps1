$ErrorActionPreference = "Stop"

$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
$python = Join-Path $projectRoot "ai_libraries_common\python_env\python.exe"
$service = Join-Path $projectRoot "vocal_separator_service.py"
$model = Join-Path $projectRoot "models\audio-separator\Kim_Vocal_2.onnx"
$runtime = Join-Path $projectRoot "models\audio-separator\runtime"
$staging = Join-Path $projectRoot "models\audio-separator\runtime.cuda-staging"
$backup = Join-Path $projectRoot "models\audio-separator\runtime.previous"
$sitePackages = Join-Path $projectRoot "ai_libraries_common\python_env\Lib\site-packages"

foreach ($required in @($python, $service, $model, $runtime)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required Audio Separator component is missing: $required"
    }
}

Write-Host "[Audio Separator] Installing CUDA runtime in a verified staging directory..."
if (Test-Path -LiteralPath $staging) {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
Copy-Item -LiteralPath $runtime -Destination $staging -Recurse -Force

$oldProviderItems = @(
    (Join-Path $staging "onnxruntime"),
    (Get-ChildItem -LiteralPath $staging -Directory -Filter "onnxruntime*.dist-info" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName),
    (Get-ChildItem -LiteralPath $staging -Directory -Filter "onnxruntime_gpu*.dist-info" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
)
foreach ($item in $oldProviderItems) {
    if ($item -and (Test-Path -LiteralPath $item)) {
        Remove-Item -LiteralPath $item -Recurse -Force
    }
}

& $python -m pip install --disable-pip-version-check --no-deps --upgrade `
    --target $staging "onnxruntime-gpu==1.23.2"
if ($LASTEXITCODE -ne 0) {
    throw "onnxruntime-gpu installation failed; the existing runtime was preserved"
}

Write-Host "[Audio Separator] Validating CUDAExecutionProvider with the real Kim_Vocal_2 model..."
& $python -S $service --runtime $staging --studio-site-packages $sitePackages --model $model --probe
if ($LASTEXITCODE -ne 0) {
    throw "CUDA provider validation failed; the existing runtime was preserved"
}

if (Test-Path -LiteralPath $backup) {
    Remove-Item -LiteralPath $backup -Recurse -Force
}
Move-Item -LiteralPath $runtime -Destination $backup
try {
    Move-Item -LiteralPath $staging -Destination $runtime
} catch {
    Move-Item -LiteralPath $backup -Destination $runtime
    throw
}
Remove-Item -LiteralPath $backup -Recurse -Force
Write-Host "[Audio Separator] CUDA runtime installed and verified."
