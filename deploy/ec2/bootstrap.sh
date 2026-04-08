#!/usr/bin/env bash
# Ejecutar en Ubuntu EC2 como usuario con sudo (típicamente ubuntu).
# Clona/actualiza Synapse, backend venv, frontend build, nginx, systemd.

set -euo pipefail

REPO_URL="${SYNAPSE_REPO_URL:-https://github.com/gerardoriarte-bt/synapse.git}"
INSTALL_ROOT="${SYNAPSE_HOME:-$HOME}"
APP_DIR="$INSTALL_ROOT/Synapse"

echo "==> Paquetes base"
sudo apt-get update -y
sudo apt-get install -y nginx git curl

echo "==> Node.js 22 (NodeSource)"
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
node -v
npm -v

echo "==> Python venv"
sudo apt-get install -y python3.12-venv python3-pip build-essential libpq-dev

echo "==> Repo"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull
fi

echo "==> Backend"
cd "$APP_DIR/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  echo "Crea $APP_DIR/backend/.env (ver backend/.env.example). Abortando."
  exit 1
fi

echo "==> Frontend"
cd "$APP_DIR/frontend"
npm ci
if [[ ! -f .env.production ]]; then
  echo "NEXT_PUBLIC_API_URL=" > .env.production
  echo "Creado .env.production con API same-origin (vacío). Edita si usas API en otro host."
fi
npm run build

echo "==> systemd"
sudo cp "$APP_DIR/deploy/ec2/synapse-api.service" /etc/systemd/system/
sudo cp "$APP_DIR/deploy/ec2/synapse-frontend.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable synapse-api synapse-frontend
sudo systemctl restart synapse-api synapse-frontend

echo "==> nginx"
sudo cp "$APP_DIR/deploy/ec2/nginx-synapse.conf" /etc/nginx/sites-available/synapse
sudo ln -sf /etc/nginx/sites-available/synapse /etc/nginx/sites-enabled/synapse
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "==> Listo. Abre http://$(curl -sS ifconfig.me 2>/dev/null || echo TU_IP_PUBLICA)/"
echo "    Security Group: TCP 22, 80 (y 443 si luego pones TLS)."
