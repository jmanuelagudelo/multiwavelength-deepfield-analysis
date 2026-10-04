
#!/bin/bash

set -e

echo "1. Consultando VizieR TAP mediante ADQL..."

mkdir -p data

ADQL="
SELECT TOP 10
    g.DR3Name,
    g.RA_ICRS,
    g.DE_ICRS,
    g.Gmag
FROM \"I/355/gaiadr3\" AS g
WHERE 1 = CONTAINS(
    POINT('ICRS', g.RA_ICRS, g.DE_ICRS),
    CIRCLE('ICRS', 135.5, 0.5, 0.5)
)"

ADQL2="
SELECT TOP 10
    w.RAJ2000,
    w.DEJ2000,
    w.W1mag
FROM \"II/328/allwise\" AS w
WHERE 1 = CONTAINS(
    POINT('ICRS', w.RAJ2000, w.DEJ2000),
    CIRCLE('ICRS', 135.5, 0.5, 0.5)
)"

# Codificamos los espacios como '+', siguiendo el ejemplo del profesor
URL_ADQL=$(echo $ADQL2 | sed 's/ /+/g')

# Endpoint TAP de VizieR
TAP_URL="https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync?request=doQuery&lang=ADQL&format=csv&query="

echo "2. Descargando resultados..."

wget -O data/gaia_allwise.csv "$TAP_URL$URL_ADQL"

echo "3. Verificando el archivo descargado..."
head -n 5 data/gaia_allwise.csv

echo "Proceso de extracción finalizado."
