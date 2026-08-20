"""
Réplica fiel, en forma de funciones cacheadas para Streamlit, de la lógica de
`notebooks/01_turismo_vivienda_analisis.ipynb` (H1-H6 + extensión DBSCAN).

No se cambia ningún cálculo respecto al notebook: se reorganiza el mismo código
en funciones puras + `st.cache_data` / `st.cache_resource` para que el
dashboard no tenga que re-descargar ni re-procesar nada en cada rerun.
"""
from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from shapely import STRtree
from shapely.geometry import Point, Polygon, shape

# ---------------------------------------------------------------------------
# Rutas (mismo layout relativo que usa el notebook: data/raw, data/processed)
# ---------------------------------------------------------------------------


def _find_dir(name: str) -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        Path(name),
        Path("..") / name,
        here.parent / name,
        here.parent.parent / name,
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    return (here.parent / name).resolve()


RAW = _find_dir("data/raw/turismo_vivienda")
PROCESSED = _find_dir("data/processed")

REQUIRED_FILES = [
    "vivienda_turistica_actual.geojson",
    "vivienda_turistica_2023.geojson",
    "zit_actual.geojson",
    "hogares_viviendas_localidad_2018_2035.ods",
    "localidades_bogota.geojson",
    "avaluo_catastral_ph_manzana_actual.geojson",
    "alojamiento_turistico_actual.geojson",
    "gastronomia_bar_actual.geojson",
]


def datos_disponibles() -> bool:
    return all((RAW / f).exists() for f in REQUIRED_FILES)


# ---------------------------------------------------------------------------
# Utilidades (idénticas al notebook)
# ---------------------------------------------------------------------------

LOC_CODE_TO_NAME = {
    1: "Usaquén", 2: "Chapinero", 3: "Santa Fe", 4: "San Cristóbal", 5: "Usme",
    6: "Tunjuelito", 7: "Bosa", 8: "Kennedy", 9: "Fontibón", 10: "Engativá",
    11: "Suba", 12: "Barrios Unidos", 13: "Teusaquillo", 14: "Los Mártires",
    15: "Antonio Nariño", 16: "Puente Aranda", 17: "La Candelaria",
    18: "Rafael Uribe Uribe", 19: "Ciudad Bolívar", 20: "Sumapaz",
}
LOC_KEY_TO_NAME = {}


def fix_mojibake(s):
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def normalizar(s):
    s = "".join(
        c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c)
    ).upper().strip()
    if s.startswith("LA "):
        s = s[3:]
    return s


LOC_KEY_TO_NAME = {normalizar(v): v for v in LOC_CODE_TO_NAME.values()}


