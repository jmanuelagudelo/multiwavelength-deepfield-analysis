# Campo PRofundo Multi-Longitudinal de Onda

## 1. Objetivo

Este proyecto estudia el campo ecuatorial centrado en $\mathrm{RA} = 135.5^\circ$, $\mathrm{Dec} = 0.5^\circ$, con radio de $0.5^\circ$. En donde se cruza astrometria y fotometria Gaia DR3 con AllWISE en un radio de 2 arco segundos y consulta los espectros fotometricos del SDSS para el mismo cirulo en 30 min de arco

se utilizan:

- **GaIA DR3**: En donde se almacenan posiciones, paralajes, movimientos propios, magnitud optica `Gmag` y la temperatura efectiva `T_eff`
- **AllWISE**: En donde se almacena la magnitud infrarroja W1 `W1mag` asociada espacialmente a los datos de GAIA
- **SDSS**: En donde se almacena la clasificacion espectroscopica `class`, el corrimiento al rojo `z` y las magnitudes `u` y `g`



## 3. Ejecución

Desde la raíz del proyecto, ejecuta:

```bash
bash main.sh
```


Se requiere Bash, Python 3 y las bibliotecas `pandas`, `numpy` y `matplotlib`. Para ejecutar las consultas se requieren `wget` (VizieR) y `curl` (SDSS). La opción interactiva necesita además `plotly`.

### Modo de datos actual