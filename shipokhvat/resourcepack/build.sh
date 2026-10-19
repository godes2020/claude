#!/usr/bin/env bash
# Собирает ресурс-пак в zip и печатает SHA-1 для server.properties.
set -euo pipefail
cd "$(dirname "$0")"
OUT="Shipokhvat-ResourcePack.zip"
rm -f "$OUT"
zip -qr -X "$OUT" pack.mcmeta assets
[ -f pack.png ] && zip -q "$OUT" pack.png
echo "Готово: $(pwd)/$OUT"
echo "resource-pack-sha1=$(sha1sum "$OUT" | cut -d' ' -f1)"
