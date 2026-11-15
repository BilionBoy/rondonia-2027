#!/usr/bin/env bash
# Copia a tela "Custo da máquina" gerada por maquina/build_maquina.py para o clone local do SIPRE.
# Uso: bash maquina/copiar_para_sipre.sh   (depois: testes do Observatório no SIPRE e deploy conforme o README do SIPRE)
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
SIPRE="${SIPRE:-$AQUI/../../../sipre}"
for f in "$AQUI/sipre/custo_da_maquina.html.erb" "$AQUI/sipre/maquina.js"; do
  [ -f "$f" ] || { echo "falta $f: rode antes python3 maquina/build_maquina.py" >&2; exit 1; }
done
cp "$AQUI/sipre/custo_da_maquina.html.erb" "$SIPRE/app/views/observatorio/custo_da_maquina.html.erb"
cp "$AQUI/sipre/maquina.js" "$SIPRE/lib/observatorio/maquina.js"
echo "copiado para $SIPRE: app/views/observatorio/custo_da_maquina.html.erb e lib/observatorio/maquina.js"
