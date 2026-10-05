from pathlib import Path

import webbrowser
import numpy as np
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]

MATCH_RADIUS_ARCSEC = 2.0
GAIA_DATA = ROOT / "data" / "gaia_allwise.csv"
GAIA_SAMPLE = ROOT / "sample_data" / "gaia_allwise.csv"

SDSS_DATA = ROOT / "data" / "sdss_field.csv"
SDSS_SAMPLE = ROOT / "sample_data" / "sdss_field.csv"

RESULTS = ROOT / "resultados"
OUTPUT_HTML = RESULTS / "combined_catalogs_interactive.html"
OUTPUT_CSV = RESULTS / "combined_catalog.csv"


CLASS_COLORS = {
    "Estrella candidata de la Via Lactea": "#f4c542",
    "Estrella SDSS": "#f4c542",
    "Galaxia SDSS": "#42a5f5",
    "Cuasar SDSS": "#ff595e",
    "Sin clasificar": "#b0bec5",
}

def read_csv(data_path, sample_path, label, comment=None):
    """Prefiere la descarga y usa sample_data si falta o no contiene filas."""
    df = None
    source = data_path

    try:
        candidate = pd.read_csv(data_path, comment=comment)
        if not candidate.empty:
            df = candidate
        else:
            print(f"Aviso: {data_path} no contiene filas. Usando sample_data")
    except (FileNotFoundError, pd.errors.EmptyDataError) as e:
        print(f"No se pudo leer {data_path} ({e}). Usando sample_data")

    if df is None:
        df = pd.read_csv(sample_path, comment=comment)
        source = sample_path
        print(f"Datos de {label} cargados exitosamente desde: {sample_path}")

    return df

def angular_separation_arcsec(ra1, dec1, ra2, dec2):
    """
    Calcula las separaciones esfericas en segundos de arco
    """

    ra1 = np.radians(np.asarray(ra1, dtype=float))[:, None]
    dec1 = np.radians(np.asarray(dec1, dtype=float))[:, None]

    ra2 = np.radians(np.asarray(ra2, dtype=float))[None, :]
    dec2 = np.radians(np.asarray(dec2, dtype=float))[None, :]

    delta_ra = ra2 - ra1
    delta_dec = dec2 - dec1

    hav = (np.sin(delta_dec / 2.0) ** 2 + np.cos(dec1) * np.cos(dec2) * np.sin(delta_ra / 2.0) ** 2)
    hav = np.clip(hav, 0.0, 1.0)
    return 2.0 * np.arcsin(np.sqrt(hav)) * (180.0 / np.pi) * 3600.0


def make_crossmath(gaia,sdss, radius_arcsec=MATCH_RADIUS_ARCSEC):
    """
    Comparamos uno a uno los objetos para identificarlos en una sola tabla
    """

    gaia_valid = gaia.dropna(subset=["RA_ICRS", "DE_ICRS"])
    sdss_valid = sdss.dropna(subset=["ra", "dec"])


    sdss_ra = sdss_valid["ra"].to_numpy(dtype=float)
    sdss_dec = sdss_valid["dec"].to_numpy(dtype=float)

    sdss_indices = sdss_valid.index.to_numpy()
    gaia_indices = gaia_valid.index.to_numpy()

    candidate_pairs = []
    for star in range(0, len(gaia_valid), 256):
        block = gaia_valid.iloc[star:star + 256]
        separation = angular_separation_arcsec(
            block['RA_ICRS'], block['DE_ICRS'],
            sdss_ra, sdss_dec
        )
        gaia_bloc_id = block.index.to_numpy()
        rows, cols = np.where(separation <= radius_arcsec)
        candidate_pairs.extend(
            (float(separation[row, col]), gaia_bloc_id[row], sdss_indices[col])
            for row, col in zip(rows, cols)
        )

    #Si vairas fuentes quedan dentro del radio se prioriza la mas cercana
    candidate_pairs.sort(key=lambda pair: pair[0])
    used_gaia = set()
    used_sdss = set()
    pairs = []
    for separation, gaia_index, sdss_index in candidate_pairs:
        if gaia_index in used_gaia or sdss_index in used_sdss:
            continue
        pairs.append((gaia_index, sdss_index, separation))
        used_gaia.add(gaia_index)
        used_sdss.add(sdss_index)

    records = []
    for gaia_index, sdss_index, separation in pairs:
        record = {f"gaia_{key}": value for key, value in gaia.loc[gaia_index].items()}
        record.update({f"sdss_{key}": value for key, value in sdss.loc[sdss_index].items()})
        record["match_sep_arcsec"] = separation
        record["match_status"] = "Emparejado"
        records.append(record)

    for gaia_index in gaia.index.difference(used_gaia):
        record = {f"gaia_{key}": value for key, value in gaia.loc[gaia_index].items()}
        record.update({f"sdss_{key}": np.nan for key in sdss.columns})
        record["match_sep_arcsec"] = np.nan
        record["match_status"] = "Solo Gaia"
        records.append(record)

    for sdss_index in sdss.index.difference(used_sdss):
        record = {f"gaia_{key}": np.nan for key in gaia.columns}
        record.update({f"sdss_{key}": value for key, value in sdss.loc[sdss_index].items()})
        record["match_sep_arcsec"] = np.nan
        record["match_status"] = "Solo SDSS"
        records.append(record)

    combined = pd.DataFrame.from_records(records)
    return combined, len(pairs), len(candidate_pairs)

