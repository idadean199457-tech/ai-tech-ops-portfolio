$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"

Start-Process -FilePath $python -ArgumentList "app.py" -WorkingDirectory (Join-Path $projectRoot "knowledge-base-assistant") -WindowStyle Hidden
Start-Process -FilePath $python -ArgumentList "app.py" -WorkingDirectory (Join-Path $projectRoot "support-workbench") -WindowStyle Hidden

Write-Host "Knowledge assistant: http://127.0.0.1:8765"
Write-Host "Support workbench: http://127.0.0.1:8766"
