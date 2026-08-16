#!/usr/bin/env bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 не найден. Установите Python и pygame: pip install -r requirements.txt"
  exit 1
fi
exec python3 main.py
