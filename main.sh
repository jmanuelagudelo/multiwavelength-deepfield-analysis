set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
mkdir -p data resultados

echo "Extrayendo datos de VizieR y SDSS"

bash scripts/extract_sdss.sh
bash scripts/extract_vizier.sh

### limpieza de datos
python3 scripts/vizier_data_analysis.py

read -r -p "¿Deseas visualizar el diagrama color magnitud? (y/N): " respuesta
if [[ $respuesta =~ ^[yY]$ ]]; then
    python3 scripts/vizier_data_analysis.py --show
fi

read -r -p "¿Deseas visualizar el diagrama de corrimiento al rojo y color de SDSS? (y/N):" respuesta_sdss
if [[ $respuesta_sdss =~ ^[yY]$ ]]; then
    python3 scripts/sdss_data_analysis.py --show
fi

#python3 scripts/sdss_data_analysis.py