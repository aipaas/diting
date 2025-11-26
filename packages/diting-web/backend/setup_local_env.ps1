# DiTing Web Backend - 本地环境配置脚本 (Windows PowerShell)
# 用法: .\setup_local_env.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "DiTing Web 本地环境配置向导" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 .env 文件是否存在
if (Test-Path ".env") {
    Write-Host "⚠️  .env 文件已存在" -ForegroundColor Yellow
    $overwrite = Read-Host "是否覆盖? (y/N)"
    if ($overwrite -ne "y") {
        Write-Host "❌ 已取消配置" -ForegroundColor Red
        exit
    }
}

Write-Host "📝 请输入远程服务器配置信息:" -ForegroundColor Green
Write-Host ""

# 获取用户输入
$remoteHost = Read-Host "远程服务器 IP 或域名"
$pgUser = Read-Host "PostgreSQL 用户名 [admin]"
if ([string]::IsNullOrWhiteSpace($pgUser)) { $pgUser = "admin" }

$pgPassword = Read-Host "PostgreSQL 密码 [password]" -AsSecureString
$pgPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pgPassword))
if ([string]::IsNullOrWhiteSpace($pgPasswordPlain)) { $pgPasswordPlain = "password" }

$pgDatabase = Read-Host "PostgreSQL 数据库名 [diting_web]"
if ([string]::IsNullOrWhiteSpace($pgDatabase)) { $pgDatabase = "diting_web" }

$redisPassword = Read-Host "Redis 密码 (如无密码直接回车)"
$redisUrl = if ([string]::IsNullOrWhiteSpace($redisPassword)) {
    "redis://${remoteHost}:6379/0"
} else {
    "redis://:${redisPassword}@${remoteHost}:6379/0"
}

$minioAccessKey = Read-Host "MinIO Access Key [minioadmin]"
if ([string]::IsNullOrWhiteSpace($minioAccessKey)) { $minioAccessKey = "minioadmin" }

$minioSecretKey = Read-Host "MinIO Secret Key [minioadmin]" -AsSecureString
$minioSecretKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($minioSecretKey))
if ([string]::IsNullOrWhiteSpace($minioSecretKeyPlain)) { $minioSecretKeyPlain = "minioadmin" }

$llmApiKey = Read-Host "OpenAI API Key (sk-...)"
$embeddingApiKey = Read-Host "Embedding API Key (如同上直接回车)"
if ([string]::IsNullOrWhiteSpace($embeddingApiKey)) { $embeddingApiKey = $llmApiKey }

Write-Host ""
Write-Host "✅ 正在生成 .env 文件..." -ForegroundColor Green

# 生成 .env 文件
$envContent = @"
# ========================================
# DiTing Web Backend - 本地开发配置
# 自动生成于: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ========================================

# 应用配置
ENVIRONMENT=development
DEBUG=True
HOST=0.0.0.0
PORT=8000

# ========================================
# 远程服务器配置
# ========================================

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://${pgUser}:${pgPasswordPlain}@${remoteHost}:5432/${pgDatabase}
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=False

# Redis
REDIS_URL=${redisUrl}

# MinIO
MINIO_ENDPOINT=${remoteHost}:9000
MINIO_ACCESS_KEY=${minioAccessKey}
MINIO_SECRET_KEY=${minioSecretKeyPlain}
MINIO_SECURE=False
MINIO_BUCKET_NAME=diting-datasets

# ========================================
# 认证配置
# ========================================
JWT_SECRET_KEY=local-dev-secret-key-$(Get-Random)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# ========================================
# LLM 配置
# ========================================
DEFAULT_LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=${llmApiKey}
LLM_TIMEOUT=60.0

# ========================================
# Embedding 配置
# ========================================
DEFAULT_EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=${embeddingApiKey}
EMBEDDING_TIMEOUT=60.0

# ========================================
# CORS 配置
# ========================================
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:8000"]
CORS_ALLOW_CREDENTIALS=True

# ========================================
# 日志配置
# ========================================
LOG_LEVEL=INFO
LOG_FORMAT=json
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8 -NoNewline

Write-Host "✅ .env 文件创建成功！" -ForegroundColor Green
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "下一步操作:" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "1. 安装依赖:        uv sync" -ForegroundColor Yellow
Write-Host "2. 数据库迁移:      uv run alembic upgrade head" -ForegroundColor Yellow
Write-Host "3. 初始化数据:      uv run python -m diting_web.scripts.init_admin" -ForegroundColor Yellow
Write-Host "                    uv run python -m diting_web.scripts.init_metrics" -ForegroundColor Yellow
Write-Host "4. 启动 API:        uv run uvicorn diting_web.main:app --reload" -ForegroundColor Yellow
Write-Host "5. 启动 Worker:     .\run_worker.ps1 (新终端)" -ForegroundColor Yellow
Write-Host ""
Write-Host "📚 详细文档: ..\LOCAL_SETUP.md" -ForegroundColor Cyan
Write-Host ""

$autoInstall = Read-Host "是否立即安装依赖? (y/N)"
if ($autoInstall -eq "y") {
    Write-Host ""
    Write-Host "📦 正在安装依赖..." -ForegroundColor Green
    uv sync
    
    Write-Host ""
    $autoMigrate = Read-Host "是否执行数据库迁移? (y/N)"
    if ($autoMigrate -eq "y") {
        Write-Host ""
        Write-Host "🗄️  执行数据库迁移..." -ForegroundColor Green
        uv run alembic upgrade head
        
        Write-Host ""
        $autoInit = Read-Host "是否初始化数据? (y/N)"
        if ($autoInit -eq "y") {
            Write-Host ""
            Write-Host "🔧 初始化管理员..." -ForegroundColor Green
            uv run python -m diting_web.scripts.init_admin
            
            Write-Host ""
            Write-Host "📊 初始化指标..." -ForegroundColor Green
            uv run python -m diting_web.scripts.init_metrics
            
            Write-Host ""
            Write-Host "✅ 全部完成！现在可以启动服务了:" -ForegroundColor Green
            Write-Host "   uv run uvicorn diting_web.main:app --reload" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "🎉 配置完成！" -ForegroundColor Green

