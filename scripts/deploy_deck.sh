#!/bin/bash
set -euo pipefail

DECK_HOST="deck@steamdeck"
DECK_DEST="/home/deck/.local/share/dfb"
SERVICE_NAME="flybrain"
SERVICE_PORT=8082

echo "🚀 Deploying to Steam Deck..."

# Ensure destination exists
ssh "$DECK_HOST" "mkdir -p $DECK_DEST/src $DECK_DEST/sim $DECK_DEST/shaders"

# Sync source (excluding venv, __pycache__, .git)
rsync -avz --delete \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.ruff_cache' \
  --exclude='coverage.xml' \
  --exclude='htmlcov' \
  ./src/ "$DECK_HOST:$DECK_DEST/src/"

rsync -avz ./sim/ "$DECK_HOST:$DECK_DEST/sim/"
rsync -avz ./shaders/ "$DECK_HOST:$DECK_DEST/shaders/"
rsync -avz ./pyproject.toml "$DECK_HOST:$DECK_DEST/"
rsync -avz ./Makefile "$DECK_HOST:$DECK_DEST/"

# Create venv and install deps on Deck (including psutil for monitoring)
ssh "$DECK_HOST" "cd $DECK_DEST && python3 -m venv .venv && .venv/bin/pip install -e . psutil --quiet"

# Install systemd unit
rsync -avz ./deploy/flybrain.service "$DECK_HOST:.config/systemd/user/"

# Reload and restart
ssh "$DECK_HOST" "systemctl --user daemon-reload && systemctl --user restart $SERVICE_NAME && systemctl --user enable $SERVICE_NAME"

echo "✅ Deploy complete. Health check:"
ssh "$DECK_HOST" "sleep 2 && curl -s http://localhost:$SERVICE_PORT/health"