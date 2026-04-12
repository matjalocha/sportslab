#!/bin/bash
# =============================================================
# SportsLab VM Bootstrap — run on ANY fresh VM with GPU
# Sets up training environment in < 30 minutes
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/.../setup_vm.sh | bash
#   # or:
#   scp setup_vm.sh vm-host: && ssh vm-host bash setup_vm.sh
#
# Requirements: Ubuntu 22.04+, CUDA drivers pre-installed (for GPU)
# =============================================================

set -euo pipefail

echo "=== SportsLab VM Bootstrap ==="
echo "Start: $(date)"

# --- 1. System packages ---
echo "[1/7] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq git curl build-essential libpq-dev

# --- 2. Python + uv ---
echo "[2/7] Installing uv + Python 3.11..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11

# --- 3. Tailscale (mesh VPN to reach Pi) ---
echo "[3/7] Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
echo ">>> Run 'sudo tailscale up' and authenticate to join mesh"

# --- 4. Clone repo ---
echo "[4/7] Cloning SportsLab..."
if [ -d "$HOME/sportslab" ]; then
    cd "$HOME/sportslab" && git pull
else
    git clone https://github.com/YOUR_USER/sportslab.git "$HOME/sportslab"
fi
cd "$HOME/sportslab"

# --- 5. Install deps (with GPU extras) ---
echo "[5/7] Installing Python dependencies..."
uv sync --all-extras --dev
# TabPFN needs PyTorch — install with CUDA
uv pip install torch --index-url https://download.pytorch.org/whl/cu121 2>/dev/null || true

# --- 6. Pull latest data from Pi ---
echo "[6/7] Pulling data from Pi..."
PI_HOST="${PI_HOST:-pi}"  # Tailscale hostname
mkdir -p data/features data/odds
scp "$PI_HOST:/app/sportslab/data/features/all_features.parquet" data/features/ 2>/dev/null || echo ">>> Manual: scp parquet from Pi"
scp -r "$PI_HOST:/app/sportslab/data/odds/" data/ 2>/dev/null || echo ">>> Manual: scp odds from Pi"

# --- 7. Configure MLflow to point to Pi ---
echo "[7/7] Configuring MLflow..."
PI_MLFLOW="${PI_MLFLOW:-http://$PI_HOST:5000}"
echo "export MLFLOW_TRACKING_URI=$PI_MLFLOW" >> ~/.bashrc
export MLFLOW_TRACKING_URI="$PI_MLFLOW"

echo ""
echo "=== Setup complete! ==="
echo "Time: $(date)"
echo ""
echo "Quick test:"
echo "  cd ~/sportslab"
echo "  uv run sl backtest run experiments/quick_test.yaml --mlflow"
echo ""
echo "Full training:"
echo "  uv run sl backtest run experiments/hybrid_v1.yaml --mlflow"
echo ""
echo "Push model to Pi:"
echo "  scp models/latest/model.pkl $PI_HOST:/app/sportslab/models/production/"
echo ""
echo "MLflow UI (on Pi): $PI_MLFLOW"
