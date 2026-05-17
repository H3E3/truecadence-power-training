# TrueCadence Streamlit 重启脚本
# 用法：在 bt_power 目录右键 "使用 PowerShell 运行"，或
#       powershell -File restart.ps1

$port = 8502

# 1. 检查端口是否已被占用
$existing = netstat -ano | Select-String ":$port.*LISTENING"
if ($existing) {
    Write-Host "Port $port already in use. Killing existing python processes..." -ForegroundColor Yellow
    taskkill /F /FI "IMAGENAME eq python.exe" 2>$null | Out-Null
    Start-Sleep 2
}

# 2. 启动 Streamlit
Write-Host "Starting Streamlit on port $port..." -ForegroundColor Green
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port $port --server.headless true --server.fileWatcherType none

Write-Host "`nDone. Open http://localhost:$port in your browser." -ForegroundColor Cyan
