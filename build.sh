#!/usr/bin/env bash
# Builds the Foklumi beta as a standalone folder with PyInstaller.
# Linux / macOS only. Output: dist/foklumi/ and a .tar.gz next to it.
set -euo pipefail
cd "$(dirname "$0")"

VERSION="0.1.0-beta"

if [ ! -d .venv ]; then
    python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q --upgrade pip
pip install -q -r requirements.txt pyinstaller

echo "==> Running tests"
python -m unittest discover -s tests -t .

echo "==> Building $VERSION"
rm -rf build dist
pyinstaller --noconfirm --clean \
    --name foklumi \
    --add-data "data/vocab.json:data" \
    main.py

ARCHIVE="foklumi-${VERSION}-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m).tar.gz"
tar -czf "dist/${ARCHIVE}" -C dist foklumi

echo
echo "Done."
echo "  Run:     ./dist/foklumi/foklumi"
echo "  Archive: dist/${ARCHIVE}"
