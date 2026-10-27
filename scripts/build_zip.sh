#!/usr/bin/env bash
# Собирает dist/humanize-text.zip для загрузки в claude.ai (Settings → Capabilities → Skills).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf dist && mkdir -p dist
( cd skills && zip -rq ../dist/humanize-text.zip humanize-text -x "*/__pycache__/*" "*.pyc" )
echo "dist/humanize-text.zip"
unzip -l dist/humanize-text.zip
