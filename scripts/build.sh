#!/usr/bin/env bash
# build.sh — produz os artefatos que o módulo NixOS (habbo-nixos) consome.
#
# O módulo habbo.nix espera, dentro de <habboRoot>/:
#   arcturus/Habbo-3.5.5-jar-with-dependencies.jar   (emulador)
#   cms/                                             (CMS Laravel + client buildado)
# Os dados pesados (swf-assets, nitro-converter) NÃO entram no git — o
# habbo-asset-convert.service (flake) os consome do disco, o script de
# conversão é idempotente e roda no boot.
#
# Uso:
#   scripts/build.sh               # compila o emulador (maven) + valida CMS
#   scripts/build.sh --emulator    # só o JAR
#   scripts/build.sh --furniture   # converte SWFs -> .nitro (se existirem)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAR_SRC="$ROOT/arcturus"
JAR_DST="$JAR_SRC/Habbo-3.5.5-jar-with-dependencies.jar"

cmd_emulator() {
  echo "== Compilando o emulador (maven) =="
  [ -d "$JAR_SRC/src" ] || { echo "ERRO: $JAR_SRC/src ausente"; exit 1; }
  command -v mvn >/dev/null || { echo "ERRO: maven não instalado (nix develop / mvn)"; exit 1; }
  ( cd "$JAR_SRC" && mvn -q -DskipTests package )
  # o maven gera o jar de deps no target/; copia para o nome que o módulo espera
  if [ ! -f "$JAR_DST" ]; then
    JAR=$(find "$JAR_SRC/target" -name '*-jar-with-dependencies.jar' 2>/dev/null | head -1)
    [ -n "$JAR" ] || { echo "ERRO: jar-with-dependencies não gerado em target/"; exit 1; }
    cp "$JAR" "$JAR_DST"
  fi
  echo "OK: $JAR_DST ($(du -h "$JAR_DST" | cut -f1))"
}

cmd_furniture() {
  echo "== Convertendo furniture (se swf-assets existir) =="
  if [ -x "$ROOT/../habbo-nixos/scripts/convert-furniture.sh" ]; then
    "$ROOT/../habbo-nixos/scripts/convert-furniture.sh" "$ROOT"
  else
    echo "AVISO: convert-furniture.sh não encontrado (habbo-nixos não clonado ao lado) — pule"
  fi
}

cmd_cms() {
  echo "== Validando CMS (composer/vendor + build client) =="
  [ -d "$ROOT/cms/vendor" ] || { echo "AVISO: cms/vendor ausente — rode 'composer install' em cms/"; }
  [ -d "$ROOT/cms/public/client" ] || { echo "AVISO: client não buildado — rode o build do nitro-react em cms/public/client"; }
}

"cmd_${1:-emulator}"