def classify_sources(combined):
    """
    Combinamos clase espectroscopia SDSS con astrometria GAIA
    """

    sdss_class = combined.get("sdss_class", pd.Series(index=combined.index, dtype="object"))
    sdss_class = sdss_class.astype("string").str.strip().str.upper()
    parallax = pd.to_numeric(combined.get("gaia_Plx"), errors="coerce")

    combined["combined_class"] = "Sin clasificar"
    combined.loc[sdss_class == "GALAXY", "combined_class"] = "Galaxia SDSS"
    combined.loc[sdss_class == "QSO", "combined_class"] = "Cuasar SDSS"
    combined.loc[sdss_class == "STAR", "combined_class"] = "Estrella SDSS"

    no_sdss_class = ~sdss_class.isin(["GALAXY", "QSO", "STAR"])
    combined.loc[
        no_sdss_class & (parallax > 0), "combined_class"
    ] = "Estrella candidata de la Vía Láctea"

    combined["astrometry_conflict"] = (
        sdss_class.isin(["GALAXY", "QSO"])
        & (parallax > 0)
    )
    return combined

def add_view_traces(fig, combined, view):
    """Añade las trazas de una vista; devuelve sus índices para el selector."""
    categories = list(CLASS_COLORS)
    trace_indices = []

    if view == "map":
        ra = pd.to_numeric(combined.get("gaia_RA_ICRS"), errors="coerce").fillna(
            pd.to_numeric(combined.get("sdss_ra"), errors="coerce")
        )
        dec = pd.to_numeric(combined.get("gaia_DE_ICRS"), errors="coerce").fillna(
            pd.to_numeric(combined.get("sdss_dec"), errors="coerce")
        )
        eligible = ra.notna() & dec.notna()
        for category in categories:
            subset = combined.loc[eligible & (combined["combined_class"] == category)]
            fig.add_trace(go.Scatter(
                x=ra.loc[subset.index], y=dec.loc[subset.index],
                mode="markers", name=category, legendgroup=category,
                marker=dict(color=CLASS_COLORS[category], size=8, opacity=0.75),
                customdata=np.column_stack([
                    subset["match_status"].astype(str),
                    subset["match_sep_arcsec"].astype(str),
                    subset.get("gaia_DR3Name", pd.Series(index=subset.index, dtype="object")).astype(str),
                    subset.get("sdss_z", pd.Series(index=subset.index, dtype="float64")),
                    subset["astrometry_conflict"].astype(str),
                ]),
                hovertemplate=(
                    "RA=%{x:.5f}°<br>Dec=%{y:.5f}°"
                    "<br>Clase=%{fullData.name}<br>Estado=%{customdata[0]}"
                    "<br>Separación=%{customdata[1]}″<br>Gaia=%{customdata[2]}"
                    "<br>z SDSS=%{customdata[3]}"
                    "<br>Conflicto astrométrico=%{customdata[4]}<extra></extra>"
                ),
                showlegend=True,
                visible=True,
            ))
            trace_indices.append(len(fig.data) - 1)

    elif view == "gaia":
        plx = pd.to_numeric(combined.get("gaia_Plx"), errors="coerce")
        pmra = pd.to_numeric(combined.get("gaia_pmRA"), errors="coerce")
        pmde = pd.to_numeric(combined.get("gaia_pmDE"), errors="coerce")
        pm_total = np.sqrt(pmra ** 2 + pmde ** 2)
        eligible = plx.notna() & pm_total.notna() & (plx > 0) & (pm_total > 0)
        for category in categories:
            subset = combined.loc[eligible & (combined["combined_class"] == category)]
            fig.add_trace(go.Scatter(
                x=plx.loc[subset.index], y=pm_total.loc[subset.index],
                mode="markers", name=category, legendgroup=category,
                marker=dict(color=CLASS_COLORS[category], size=8, opacity=0.75),
                customdata=np.column_stack([
                    subset["match_status"].astype(str),
                    subset.get("sdss_class", pd.Series(index=subset.index, dtype="object")).astype(str),
                    subset.get("sdss_z", pd.Series(index=subset.index, dtype="float64")),
                ]),
                hovertemplate=(
                    "Paralaje=%{x:.3f} mas<br>Movimiento total=%{y:.3f} mas/año"
                    "<br>Clase combinada=%{fullData.name}<br>Estado=%{customdata[0]}"
                    "<br>Clase SDSS=%{customdata[1]}<br>z=%{customdata[2]}<extra></extra>"
                ),
                showlegend=True,
                visible=False,
            ))
            trace_indices.append(len(fig.data) - 1)

    else:  # vista SDSS: z frente a u-g
        sdss_class = combined.get("sdss_class", pd.Series(index=combined.index, dtype="object"))
        z = pd.to_numeric(combined.get("sdss_z"), errors="coerce")
        u = pd.to_numeric(combined.get("sdss_u"), errors="coerce")
        g = pd.to_numeric(combined.get("sdss_g"), errors="coerce")
        u_g = u - g
        eligible = z.notna() & u_g.notna()
        sdss_categories = {
            "GALAXY": ("Galaxia SDSS", "#42a5f5", "circle"),
            "QSO": ("Cuásar SDSS", "#ff595e", "triangle-up"),
            "STAR": ("Estrella SDSS", "#c7c7c7", "circle-open"),
        }
        for code, (category, color, symbol) in sdss_categories.items():
            subset = combined.loc[eligible & (sdss_class == code)]
            is_red_qso = (code == "QSO") & (u_g.loc[subset.index] >= 1.0)
            symbols = np.where(is_red_qso, "diamond", symbol)
            fig.add_trace(go.Scatter(
                x=u_g.loc[subset.index], y=z.loc[subset.index],
                mode="markers", name=category, legendgroup=category,
                marker=dict(color=color, size=9, opacity=0.75, symbol=symbols),
                customdata=np.column_stack([
                    subset["match_status"].astype(str),
                    subset["match_sep_arcsec"].astype(str),
                    subset.get("gaia_Plx", pd.Series(index=subset.index, dtype="float64")),
                    subset.get("gaia_pmRA", pd.Series(index=subset.index, dtype="float64")),
                    subset.get("gaia_pmDE", pd.Series(index=subset.index, dtype="float64")),
                ]),
                hovertemplate=(
                    "u−g=%{x:.3f} mag<br>z=%{y:.4f}"
                    "<br>Clase espectroscópica=%{fullData.name}"
                    "<br>Estado=%{customdata[0]}<br>Separación=%{customdata[1]}″"
                    "<br>Paralaje Gaia=%{customdata[2]} mas"
                    "<br>pmRA=%{customdata[3]} mas/año"
                    "<br>pmDE=%{customdata[4]} mas/año<extra></extra>"
                ),
                showlegend=True,
                visible=False,
            ))
            trace_indices.append(len(fig.data) - 1)

    return trace_indices

