set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SQL="
SELECT
    s.ra,
    s.dec,
    s.class,
    s.z,
    p.modelMag_u AS u,
    p.modelMag_g AS g
FROM SpecObj AS s
INNER JOIN PhotoObjAll AS p
    ON s.bestObjID = p.objID
WHERE
    s.ra BETWEEN 135.0 AND 136.0
    AND s.dec BETWEEN 0.0 AND 1.0
    AND dbo.fDistanceArcMinEq(s.ra, s.dec, 135.5, 0.5) <= 30.0
"

URL="https://skyserver.sdss.org/dr18/SkyServerWS/SearchTools/SqlSearch"
curl --fail --get \
    --data-urlencode "format=csv" \
    --data-urlencode "cmd=$SQL" \
    "$URL" \
    -o data/sdss_field.csv