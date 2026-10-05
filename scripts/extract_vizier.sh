set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "1. Consultando VizieR TAP mediante ADQL..."

ADQL="
SELECT
    g.DR3Name,
    g.RA_ICRS,
    g.DE_ICRS,
    g.Teff,
    g.Plx,
    g.pmRA,
    g.pmDE,
    g.Gmag,
    w.W1mag
FROM \"I/355/gaiadr3\" AS g
LEFT JOIN \"II/328/allwise\" AS w
    ON 1 = CONTAINS(
        POINT('ICRS', g.RA_ICRS, g.DE_ICRS),
        CIRCLE(
            'ICRS',
            w.RAJ2000,
            w.DEJ2000,
            2.0 / 3600.0
        )
    )
WHERE 1 = CONTAINS(
    POINT('ICRS', g.RA_ICRS, g.DE_ICRS),
    CIRCLE('ICRS', 135.5, 0.5, 0.5)
)
"

# Codificamos los espacios como '+', siguiendo el ejemplo del profesor
URL_ADQL=$(echo $ADQL | sed 's/ /+/g')

# Endpoint TAP de VizieR
TAP_URL="https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync?request=doQuery&lang=ADQL&format=csv&query="

wget -O ../data/gaia_allwise.csv "$TAP_URL$URL_ADQL"

#####


