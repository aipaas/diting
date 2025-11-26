# PowerShell script to run ARQ worker on Windows
# 
# Environment:
#   - This script is for LOCAL DEVELOPMENT on Windows (本地调试 Windows 环境)
#   - Production environment uses Linux server
#
# Cross-platform Note:
#   - The Python code (run_worker.py) is designed to work on both Windows and Linux
#   - This .ps1 script is Windows-specific for convenience
#   - Linux equivalent would use: bash run_worker.sh (if exists) or direct python command

Write-Host "🚀 Starting ARQ Worker..." -ForegroundColor Green
Write-Host "Environment: Windows (Local Development)" -ForegroundColor Cyan

# Run worker
uv run python -m diting_web.scripts.run_worker

# Alternative methods:
# uv run python -m diting_web.workers.worker
# uv run arq diting_web.workers.worker.WorkerSettings