def webmercator_to_deg(x, y):
    lon = x / 20037508.34 * 180
    lat = 180 / math.pi * (2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lon, lat


def poly_a_grados(poly):
    def anillo(coords):
        return [webmercator_to_deg(x, y) for x, y in coords]

    partes = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    return [Polygon(anillo(p.exterior.coords), [anillo(r.coords) for r in p.interiors]) for p in partes]


# ---------------------------------------------------------------------------
# Carga de capas base (cacheadas — pesadas de leer)
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Cargando límites de localidades...")
def cargar_localidades():
    data = json.load(open(RAW / "localidades_bogota.geojson", encoding="utf-8"))
    polys = []
    for feat in data["features"]:
        nombre = fix_mojibake(feat["attributes"]["LocNombre"])
        rings = feat["geometry"]["rings"]
        poly = Polygon(rings[0], holes=rings[1:] if len(rings) > 1 else None).buffer(0)
        polys.append((nombre, poly))
    return polys


@st.cache_resource(show_spinner="Cargando Zonas de Interés Turístico...")
def cargar_zit():
    zit_data = json.load(open(RAW / "zit_actual.geojson", encoding="utf-8"))
    zit_polys = [shape(f["geometry"]) for f in zit_data["features"]]
    return zit_data, zit_polys


def asignar_localidad(punto, localidad_polys):
    for nombre, poly in localidad_polys:
        if poly.contains(punto):
            return nombre
    return None


@st.cache_data(show_spinner=False)
def contar_por_codigo_localidad(filename: str, campo: str) -> pd.Series:
    data = json.load(open(RAW / filename, encoding="utf-8"))
    codigos = [
        int(f["properties"][campo])
        for f in data["features"]
        if f["properties"].get(campo) not in (None, "")
    ]
    conteo = pd.Series(codigos).value_counts()
    conteo.index = conteo.index.map(LOC_CODE_TO_NAME)
    return conteo


# ---------------------------------------------------------------------------
# H1 — Crecimiento y concentración geográfica
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Calculando H1 (crecimiento por localidad)...")
def compute_h1() -> pd.DataFrame:
    vt_2023 = contar_por_codigo_localidad("vivienda_turistica_2023.geojson", "Localidad").rename("vt_2023")
    vt_actual = contar_por_codigo_localidad("vivienda_turistica_actual.geojson", "LOCALIDAD").rename("vt_actual")
    h1 = pd.concat([vt_2023, vt_actual], axis=1).fillna(0).astype(int)
    h1["crecimiento_abs"] = h1["vt_actual"] - h1["vt_2023"]
    h1["crecimiento_pct"] = (
        (h1["vt_actual"] - h1["vt_2023"]) / h1["vt_2023"].replace(0, pd.NA) * 100
    ).round(1)
    return h1.sort_values("vt_actual", ascending=False)


# ---------------------------------------------------------------------------
# H2 — Relación con ZIT
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Calculando H2 (dentro/fuera de ZIT)...")
def compute_h2() -> pd.DataFrame:
    _, zit_polys = cargar_zit()

    def pct_dentro_zit(fname):
        data = json.load(open(RAW / fname, encoding="utf-8"))
        dentro = fuera = 0
        for f in data["features"]:
            punto = shape(f["geometry"])
            if any(poly.contains(punto) for poly in zit_polys):
                dentro += 1
            else:
                fuera += 1
        total = dentro + fuera
        return dentro, fuera, total

    rows = []
    for etiqueta, fname in [("2023", "vivienda_turistica_2023.geojson"), ("actual", "vivienda_turistica_actual.geojson")]:
        dentro, fuera, total = pct_dentro_zit(fname)
        rows.append({
            "corte": etiqueta, "total": total, "dentro_zit": dentro, "fuera_zit": fuera,
            "pct_dentro_zit": round(dentro / total * 100, 1), "pct_fuera_zit": round(fuera / total * 100, 1),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# H3 — Peso sobre stock de vivienda residencial
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Calculando H3 (peso sobre stock de vivienda)...")
def compute_h3() -> pd.DataFrame:
    h1 = compute_h1()
    vt_2023_k = h1["vt_2023"].copy()
    vt_2023_k.index = vt_2023_k.index.map(normalizar)
    vt_actual_k = h1["vt_actual"].copy()
    vt_actual_k.index = vt_actual_k.index.map(normalizar)

    viv_raw = pd.read_excel(
        RAW / "hogares_viviendas_localidad_2018_2035.ods", engine="odf",
        sheet_name="Proy_Viviendas_Totales_Loc", header=None,
    )
    años = viv_raw.iloc[7]
    datos = viv_raw.iloc[8:28].copy()
    datos.columns = list(viv_raw.iloc[6, :6]) + list(años[6:])
    viviendas = datos[["Nombre Localidad", 2023.0, 2025.0]].dropna()
    viviendas.columns = ["localidad", "viviendas_2023", "viviendas_2025"]
    viviendas["localidad"] = viviendas["localidad"].apply(fix_mojibake)
    viviendas["key"] = viviendas["localidad"].apply(normalizar)
    viviendas = viviendas.set_index("key")

    h3 = viviendas.join(vt_2023_k.rename("vt_2023")).join(vt_actual_k.rename("vt_actual")).fillna(0)
    h3["pct_2023"] = (h3["vt_2023"] / h3["viviendas_2023"] * 100).round(3)
    h3["pct_2025"] = (h3["vt_actual"] / h3["viviendas_2025"] * 100).round(3)
    return h3.sort_values("pct_2025", ascending=False)


# ---------------------------------------------------------------------------
# H4 — Avalúo catastral
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Cargando avalúo catastral por manzana...")
def cargar_avaluo():
    return json.load(open(RAW / "avaluo_catastral_ph_manzana_actual.geojson", encoding="utf-8"))


@st.cache_data(show_spinner="Calculando H4 (avalúo catastral)...")
def compute_h4():
    avaluo_data = cargar_avaluo()
    localidad_polys = cargar_localidades()
    h1 = compute_h1()
    vt_actual_k = h1["vt_actual"].copy()
    vt_actual_k.index = vt_actual_k.index.map(normalizar)

    filas = []
    for f in avaluo_data["features"]:
        p = f["properties"]
        centroide = shape(f["geometry"]).centroid
        localidad = asignar_localidad(centroide, localidad_polys)
        filas.append({"av_cat_ph": p.get("AV_CAT_PH"), "predios": p.get("PREDIOS"), "localidad": localidad})

    avaluo_df = pd.DataFrame(filas).dropna(subset=["localidad", "av_cat_ph", "predios"])
    avaluo_df["ponderado"] = avaluo_df["av_cat_ph"] * avaluo_df["predios"]
    avaluo_df["key"] = avaluo_df["localidad"].apply(normalizar)

    avaluo_loc = avaluo_df.groupby("key").apply(
        lambda g: g["ponderado"].sum() / g["predios"].sum(), include_groups=False
    ).rename("avaluo_ph_m2")

    h4 = pd.concat([avaluo_loc, vt_actual_k.rename("vt_actual")], axis=1).dropna()
    h4["avaluo_ph_m2"] = h4["avaluo_ph_m2"].round(0).astype(int)
    h4 = h4.sort_values("vt_actual", ascending=False)
    corr_h4 = h4[["avaluo_ph_m2", "vt_actual"]].corr(method="spearman").iloc[0, 1]
    return h4, corr_h4


# ---------------------------------------------------------------------------
# H5 — Coincidencia con infraestructura turística formal
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Calculando H5 (clúster de economía turística)...")
def compute_h5():
    h1 = compute_h1()
    alojamiento = contar_por_codigo_localidad("alojamiento_turistico_actual.geojson", "LOCALIDAD").rename("alojamiento_formal")
    gastronomia = contar_por_codigo_localidad("gastronomia_bar_actual.geojson", "Nombre_Loc").rename("gastronomia_bar")

    h5 = pd.concat([h1["vt_actual"].rename("vivienda_turistica"), alojamiento, gastronomia], axis=1).fillna(0).astype(int)
    h5 = h5.sort_values("vivienda_turistica", ascending=False)
    corr_h5 = h5.corr(method="spearman")
    return h5, corr_h5


# ---------------------------------------------------------------------------
# H6 — Clusters de sector catastral (SOM + Agglomerative) vs. brecha ZIT
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Entrenando clusters de sector catastral (H6, puede tardar)...")
def compute_h6():
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.preprocessing import StandardScaler
    from minisom import MiniSom

    avaluo_data = cargar_avaluo()
    _, zit_polys = cargar_zit()
    h2 = compute_h2()

    manzana_polys = [shape(f["geometry"]) for f in avaluo_data["features"]]
    manzana_valores = [f["properties"]["AV_CAT_PH"] for f in avaluo_data["features"]]
    manzana_tree = STRtree(manzana_polys)

    def avaluo_por_punto(lon, lat):
        if lon is None or lat is None:
            return None
        idx = manzana_tree.query(Point(lon, lat), predicate="within")
        return manzana_valores[idx[0]] if len(idx) else None

    FUENTES_SECTOR = [
        ("vivienda_turistica_actual.geojson", "SECCATASTR", "LATITUD", "LONGITUD", "vivienda_turistica"),
        ("alojamiento_turistico_actual.geojson", "SECCATASTR", "LATITUD", "LONGITUD", "alojamiento_formal"),
        ("gastronomia_bar_actual.geojson", "Sector_Cat", "Latitud", "Longitud", "gastronomia_bar"),
    ]

    filas, zit_filas = [], []
    vt_2023_por_sector = {}
    vt_2023_data = json.load(open(RAW / "vivienda_turistica_2023.geojson", encoding="utf-8"))
    for f in vt_2023_data["features"]:
        p = f["properties"]
        sector = fix_mojibake(p.get("SECCATASTR") or p.get("SECTOR_CAT") or p.get("Sector_Cat"))
        if sector:
            vt_2023_por_sector[sector] = vt_2023_por_sector.get(sector, 0) + 1

    for fname, campo_sector, campo_lat, campo_lon, etiqueta in FUENTES_SECTOR:
        data = json.load(open(RAW / fname, encoding="utf-8"))
        for f in data["features"]:
            p = f["properties"]
            sector = fix_mojibake(p.get(campo_sector))
            if not sector:
                continue
            avaluo = avaluo_por_punto(p.get(campo_lon), p.get(campo_lat))
            filas.append({"sector": sector, "tipo": etiqueta, "avaluo": avaluo})
            if etiqueta == "vivienda_turistica":
                punto_wm = shape(f["geometry"])
                dentro = any(poly.contains(punto_wm) for poly in zit_polys)
                zit_filas.append({"sector": sector, "dentro_zit": dentro})

    puntos_sector = pd.DataFrame(filas)
    conteos = puntos_sector.pivot_table(index="sector", columns="tipo", values="avaluo", aggfunc="size", fill_value=0)
    avaluo_sector = puntos_sector.groupby("sector")["avaluo"].mean().rename("avaluo_ph_m2")

    for col in ["vivienda_turistica", "alojamiento_formal", "gastronomia_bar"]:
        if col not in conteos.columns:
            conteos[col] = 0

    total_sector = conteos.sum(axis=1)
    perfiles = conteos.copy()
    perfiles = perfiles[total_sector >= 3].copy()
    perfiles["avaluo_ph_m2"] = avaluo_sector.reindex(perfiles.index)
    # Fallback defensivo: si un sector no cruza con ninguna manzana de avalúo (borde de
    # cobertura), se usa la mediana de sectores válidos y, si ni eso existe, la mediana
    # cruda de AV_CAT_PH de todas las manzanas — nunca se deja un NaN entrando al SOM.
    fallback_manzanas = float(np.nanmedian([f["properties"].get("AV_CAT_PH") for f in avaluo_data["features"]]))
    mediana_sectores = perfiles["avaluo_ph_m2"].median()
    relleno = mediana_sectores if pd.notna(mediana_sectores) else fallback_manzanas
    perfiles["avaluo_ph_m2"] = perfiles["avaluo_ph_m2"].fillna(relleno)
    perfiles["vt_2023"] = pd.Series(vt_2023_por_sector).reindex(perfiles.index).fillna(0)
    perfiles["crecimiento_pct"] = (
        (perfiles["vivienda_turistica"] - perfiles["vt_2023"])
        / perfiles["vt_2023"].replace(0, np.nan) * 100
    ).fillna(0).clip(-100, 1000)

    total_puntos_sector = perfiles[["vivienda_turistica", "alojamiento_formal", "gastronomia_bar"]].sum(axis=1)
    perfiles["pct_alojamiento_formal"] = (perfiles["alojamiento_formal"] / total_puntos_sector * 100).fillna(0)
    perfiles["pct_gastronomia_bar"] = (perfiles["gastronomia_bar"] / total_puntos_sector * 100).fillna(0)
    perfiles["pct_vivienda_turistica"] = (perfiles["vivienda_turistica"] / total_puntos_sector * 100).fillna(0)
    perfiles["intensidad_vt"] = np.log1p(perfiles["vivienda_turistica"])
    perfiles = perfiles.rename(columns={"vivienda_turistica": "vivienda_turistica"})

    FEATURE_COLS = ["intensidad_vt", "pct_alojamiento_formal", "pct_gastronomia_bar", "crecimiento_pct", "avaluo_ph_m2"]
    X_scaled = StandardScaler().fit_transform(perfiles[FEATURE_COLS].values)

    N_CLUSTERS = 6
    perfiles["cluster_id"] = AgglomerativeClustering(n_clusters=N_CLUSTERS, linkage="ward").fit_predict(X_scaled)

    GRID = 9
    som = MiniSom(GRID, GRID, len(FEATURE_COLS), sigma=1.5, learning_rate=0.5, random_seed=42)
    som.random_weights_init(X_scaled)
    som.train_random(X_scaled, 4000)
    perfiles["nodo"] = [som.winner(x) for x in X_scaled]
    u_matrix = som.distance_map()

    REPORT_COLS = FEATURE_COLS + ["pct_vivienda_turistica", "vivienda_turistica"]
    resumen_clusters = perfiles.groupby("cluster_id")[REPORT_COLS].mean().round(1)
    resumen_clusters["n_sectores"] = perfiles.groupby("cluster_id").size()

    aloj_mediana = resumen_clusters["pct_alojamiento_formal"].median()
    resumen_clusters["intensidad_rank"] = resumen_clusters["intensidad_vt"].rank(ascending=False)

    def nombrar_perfil(row):
        if row["pct_gastronomia_bar"] > 50:
            return "Gastronomía / vida local, sin presión turística"
        if row["pct_alojamiento_formal"] > row["pct_vivienda_turistica"] and row["pct_alojamiento_formal"] > aloj_mediana:
            return "Polo hotelero / negocios"
        if row["intensidad_rank"] == 1:
            return "Núcleo turístico consolidado"
        if row["intensidad_rank"] == 2:
            return "Foco turístico emergente"
        return "Residencial ordinario, sin presión turística"

    resumen_clusters["perfil"] = resumen_clusters.apply(nombrar_perfil, axis=1)
    perfiles["perfil"] = perfiles["cluster_id"].map(resumen_clusters["perfil"])

    zit_por_sector = pd.DataFrame(zit_filas).groupby("sector").agg(
        n_vt_zit_check=("dentro_zit", "size"), dentro_zit_n=("dentro_zit", "sum"),
    )
    check_total = zit_por_sector["n_vt_zit_check"].sum()
    dentro_total = zit_por_sector["dentro_zit_n"].sum()
    baseline_fuera_zit = (1 - dentro_total / check_total) * 100 if check_total else float("nan")

    zit_counts = zit_por_sector.rename(columns={"dentro_zit_n": "dentro", "n_vt_zit_check": "total"})
    con_zit = perfiles.join(zit_counts[["dentro", "total"]]).dropna(subset=["total"])
    brecha = con_zit.groupby("perfil")[["dentro", "total"]].sum()
    brecha["pct_fuera_zit"] = (1 - brecha["dentro"] / brecha["total"]) * 100
    brecha["brecha_vs_ciudad"] = (brecha["pct_fuera_zit"] - baseline_fuera_zit).round(1)
    brecha["n_sectores"] = con_zit.groupby("perfil").size()

    return perfiles, resumen_clusters, brecha, baseline_fuera_zit, u_matrix, GRID


# ---------------------------------------------------------------------------
# Extensión — DBSCAN geográfico + candidatas a nueva ZIT
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Ejecutando DBSCAN espacial (candidatas a nueva ZIT)...")
def compute_dbscan_extension(eps: float = 200, min_samples: int = 6, umbral_n: int = 20, umbral_pct: float = 60):
    from sklearn.cluster import DBSCAN

    _, zit_polys = cargar_zit()
    vt_actual_data = json.load(open(RAW / "vivienda_turistica_actual.geojson", encoding="utf-8"))

    filas_vt = []
    for f in vt_actual_data["features"]:
        p = f["properties"]
        if p.get("LATITUD") is None or p.get("LONGITUD") is None:
            continue
        x, y = f["geometry"]["coordinates"]
        filas_vt.append({
            "x": x, "y": y, "lat": p["LATITUD"], "lon": p["LONGITUD"],
            "localidad": LOC_CODE_TO_NAME.get(int(p["LOCALIDAD"])) if p.get("LOCALIDAD") else None,
            "geom": Point(x, y),
        })
    puntos_vt = pd.DataFrame(filas_vt)

    dbscan_labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(puntos_vt[["x", "y"]].values)
    puntos_vt["cluster"] = dbscan_labels
    puntos_vt["dentro_zit"] = [any(poly.contains(g) for poly in zit_polys) for g in puntos_vt["geom"]]

    def veredicto(row):
        if row["n_puntos"] < umbral_n:
            return "cluster menor"
        return "candidata a nueva ZIT" if row["pct_fuera_zit"] >= umbral_pct else "ya cubierta por ZIT"

    resumen_dbscan = puntos_vt[puntos_vt["cluster"] != -1].groupby("cluster").agg(
        n_puntos=("cluster", "size"),
        pct_fuera_zit=("dentro_zit", lambda s: round((1 - s.mean()) * 100, 1)),
        lat=("lat", "mean"), lon=("lon", "mean"),
        localidad=("localidad", lambda s: s.mode().iloc[0] if not s.mode().empty else "?"),
    )
    resumen_dbscan["veredicto"] = resumen_dbscan.apply(veredicto, axis=1)
    puntos_vt["veredicto"] = puntos_vt["cluster"].map(resumen_dbscan["veredicto"]).fillna("aislado (sin cluster)")

    return puntos_vt, resumen_dbscan


# ---------------------------------------------------------------------------
# Síntesis final por localidad
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Construyendo tabla de síntesis...")
def compute_synthesis() -> pd.DataFrame:
    h1 = compute_h1()
    h3 = compute_h3()
    h4, _ = compute_h4()
    h5, _ = compute_h5()

    h1_k = h1.copy()
    h1_k.index = h1_k.index.map(normalizar)
    h5_k = h5.copy()
    h5_k.index = h5_k.index.map(normalizar)

    resumen = pd.concat([
        h1_k[["vt_2023", "vt_actual", "crecimiento_pct"]],
        h3[["pct_2025"]].rename(columns={"pct_2025": "pct_stock_vivienda"}),
    ], axis=1)
    resumen = resumen.join(h4["avaluo_ph_m2"], how="left").join(h5_k[["alojamiento_formal", "gastronomia_bar"]], how="left")
    resumen.insert(0, "localidad", [LOC_KEY_TO_NAME.get(k, k) for k in resumen.index])
    return resumen.sort_values("vt_actual", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Geometría auxiliar para el mapa (ZIT en grados, para overlay)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def zit_polygons_deg():
    _, zit_polys = cargar_zit()
    polys_deg = [p for poly in zit_polys for p in poly_a_grados(poly)]
    return [list(p.exterior.coords) for p in polys_deg]