def main():
    gaia = read_csv(
        GAIA_DATA,
        GAIA_SAMPLE,
        "Gaia-AllWISE",
    )

    sdss = read_csv(
        SDSS_DATA,
        SDSS_SAMPLE,
        "SDSS",
        comment="#",
    )
    gaia_required = {"RA_ICRS", "DE_ICRS", "Plx", "pmRA", "pmDE", "Gmag", "W1mag"}
    sdss_required = {"ra", "dec", "class", "z", "u", "g"}
    missing_gaia = gaia_required.difference(gaia.columns)
    missing_sdss = sdss_required.difference(sdss.columns)
    if missing_gaia:
        raise ValueError("Faltan columnas en Gaia–AllWISE: " + ", ".join(sorted(missing_gaia)))
    if missing_sdss:
        raise ValueError("Faltan columnas en SDSS: " + ", ".join(sorted(missing_sdss)))

    for column in ["RA_ICRS", "DE_ICRS", "Plx", "pmRA", "pmDE", "Gmag", "W1mag", "Teff"]:
        if column in gaia:
            gaia[column] = pd.to_numeric(gaia[column], errors="coerce")
    for column in ["ra", "dec", "z", "u", "g"]:
        sdss[column] = pd.to_numeric(sdss[column], errors="coerce")
    sdss["class"] = sdss["class"].astype("string").str.strip().str.upper()

    # Una fila por objeto Gaia; si el cruce con AllWISE produjo varias filas,
    # prioriza la que sí tenga W1 disponible. El CSV original no se modifica.
    if "DR3Name" in gaia.columns:
        duplicates = gaia["DR3Name"].duplicated(keep=False).sum()
        if duplicates:
            print(f"Aviso: {duplicates} filas Gaia tienen DR3Name repetido; se usa una fila por fuente.")
            gaia = (
                gaia.assign(_has_w1=gaia["W1mag"].notna())
                .sort_values("_has_w1", ascending=False)
                .drop_duplicates(subset="DR3Name", keep="first")
                .drop(columns="_has_w1")
            )

    sdss_duplicates = sdss.duplicated(subset=["ra", "dec", "class", "z"], keep=False).sum()
    if sdss_duplicates:
        print(f"Aviso: {sdss_duplicates} filas SDSS duplicadas por posición/clase/z; se conserva una por registro.")
        sdss = sdss.drop_duplicates(subset=["ra", "dec", "class", "z"], keep="first")

    # Restablecer índices para que los identificadores de pareja sean simples y únicos.
    gaia = gaia.reset_index(drop=True)
    sdss = sdss.reset_index(drop=True)
    combined, match_count, candidate_count = make_crossmath(gaia, sdss)
    combined = classify_sources(combined)

    print("\nResumen del cruce espacial:")
    print(f"  Radio máximo: {MATCH_RADIUS_ARCSEC:.1f} arcsec")
    print(f"  Parejas candidatas dentro del radio: {candidate_count}")
    print(f"  Asociaciones uno a uno aceptadas: {match_count}")
    print(f"  Fuentes Gaia: {len(gaia)}; fuentes SDSS: {len(sdss)}")
    print(f"  Filas en el catálogo combinado (incluye fuentes sin pareja): {len(combined)}")
    print("\nObjetos por clasificación combinada:")
    print(combined["combined_class"].value_counts(dropna=False).to_string())
    conflicts = int(combined["astrometry_conflict"].sum())
    print(f"\nCoincidencias QSO/galaxia con paralaje Gaia positivo para revisar: {conflicts}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_CSV, index=False)
    print(f"Catálogo combinado guardado en: {OUTPUT_CSV}")

    fig = go.Figure()
    map_indices = add_view_traces(fig, combined, "map")
    gaia_indices = add_view_traces(fig, combined, "gaia")
    sdss_indices = add_view_traces(fig, combined, "sdss")

    total_traces = len(fig.data)
    map_visible = [i in map_indices for i in range(total_traces)]
    gaia_visible = [i in gaia_indices for i in range(total_traces)]
    sdss_visible = [i in sdss_indices for i in range(total_traces)]
    buttons = [
        dict(
            label="Mapa combinado",
            method="update",
            args=[{"visible": map_visible}, {
                "title": "Gaia + SDSS: posiciones y resultado del cruce",
                "xaxis.title": "Ascensión recta (grados)",
                "yaxis.title": "Declinación (grados)",
                "yaxis.type": "linear",
                "yaxis.autorange": True,
                "xaxis.autorange": "reversed",
            }],
        ),
        dict(
            label="Astrometría Gaia",
            method="update",
            args=[{"visible": gaia_visible}, {
                "title": "Gaia: paralaje frente a movimiento propio total",
                "xaxis.title": "Paralaje (mas)",
                "yaxis.title": "Movimiento propio total (mas/año; escala logarítmica)",
                "yaxis.type": "log",
                "yaxis.autorange": True,
                "xaxis.type": "linear",
                "xaxis.autorange": True,
            }],
        ),
        dict(
            label="Espectroscopía SDSS",
            method="update",
            args=[{"visible": sdss_visible}, {
                "title": "SDSS: corrimiento al rojo frente a color u−g",
                "xaxis.title": "Índice de color u−g (mag)",
                "yaxis.title": "Corrimiento al rojo z",
                "yaxis.type": "linear",
                "yaxis.autorange": True,
                "xaxis.type": "linear",
                "xaxis.autorange": True,
            }],
        ),
    ]

    fig.update_layout(
        title="Gaia + SDSS: posiciones y resultado del cruce",
        template="plotly_dark",
        xaxis_title="Ascensión recta (grados)",
        yaxis_title="Declinación (grados)",
        xaxis=dict(autorange="reversed"),
        updatemenus=[dict(
            type="dropdown", direction="down", x=1.0, y=1.16,
            xanchor="right", buttons=buttons,
        )],
        legend=dict(groupclick="togglegroup"),
        annotations=[dict(
            text=(
                f"Cruce posicional ≤ {MATCH_RADIUS_ARCSEC:g}″ · "
                f"{match_count} asociaciones aceptadas · "
                "QSO/galaxia con Plx>0 se marca como posible conflicto a revisar"
            ),
            x=0, y=-0.16, xref="paper", yref="paper",
            showarrow=False, align="left",
        )],
    )

    fig.write_html(OUTPUT_HTML, include_plotlyjs=True, full_html=True)
    webbrowser.open(OUTPUT_HTML.resolve().as_uri())
    print(f"Gráfica interactiva guardada en: {OUTPUT_HTML}")
    fig.show()

if __name__ == "__main__":
    main()
