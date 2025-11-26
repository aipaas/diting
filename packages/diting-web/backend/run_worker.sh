#!/bin/bash
# Bash script to run ARQ worker on Linux
# 
# Environment:
#   - This script is for PRODUCTION on Linux server (生产环境 Linux 服务器)
#   - Also works for local development on Linux/macOS
#   - Windows users should use: run_worker.ps1
#
# Cross-platform Note:
#   - The Python code (run_worker.py) is designed to work on both Windows and Linux
#   - This .sh script is Linux/macOS-specific for convenience

echo "🚀 Starting ARQ Worker..."
echo "Environment: Linux (Production/Development)"

# Run worker
uv run python -m diting_web.scripts.run_worker

# Alternative methods:
# uv run python -m diting_web.workers.worker
# uv run arq diting_web.workers.worker.WorkerSettings


