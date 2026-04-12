#!/bin/bash
# =============================================================
# SportsLab Raspberry Pi 4 Bootstrap — production server
# Sets up: Postgres, MLflow, cron pipeline, Telegram, backup
#
# Requirements: Raspberry Pi 4 (4GB+), Ubuntu Server 24.04 ARM, SSD via USB3
# =============================================================

set -euo pipefail

echo "=== SportsLab Pi Production Bootstrap ==="
echo "Start: $(date)"

# --- 1. System packages ---
echo "[1/9] System packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq postgresql postgresql-client python3.11 python3.11-venv \
    libpq-dev git curl

# --- 2. Python + uv ---
echo "[2/9] Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# --- 3. Tailscale ---
echo "[3/9] Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
echo ">>> Run 'sudo tailscale up' to join mesh VPN"

# --- 4. Clone repo ---
echo "[4/9] Cloning SportsLab..."
APP_DIR="/app/sportslab"
sudo mkdir -p /app && sudo chown "$USER" /app
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && git pull
else
    git clone https://github.com/YOUR_USER/sportslab.git "$APP_DIR"
fi
cd "$APP_DIR"

# --- 5. Install deps (no GPU, no dev) ---
echo "[5/9] Installing Python dependencies (production)..."
uv sync --no-dev
# Install psycopg2 for Postgres
uv pip install psycopg2-binary

# --- 6. Postgres setup ---
echo "[6/9] Setting up Postgres..."
sudo -u postgres createuser --createdb sportslab 2>/dev/null || true
sudo -u postgres createdb sportslab 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER sportslab PASSWORD 'changeme';" 2>/dev/null || true

# Tune for 4GB RAM
sudo tee -a /etc/postgresql/16/main/conf.d/sportslab.conf > /dev/null <<PGCONF
shared_buffers = 512MB
effective_cache_size = 2GB
work_mem = 32MB
maintenance_work_mem = 128MB
max_connections = 20
PGCONF
sudo systemctl restart postgresql

# Run Alembic migrations
cd packages/ml-in-sports
ML_IN_SPORTS_DATABASE_URL="postgresql://sportslab:changeme@localhost:5432/sportslab" \
    uv run alembic upgrade head
cd "$APP_DIR"

# --- 7. Environment file ---
echo "[7/9] Creating .env..."
cat > "$APP_DIR/.env" <<ENVFILE
ML_IN_SPORTS_DATABASE_URL=postgresql://sportslab:changeme@localhost:5432/sportslab
ML_IN_SPORTS_DB_PATH=data/football.db
ML_IN_SPORTS_PINNACLE_ODDS_DIR=data/odds
ML_IN_SPORTS_LOG_JSON=true
ML_IN_SPORTS_LOG_LEVEL=INFO
ML_IN_SPORTS_TELEGRAM_BOT_TOKEN=
ML_IN_SPORTS_TELEGRAM_CHAT_ID=
ML_IN_SPORTS_HEALTHCHECK_ID=
ENVFILE
echo ">>> Edit .env with your Telegram token and healthcheck ID"

# --- 8. MLflow server ---
echo "[8/9] Setting up MLflow..."
uv pip install mlflow
mkdir -p /app/mlflow
cat > /etc/systemd/system/mlflow.service <<MLFLOW
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
User=$USER
WorkingDirectory=/app/mlflow
ExecStart=$(which mlflow) server \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root /app/mlflow/artifacts \
    --host 0.0.0.0 --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
MLFLOW
sudo systemctl daemon-reload
sudo systemctl enable mlflow
sudo systemctl start mlflow
echo "MLflow UI: http://$(hostname -I | awk '{print $1}'):5000"

# --- 9. Cron ---
echo "[9/9] Setting up cron..."
CRON_FILE="/tmp/sportslab_cron"
cat > "$CRON_FILE" <<CRON
# SportsLab daily pipeline
0 6 * * * cd $APP_DIR && source .env && uv run python infra/daily_pipeline.py morning >> /var/log/sportslab/morning.log 2>&1
30 23 * * * cd $APP_DIR && source .env && uv run python infra/daily_pipeline.py evening >> /var/log/sportslab/evening.log 2>&1
59 23 * * 0 cd $APP_DIR && source .env && uv run sl weekly run >> /var/log/sportslab/weekly.log 2>&1
0 2 * * * cd $APP_DIR && bash infra/backup.sh >> /var/log/sportslab/backup.log 2>&1
CRON
crontab "$CRON_FILE"
sudo mkdir -p /var/log/sportslab

echo ""
echo "=== Pi Setup Complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env (Telegram token, healthcheck ID)"
echo "  2. sudo tailscale up (join mesh)"
echo "  3. Load initial data: scp data/features/all_features.parquet from dev"
echo "  4. Test: source .env && uv run sl predict run --model-path models/production/model.pkl"
echo ""
echo "MLflow: http://$(hostname -I | awk '{print $1}'):5000"
echo "Postgres: postgresql://sportslab:changeme@localhost:5432/sportslab"
