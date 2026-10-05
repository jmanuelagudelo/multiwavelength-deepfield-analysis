"""Limpieza, resumen y gráfico z frente a u-g para SDSS."""
from pathlib import Path
import argparse

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "gaia_allwise.csv"
SAMPLE_DATA = ROOT / "data" / "gaia_allwise.csv"
OUTPUT = ROOT / "resultados" / "color_magnitude_diagram.png"


def analyse(show=False):
    """CLasifica las fuentes, reporta el procesos y genera un diagrama color-magnitud."""

    source = DATA
    df = None
    if DATA.exists() and DATA.stat().st_size > 10:
        try:
            downloaded_df = pd.read_csv(DATA)
            if not downloaded_df.empty:
                df = downloaded_df
            else:
                print(f"El archivo de datos {DATA} está vacío. Se usará un conjunto de datos de ejemplo.")
        except pd.errors.EmptyDataError:
            print(f"El archivo de datos {DATA} no se pudo leer. Se usará un conjunto de datos de ejemplo.")
    else:
        print(f"El archivo de datos {DATA} no existe o está vacío. Se usará un conjunto de datos de ejemplo.")

    if df is None:
        try:
            df = pd.read_csv(SAMPLE_DATA)
            print(f"Se cargó un conjunto de datos de ejemplo desde {SAMPLE_DATA}.")
        except pd.errors.EmptyDataError:
            raise FileNotFoundError(
                f"El archivo de datos de ejemplo {SAMPLE_DATA} no existe o está vacío. "
                "Ejecute primero el script main.sh para obtener los datos."
            )
    else:
        print(f"Se cargaron {len(df)} registros desde {source}.")

    numeric_columns = [
        "RA_ICRS", "DE_ICRS", "Teff","Plx",
        "pmRA", "pmDE", "Gmag", "W1mag"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        invalid_count = df[column].isna().sum()
        print(f"{column}: {invalid_count} valores faltantes o inválidos")


    # Duplicados y coordenadas faltantes
    duplicate_count = df["DR3Name"].duplicated(keep=False).sum()
    missing_coordinates = df[["RA_ICRS", "DE_ICRS"]].isna().any(axis=1).sum()


    # Clasificacion preliminar 
    df["class"] = "Sin clasificar"
    positive_parallax = df["Plx"] > 0
    df.loc[positive_parallax, "class"] = ("Estrella candidata de la Vía Láctea")


    # Resumen

    print("Clasificación preliminar:")
    print("Paralaje positivo: estrella candidata de la Vía Láctea.")
    print("Gaia-AllWISE no contiene clase espectroscópica ni corrimiento al rojo, por lo que no se puede clasificar cuásares ni otras galaxias.")

    class_counts = df["class"].value_counts(dropna=False)
    for class_name, count in class_counts.items():
        print(f"{class_name}: {count}")

    ## Movimiento propio
    df['pm_total'] = (df['pmRA']**2 + df['pmDE']**2)**0.5


    # ----------------------------------------#
    #    Diagrama color-magnitud: z vs u-g    #
    # ----------------------------------------#

    cmd_mask = ((df['class'] == 'Estrella candidata de la Vía Láctea') &
                df['Gmag'].notna() & df['W1mag'].notna())

    cmd_data = df.loc[cmd_mask].copy()
    cmd_data["G_W1"] = cmd_data["Gmag"] - cmd_data["W1mag"]
    cmd_data["M_G"] = (cmd_data["Gmag"] + 5 * np.log10(cmd_data["Plx"])- 10)

    # Luminosidad relativa

    cmd_data["L_G"] = 10 ** (0.4 * (4.66 - cmd_data["M_G"]))

    print(f"Generando diagrama color-magnitud para {len(cmd_data)} estrellas candidatas de la Vía Láctea.")

    fig_cmd, ax = plt.subplots(figsize=(10, 8), facecolor="black")
    ax.set_facecolor("black")

    points = ax.scatter(
        cmd_data["G_W1"],
        cmd_data["L_G"],
        c=cmd_data["Teff"],
        cmap="plasma",
        s=9,
        alpha=0.75,
        linewidths=0,
    )

    # Eje izquierdo: luminosidad aproximada en la banda G.
    ax.set_yscale("log")
    ax.set_xlabel("Color G - W1 (mag)", color="white", labelpad=10)
    ax.set_ylabel(r"Luminosidad en banda G", color="yellow")
    ax.set_title("Diagrama color-magnitud Gaia–AllWISE", color="white", pad=35)


    # Estilo oscuro.
    ax.tick_params(axis="both", colors="white")
    for spine in ax.spines.values():
        spine.set_color("white")
    ax.grid(color="gray", alpha=0.25)



    right_axis = ax.twinx()
    right_axis.set_yscale("log")
    right_axis.set_ylim(ax.get_ylim())


    magnitude_ticks = np.arange(-5, 16, 5)
    luminosity_ticks = 10 ** (
        0.4 * (4.66 - magnitude_ticks)
    )


    ymin, ymax = ax.get_ylim()
    valid_ticks = ((luminosity_ticks >= ymin) & (luminosity_ticks <= ymax))

    right_axis.set_yticks(luminosity_ticks[valid_ticks])
    right_axis.set_yticklabels([
        f"{magnitude:.0f}"
        for magnitude in magnitude_ticks[valid_ticks]
    ])

    right_axis.set_ylabel(
        r"Magnitud absoluta $M_G$ (mag)",
        color="yellow",
        labelpad=12,
    )

    right_axis.tick_params(
        axis="y",
        colors="white",
        direction="out",
    )

    right_axis.spines["right"].set_color("white")

    # Eje superior: medianas observadas de temperatura por intervalos de G-W1.
    # Se muestra como orientación, porque polvo y otras propiedades también afectan el color.
    valid_temperature = cmd_data.dropna(subset=["Teff", "G_W1"])
    if len(valid_temperature) >= 10:
        color_bins = np.linspace(
            valid_temperature["G_W1"].min(),
            valid_temperature["G_W1"].max(),
            8,
        )
        valid_temperature = valid_temperature.copy()
        valid_temperature["color_bin"] = pd.cut(
            valid_temperature["G_W1"],
            bins=color_bins,
            include_lowest=True,
        )

        temperature_by_color = (
            valid_temperature.groupby("color_bin", observed=True)
            .agg(
                color=("G_W1", "median"),
                temperature=("Teff", "median"),
            )
            .dropna()
        )

    def spectral_type(temperature):
        if temperature >= 30000:
            return "O"
        if temperature >= 10000:
            return "B"
        if temperature >= 7500:
            return "A"
        if temperature >= 6000:
            return "F"
        if temperature >= 5200:
            return "G"
        if temperature >= 3700:
            return "K"
        return "M"

    top_axis = ax.twiny()
    top_axis.set_xlim(ax.get_xlim())
    top_axis.set_xticks(temperature_by_color["color"])
    top_axis.set_xticklabels([
        f"{spectral_type(temp)}\n{temp:.0f} K"
        for temp in temperature_by_color["temperature"]
    ])
    top_axis.set_xlabel(
        "Tipo espectral y temperatura aproximados (de Gaia Teff)",
        color="white",
        labelpad=8,
    )
    top_axis.tick_params(colors="white")
    for spine in top_axis.spines.values():
        spine.set_color("white")

    fig_cmd.tight_layout()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig_cmd.savefig(
        OUTPUT,
        dpi=300,
        facecolor=fig_cmd.get_facecolor()
    )


    if show:
        plt.show()

    plt.close(fig_cmd)

    print(f"Diagrama guardado en: {OUTPUT.parent.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analiza datos de Gaia-AllWISE y genera diagramas."
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Muestra el diagrama color-magnitud",
    )

    args = parser.parse_args()
    analyse(show=args.show)