
$ErrorActionPreference = "Stop"

uv sync --extra dev

Write-Host ""
Write-Host "Python environment created."
Write-Host "Tesseract OCR and Liblouis must be installed separately."
Write-Host "See README.md for installation instructions."
Write-Host ""
Write-Host "Launch using:"
Write-Host "uv run braille-converter"
