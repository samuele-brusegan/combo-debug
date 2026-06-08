#!/usr/bin/env bash
# =============================================================================
# Combo-Debug - Download degli asset di terze parti per il funzionamento offline.
#
# La dashboard usa Bootstrap 5 che, di default, e' servito da CDN (jsDelivr).
# Questo script scarica quegli asset in locale (nginx/frontend/vendor/) cosi' la
# dashboard funziona al 100% offline, senza alcuna dipendenza da internet a
# runtime. `index.html` referenzia gia' i percorsi locali: e' sufficiente
# eseguire questo script UNA VOLTA (con connessione) prima della build Docker.
#
# Gli asset scaricati NON sono versionati in git (vedi .gitignore): sono
# riproducibili rieseguendo questo script. L'integrita' dei file principali e'
# verificata contro gli hash SRI (sha384) dichiarati qui sotto.
#
# Uso:
#   ./download-vendor.sh
#
# Requisiti: bash, openssl e uno tra curl o wget.
# =============================================================================
set -euo pipefail

# Versione di Bootstrap da scaricare. Per aggiornarla: cambia questa variabile e
# gli hash SRI sotto (presi da https://getbootstrap.com -> "Include via CDN").
BOOTSTRAP_VERSION="5.3.3"
CDN_BASE="https://cdn.jsdelivr.net/npm/bootstrap@${BOOTSTRAP_VERSION}/dist"

# Directory di destinazione, relativa alla posizione dello script (non al cwd),
# cosi' lo script funziona da qualsiasi directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="${SCRIPT_DIR}/nginx/frontend/vendor/bootstrap"

# Asset da scaricare: "percorso/relativo/al/cdn" -> hash SRI atteso.
# I source map (.map) non hanno un hash di verifica (servono solo ai devtools).
ASSET_PATHS=(
  "css/bootstrap.min.css"
  "css/bootstrap.min.css.map"
  "js/bootstrap.bundle.min.js"
  "js/bootstrap.bundle.min.js.map"
)
declare -A ASSET_SRI=(
  ["css/bootstrap.min.css"]="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
  ["js/bootstrap.bundle.min.js"]="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
)

# --- Utility -----------------------------------------------------------------

die() {
  echo "ERRORE: $*" >&2
  exit 1
}

require() {
  command -v "$1" >/dev/null 2>&1 || die "comando richiesto non trovato: $1"
}

# Scarica $1 (URL) in $2 (file), usando curl o wget.
download() {
  local url="$1" out="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fSL --retry 3 -o "$out" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$out" "$url"
  else
    die "serve curl oppure wget per scaricare gli asset"
  fi
}

# Verifica l'hash SRI sha384 di $1 (file) contro $2 (atteso, es. "sha384-...").
verify_sri() {
  local file="$1" expected="$2"
  local actual
  actual="sha384-$(openssl dgst -sha384 -binary "$file" | openssl base64 -A)"
  [ "$actual" = "$expected" ] || die "SRI non valido per ${file}
  atteso:   ${expected}
  ottenuto: ${actual}"
}

# --- Esecuzione --------------------------------------------------------------

require openssl

echo "Scarico Bootstrap ${BOOTSTRAP_VERSION} in: ${VENDOR_DIR}"

for path in "${ASSET_PATHS[@]}"; do
  url="${CDN_BASE}/${path}"
  dest="${VENDOR_DIR}/${path}"
  mkdir -p "$(dirname "$dest")"
  echo "  - ${path}"
  download "$url" "$dest"
  sri="${ASSET_SRI[$path]:-}"
  if [ -n "$sri" ]; then
    verify_sri "$dest" "$sri"
    echo "    SRI verificato."
  fi
done

echo "Fatto. Gli asset offline sono in nginx/frontend/vendor/bootstrap/."
echo "Ora puoi buildare normalmente (./build.sh): nessuna dipendenza da CDN."
