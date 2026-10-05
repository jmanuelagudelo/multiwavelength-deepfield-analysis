# Campo PRofundo Multi-Longitudinal de Onda

## 1. Objetivo

Este proyecto estudia el campo ecuatorial centrado en $\mathrm{RA} = 135.5^\circ$, $\mathrm{Dec} = 0.5^\circ$, con radio de $0.5^\circ$. En donde se cruza astrometria y fotometria Gaia DR3 con AllWISE en un radio de 2 arco segundos y consulta los espectros fotometricos del SDSS para el mismo cirulo en 30 min de arco

## Ejecucion

python3 scripts/vizier_data_analysis.py --show cmd
python3 scripts/vizier_data_analysis.py --show motion
python3 scripts/vizier_data_analysis.py --show sky