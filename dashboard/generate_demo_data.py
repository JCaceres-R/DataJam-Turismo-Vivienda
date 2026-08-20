"""
Genera un set de datos SINTÉTICO con el mismo esquema que los archivos que
descarga el notebook (data/raw/turismo_vivienda/*). Se usa solo cuando el
dashboard no encuentra los datos reales, para que la app siga siendo
demostrable end-to-end. No reemplaza los datos oficiales del Portal de Datos
Abiertos de Bogotá.
"""
import json
import math
import random
from pathlib import Path

import pandas as pd

random.seed(7)

LOCALIDADES = {
    1: "Usaquén", 2: "Chapinero", 3: "Santa Fe", 4: "San Cristóbal", 5: "Usme",
    6: "Tunjuelito", 7: "Bosa", 8: "Kennedy", 9: "Fontibón", 10: "Engativá",
    11: "Suba", 12: "Barrios Unidos", 13: "Teusaquillo", 14: "Los Mártires",
    15: "Antonio Nariño", 16: "Puente Aranda", 17: "La Candelaria",
    18: "Rafael Uribe Uribe", 19: "Ciudad Bolívar", 20: "Sumapaz",
}
# pesos relativos de vivienda turística por localidad (corredor centro-norte domina)
PESOS = {
    2: 30, 1: 22, 3: 12, 13: 10, 12: 8, 11: 7, 10: 5, 9: 4, 8: 3, 14: 3,
    16: 2, 17: 2, 15: 1, 4: 1, 18: 1, 6: 1, 7: 1, 19: 1, 5: 1, 20: 1,
}
# centro aproximado (lon,lat) por localidad
CENTROS = {
    1: (-74.03, 4.70), 2: (-74.05, 4.65), 3: (-74.07, 4.61), 4: (-74.08, 4.56),
    5: (-74.11, 4.48), 6: (-74.13, 4.57), 7: (-74.19, 4.62), 8: (-74.16, 4.63),
    9: (-74.15, 4.67), 10: (-74.12, 4.71), 11: (-74.09, 4.75), 12: (-74.07, 4.67),
    13: (-74.09, 4.65), 14: (-74.09, 4.61), 15: (-74.10, 4.59), 16: (-74.12, 4.62),
    17: (-74.075, 4.596), 18: (-74.10, 4.56), 19: (-74.16, 4.55), 20: (-74.22, 4.30),
}


def lonlat_to_webmercator(lon, lat):
    x = lon * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
    return x, y


def jitter(center, spread=0.015):
    lon, lat = center
    return lon + random.uniform(-spread, spread), lat + random.uniform(-spread, spread)


def make_points(n_by_loc, seccatastr_pool_size=6, growth_factor=None):
    """growth_factor: dict codigo -> multiplicador vs 2023 (para el archivo 'actual')."""
    features = []
    for codigo, base_n in n_by_loc.items():
        n = base_n
        if growth_factor:
            n = int(round(base_n * growth_factor.get(codigo, 1.0)))
        for i in range(n):
            lon, lat = jitter(CENTROS[codigo])
            x, y = lonlat_to_webmercator(lon, lat)
            sector = f"{codigo:02d}{(i % seccatastr_pool_size) + 1:02d}"
            features.append({
                "type": "Feature",
                "properties": {
                    "LOCALIDAD": codigo, "Localidad": codigo, "Nombre_Loc": codigo,
                    "SECCATASTR": sector, "Sector_Cat": sector,
                    "LATITUD": lat, "Longitud": lon, "LONGITUD": lon, "Latitud": lat,
                },
                "geometry": {"type": "Point", "coordinates": [x, y]},
            })
    return {"type": "FeatureCollection", "features": features}


def make_zit(n_zonas=10):
    features = []
    zit_codigos = [1, 1, 2, 2, 3, 13, 12, 11, 10, 9]
    for codigo in zit_codigos[:n_zonas]:
        lon, lat = jitter(CENTROS[codigo], spread=0.02)
        d = 0.01
        ring_deg = [(lon - d, lat - d), (lon + d, lat - d), (lon + d, lat + d), (lon - d, lat + d), (lon - d, lat - d)]
        ring_wm = [lonlat_to_webmercator(x, y) for x, y in ring_deg]
        features.append({
            "type": "Feature", "properties": {"nombre": f"ZIT {codigo}"},
            "geometry": {"type": "Polygon", "coordinates": [ring_wm]},
        })
    return {"type": "FeatureCollection", "features": features}


