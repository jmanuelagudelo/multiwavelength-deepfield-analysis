
from pathlib import Path
import argparse

from pathlib import Path
import pandas as pd

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sdss_field.csv"
SAMPLE_DATA = ROOT / "data" / "sdss_field.csv"
OUTPUT = ROOT / "resultados" / "color_magnitude_diagram_sdss.png"


def load_data():
    """
    Carga datos del SDSS y, si la consulta falla, utiliza datos de muestra
    """
    df = None

    if DATA.exists():
        try:
            candidate = pd.read_csv(DATA, comment="#")
            if not candidate.empty:
                df = candidate
        except pd.errors.EmptyDataError:
            pass

    if df is not None:
        print(f"Se cargaron {len(df)} registros desde {DATA}.")
    else:
        df = pd.read_csv(SAMPLE_DATA, comment="#")
        print(f"El archivo {DATA} no existe o está vacío. Se cargaron {len(df)} registros de ejemplo desde {SAMPLE_DATA}.")

    required_columns = ["ra", "dec", "u", "g", "z"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Las siguientes columnas requeridas están ausentes en los datos: {', '.join(missing_columns)}")

    return df

def analyse(show=False):
    """
    Limpia los datos, reporta el proceso y genera un diagrama color-magnitud para SDSS.
    """

    df = load_data()
    numeric_columns = ["ra", "dec", "u", "g", "z"]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        invalid_count = df[column].isna().sum()
        print(f"{column}: {invalid_count} valores faltantes o inválidos")

    df['class'] = df['class'].astype('string').str.strip().str.upper()
    duplicate_count = df.duplicated().sum()
    missing_coordinates = df[['ra', 'dec']].isna().any(axis=1).sum()

    #indice de color optico

    df['u_g'] = df['u'] - df['g']

    
    print("Cantidad de objetos por clase SDSS:")
    class_counts = df["class"].value_counts(dropna=False)
    for object_class, count in class_counts.items():
        print(f"{object_class}: {count}")

    #umbral exploratorio para descartar quasares
    red_mask = (df["class"] == "QSO") & (df["u_g"] >= 1.0)
    print(
        " Candidatos QSO rojos (clase QSO y u-g >= 1.0; criterio exploratorio): "
        f"{int(red_mask.sum())}"
    )

    # Solo se excluyen de la figura las filas sin los valores necesarios para dibujar.
    plot_mask = df[["z", "u_g", "class"]].notna().all(axis=1)
    plot_data = df.loc[plot_mask].copy()

    fig, ax = plt.subplots(figsize=(10, 8), facecolor="black")
    ax.set_facecolor("black")

    categories = [
        ("GALAXY", "Galaxias", "#42a5f5", "o", 18),
        ("QSO", "Cuásares", "#ff595e", "^", 28),
        ("STAR", "Estrellas SDSS", "#c7c7c7", ".", 14),
    ]
    for code, label, color, marker, size in categories:
        subset = plot_data[plot_data["class"] == code]
        if not subset.empty:
            ax.scatter(
                subset["u_g"],
                subset["z"],
                s=size,
                alpha=0.7,
                color=color,
                marker=marker,
                label=f"{label} ({len(subset)})",
                edgecolors="none",
            )

    red_qsos = plot_data.loc[red_mask.loc[plot_data.index]]
    if not red_qsos.empty:
        ax.scatter(
            red_qsos["u_g"],
            red_qsos["z"],
            s=85,
            facecolors="none",
            edgecolors="#f15bb5",
            linewidths=1.5,
            label=f"Candidatos QSO rojos (u-g ≥ 1; {len(red_qsos)})",
        )


    ax.set_xlabel("Indice de color u - g (mag)", color="white", labelpad=10)
    ax.set_ylabel("Corrimiento al rojo z", color="white", labelpad=10)
    ax.set_title("SDSS: corrimiento al rojo frente al color", color="white", pad=18)
    ax.tick_params(axis="both", colors="white")

    for spine in ax.spines.values():
        spine.set_color("white")
    ax.grid(color="gray", alpha=0.25)
    ax.legend(facecolor="black", edgecolor="white", labelcolor="white")
    fig.tight_layout()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=300, facecolor=fig.get_facecolor())

    print(f"Gráfica guardada en: {OUTPUT}")

    if show:
        plt.show()
    plt.close(fig)
    return df




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analiza la fotometria y espectroscopia del campo SDSS."
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display a grafica u - g",
    )
    args = parser.parse_args()
    analyse(show=args.show)