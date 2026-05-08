$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path .\freqtrade | Out-Null
Set-Location .\freqtrade

Write-Host "Freqtrade Docker setup placeholder."
Write-Host "Use the official Freqtrade Docker quickstart for the latest compose file."
Write-Host "Keep user_data inside: D:\_projects\trading\freqtrade\user_data"
