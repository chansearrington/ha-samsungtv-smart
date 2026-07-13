#!/usr/bin/env bash
# The ONLY way to deploy this component to the live TV.
# Usage: scripts/deploy_to_ark.sh
set -euo pipefail

LOCAL="$(cd "$(dirname "$0")/.." && pwd)/custom_components/samsungtv_smart/"
REMOTE="ark:/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart/"
LOG="/mnt/user/appdata/homeassistant/home-assistant.log"

echo ">> rsync $LOCAL -> $REMOTE"
rsync -a --delete --exclude='__pycache__' --exclude='*.pyc' "$LOCAL" "$REMOTE"

echo ">> restarting homeassistant container"
ssh ark 'docker restart homeassistant'

echo ">> waiting 45s for HA to come up"
sleep 45

echo ">> scanning log for samsungtv errors (last 400 lines)"
if ssh ark "tail -n 400 $LOG | grep -iE 'error|traceback|exception' | grep -i samsungtv"; then
  echo '!! samsungtv errors found in log'; exit 1
else
  echo '>> no samsungtv errors in recent log'
fi
