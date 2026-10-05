import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

"""
Analizaremos los datos descargados de VizieR, en donde, cartografiaremos el campo profundo
en unas coordenadas específicas, y realizaremos una limpieza básica de los datos, para posteriormente
seleccionar las fuentes candidatas a pertenecer a la Vía Láctea, mediante el paralaje
"""
df = pd.read_csv("data/gaia_allwise.csv")

print("Valores faltantes por columna:")
print(df.isna().sum())

# 2. Convertir las columnas numéricas
numeric_columns = [
    "RA_ICRS", "DE_ICRS", "Plx",
    "pmRA", "pmDE", "Gmag", "W1mag"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors='coerce')

df = df.drop_duplicates(subset=["DR3Name"]).copy()

df_clean = df.dropna(
    subset=["RA_ICRS", "DE_ICRS", "Gmag"]
).copy()

print("\nDimensiones después de la limpieza básica:", df_clean.shape)
print("\nValores faltantes después de la limpieza:")
print(df_clean.isna().sum())

# Selección preliminar de fuentes con paralaje positivo
galactic_candidates = df_clean[
    df_clean["Plx"] > 0
].copy()

print(
    "\nFuentes con paralaje positivo:",
    len(galactic_candidates)
)

print(
    "Fuentes descartadas por paralaje no positivo "
    "o faltante:",
    len(df_clean) - len(galactic_candidates)
)


####

# Seleccionar fuentes con los datos necesarios para el diagrama
cmd_data = galactic_candidates.dropna(
    subset=["Gmag", "W1mag"]
).copy()

# Calcular el índice de color óptico-infrarrojo
cmd_data["G_W1"] = cmd_data["Gmag"] - cmd_data["W1mag"]

print("\nFuentes disponibles para el diagrama:", len(cmd_data))

# Crear el diagrama color-magnitud
fig, ax = plt.subplots(figsize=(9, 7))

scatter = ax.scatter(
    cmd_data["G_W1"],
    cmd_data["Gmag"],
    s=8,
    alpha=0.6
)

ax.set_xlabel(r"$G-W1$ (mag)")
ax.set_ylabel(r"$G$ (mag)")
ax.set_title("Diagrama color-magnitud óptico-infrarrojo")

# En astronomía, las magnitudes más brillantes se representan arriba
ax.invert_yaxis()

ax.grid(alpha=0.2)
fig.tight_layout()
fig.savefig("../resultados/color_magnitude_diagram.png", dpi=300)
plt.show()