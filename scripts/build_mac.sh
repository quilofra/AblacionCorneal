#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [[ ! -d "assets" ]]; then
  echo "Error: missing assets/ directory." >&2
  exit 1
fi

if [[ ! -f "assets/app_icon.png" ]]; then
  echo "Error: missing assets/app_icon.png." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found." >&2
  exit 1
fi

if [[ ! -f "AblacionCorneal.spec" ]]; then
  echo "Error: missing AblacionCorneal.spec." >&2
  exit 1
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m pip install Pillow

rm -rf build dist
python -m PyInstaller AblacionCorneal.spec

if [[ ! -d "dist/AblacionCorneal.app" ]]; then
  echo "Error: build failed; dist/AblacionCorneal.app not found." >&2
  exit 1
fi

if command -v ditto >/dev/null 2>&1; then
  rm -f "dist/AblacionCorneal-macOS.zip"
  ditto -c -k --sequesterRsrc --keepParent "dist/AblacionCorneal.app" "dist/AblacionCorneal-macOS.zip"
fi

echo "Build complete: ${PROJECT_ROOT}/dist/AblacionCorneal.app"
if [[ -f "dist/AblacionCorneal-macOS.zip" ]]; then
  echo "Archive ready: ${PROJECT_ROOT}/dist/AblacionCorneal-macOS.zip"
fi