def make_localidades():
    features = []
    for codigo, nombre in LOCALIDADES.items():
        lon, lat = CENTROS[codigo]
        d = 0.03 if codigo != 20 else 0.3
        ring_deg = [(lon - d, lat - d), (lon + d, lat - d), (lon + d, lat + d), (lon - d, lat + d), (lon - d, lat - d)]
        ring_wm = [lonlat_to_webmercator(x, y) for x, y in ring_deg]
        features.append({"attributes": {"LocNombre": nombre}, "geometry": {"rings": [ring_wm]}})
    return {"type": "FeatureCollection", "features": features}


def make_avaluo(n_manzanas=1500):
    features = []
    for i in range(n_manzanas):
        codigo = random.choice(list(LOCALIDADES.keys())[:19])
        lon, lat = jitter(CENTROS[codigo], spread=0.02)
        d = 0.001
        ring_deg = [(lon - d, lat - d), (lon + d, lat - d), (lon + d, lat + d), (lon - d, lat + d), (lon - d, lat - d)]
        ring_wm = [lonlat_to_webmercator(x, y) for x, y in ring_deg]
        base_price = 4_000_000 + PESOS.get(codigo, 1) * 120_000
        precio = max(1_500_000, int(random.gauss(base_price, base_price * 0.15)))
        features.append({
            "type": "Feature",
            "properties": {"AV_CAT_PH": precio, "PREDIOS": random.randint(5, 400)},
            "geometry": {"type": "Polygon", "coordinates": [ring_wm]},
        })
    return {"type": "FeatureCollection", "features": features}


def make_hogares_ods(path: Path):
    # Replica el layout real: fila (índice 6) trae los 6 encabezados de metadata,
    # fila (índice 7) trae los años en las columnas 6+, los datos empiezan en la fila 8.
    rows_meta = ["Codigo", "Nombre Localidad", "col3", "col4", "col5", "col6"]
    years = list(range(2018, 2036))
    n_cols = 6 + len(years)

    row6 = rows_meta + [""] * len(years)
    row7 = [""] * 6 + years

    data_rows = []
    for codigo, nombre in LOCALIDADES.items():
        base = 30000 + PESOS.get(codigo, 1) * 3500
        row = [codigo, nombre, "", "", "", ""]
        for y in years:
            growth = 1 + 0.018 * (y - 2018)
            row.append(int(base * growth))
        data_rows.append(row)

    blank = [""] * n_cols
    all_rows = [blank] * 6 + [row6, row7] + data_rows + [blank] * 2
    df = pd.DataFrame(all_rows)
    df.to_excel(path, engine="odf", header=False, index=False, sheet_name="Proy_Viviendas_Totales_Loc")


def generate(raw_dir: Path):
    raw_dir.mkdir(parents=True, exist_ok=True)

    n_2023 = {c: max(3, int(w * 2.2)) for c, w in PESOS.items()}
    growth = {c: random.uniform(1.3, 2.3) if c in (1, 2, 3, 12, 13) else random.uniform(0.9, 1.6) for c in PESOS}

    vt_2023 = make_points(n_2023, seccatastr_pool_size=8)
    vt_actual = make_points(n_2023, seccatastr_pool_size=8, growth_factor=growth)

    n_aloj = {c: max(1, int(w * 0.6)) for c, w in PESOS.items()}
    n_gastro = {c: max(1, int(w * 1.1)) for c, w in PESOS.items()}
    aloj = make_points(n_aloj, seccatastr_pool_size=8)
    gastro = make_points(n_gastro, seccatastr_pool_size=8)

    with open(raw_dir / "vivienda_turistica_2023.geojson", "w") as f:
        json.dump(vt_2023, f)
    with open(raw_dir / "vivienda_turistica_actual.geojson", "w") as f:
        json.dump(vt_actual, f)
    with open(raw_dir / "zit_actual.geojson", "w") as f:
        json.dump(make_zit(), f)
    with open(raw_dir / "localidades_bogota.geojson", "w") as f:
        json.dump(make_localidades(), f)
    with open(raw_dir / "avaluo_catastral_ph_manzana_actual.geojson", "w") as f:
        json.dump(make_avaluo(), f)
    with open(raw_dir / "alojamiento_turistico_actual.geojson", "w") as f:
        json.dump(aloj, f)
    with open(raw_dir / "gastronomia_bar_actual.geojson", "w") as f:
        json.dump(gastro, f)
    make_hogares_ods(raw_dir / "hogares_viviendas_localidad_2018_2035.ods")
    print(f"Datos sintéticos generados en {raw_dir}")


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/turismo_vivienda")
    generate(target)
