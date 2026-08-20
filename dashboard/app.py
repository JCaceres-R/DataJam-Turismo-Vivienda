import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_processing as dp

# ---------------------------------------------------------------------------
# Config general + estilo
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Turismo + Vivienda en Bogotá — Dashboard",
    page_icon="🏙️",
    layout="wide",
)

BLUE = "#0ea5e9"
GRAY = "#94a3b8"
GREEN = "#22c55e"
ORANGE = "#f97316"
SLATE = "#1e293b"
CARD_BG = "#161b24"

PALETTE_20 = [
    "#0ea5e9", "#f97316", "#22c55e", "#a855f7", "#eab308", "#ef4444",
    "#14b8a6", "#ec4899", "#84cc16", "#6366f1", "#f43f5e", "#06b6d4",
    "#d946ef", "#facc15", "#4ade80", "#fb7185", "#38bdf8", "#c084fc",
    "#fbbf24", "#34d399",
]

st.markdown(
    f"""
    <style>
    .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }}
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG}; border-radius: 10px; padding: 12px 16px;
        border: 1px solid #232935;
    }}
    div[data-testid="stMetricLabel"] {{ color: {GRAY}; }}
    h3, h4 {{ margin-top: 0; }}
    .panel-title {{ font-size: 1.05rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.3rem; }}
    .badge {{ display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; font-weight:600; }}
    .badge-green {{ background: rgba(34,197,94,0.18); color: {GREEN}; }}
    .badge-orange {{ background: rgba(249,115,22,0.18); color: {ORANGE}; }}
    .badge-blue {{ background: rgba(14,165,233,0.18); color: {BLUE}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def dark_fig(fig: go.Figure, height=340, legend=True, margin=None):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=margin or dict(l=10, r=10, t=10, b=10),
        showlegend=legend,
        font=dict(color="#e5e7eb", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    )
    fig.update_xaxes(gridcolor="#232935", zerolinecolor="#232935")
    fig.update_yaxes(gridcolor="#232935", zerolinecolor="#232935")
    return fig


def clicked_point(event):
    """Extrae el primer punto clickeado de un st.plotly_chart(..., on_select='rerun').
    Devuelve el dict del punto (con 'customdata', 'x', 'y', etc.) o None."""
    if not event:
        return None
    sel = getattr(event, "selection", None)
    if sel is None and isinstance(event, dict):
        sel = event.get("selection")
    if not sel:
        return None
    pts = getattr(sel, "points", None)
    if pts is None and isinstance(sel, dict):
        pts = sel.get("points")
    return pts[0] if pts else None


# ---------------------------------------------------------------------------
# Disponibilidad de datos (con fallback sintético para poder previsualizar)
# ---------------------------------------------------------------------------

if not dp.datos_disponibles():
    from generate_demo_data import generate as _generate_demo

    with st.spinner("No se encontraron los datos del notebook — generando datos sintéticos de demo..."):
        _generate_demo(dp.RAW)
    st.warning(
        "⚠️ No se encontraron los archivos crudos que descarga el notebook en "
        f"`{dp.RAW}`. Estás viendo **datos sintéticos de ejemplo** para poder "
        "previsualizar el dashboard. Corre las celdas de descarga del notebook "
        "(`01_turismo_vivienda_analisis.ipynb`, celda *Descarga reproducible*) "
        "y recarga esta página para ver los datos reales del Portal de Datos "
        "Abiertos de Bogotá.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Carga de todas las hipótesis
# ---------------------------------------------------------------------------

h1 = dp.compute_h1()
h2 = dp.compute_h2()
h3 = dp.compute_h3()
h4, corr_h4 = dp.compute_h4()
h5, corr_h5 = dp.compute_h5()
synth = dp.compute_synthesis()

localidades_disponibles = list(h1.index)

# ---------------------------------------------------------------------------
# Encabezado 
# ---------------------------------------------------------------------------

head_l, head_m, head_r = st.columns([3.2, 1, 1])
with head_l:
    st.markdown("## 🏙️ Turismo + Vivienda en Bogotá — Dashboard")
    st.caption("DataJam Bogotá 2026 — expansión de la vivienda turística tipo Airbnb, H1–H5 + extensión DBSCAN")
with head_m:
    localidad_sel = st.selectbox("Localidad", ["Todas"] + localidades_disponibles, index=0)
with head_r:
    corte_sel = st.selectbox("Corte temporal", ["Actual", "2023"], index=0)

corte_key = "actual" if corte_sel == "Actual" else "2023"

# ---------------------------------------------------------------------------
# Franja de KPIs
# ---------------------------------------------------------------------------

total_2023 = int(h1["vt_2023"].sum())
total_actual = int(h1["vt_actual"].sum())
crecimiento_ciudad = (total_actual / total_2023 - 1) * 100 if total_2023 else float("nan")
pct_fuera_actual = h2.loc[h2["corte"] == "actual", "pct_fuera_zit"].iloc[0]
pct_fuera_2023 = h2.loc[h2["corte"] == "2023", "pct_fuera_zit"].iloc[0]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Vivienda turística (actual)", f"{total_actual:,}", f"+{crecimiento_ciudad:.0f}% vs. 2023")
k2.metric("Fuera de ZIT (actual)", f"{pct_fuera_actual:.1f}%", f"{pct_fuera_actual - pct_fuera_2023:+.1f} pts vs. 2023")
k3.metric("Correlación con avalúo (H4)", f"ρ = {corr_h4:.2f}", "Spearman, por localidad")
k4.metric("Correlación con alojamiento formal (H5)", f"ρ = {corr_h5.loc['vivienda_turistica','alojamiento_formal']:.2f}")

st.write("")

# ---------------------------------------------------------------------------
# Fila principal:
# ---------------------------------------------------------------------------

left_col, right_col = st.columns([1.05, 2.15], gap="medium")

with left_col:
    with st.container(border=True):
        st.markdown('<div class="panel-title">Vivienda Turística por Localidad (2023 vs. actual)</div>', unsafe_allow_html=True)
        top10 = h1.head(10).sort_values("vt_actual")
        crecimiento_seg = (top10["vt_actual"] - top10["vt_2023"]).clip(lower=0)
        fig1 = go.Figure()
        colors_2023 = [GREEN if loc == localidad_sel else GRAY for loc in top10.index]
        colors_growth = [GREEN if loc == localidad_sel else BLUE for loc in top10.index]
        fig1.add_bar(y=top10.index, x=top10["vt_2023"], orientation="h", name="2023", marker_color=colors_2023)
        fig1.add_bar(y=top10.index, x=crecimiento_seg, orientation="h", name="Crecimiento hasta hoy",
                     base=top10["vt_2023"], marker_color=colors_growth)
        fig1.update_layout(barmode="overlay", xaxis_title="Unidades de vivienda turística")
        st.plotly_chart(dark_fig(fig1, height=300), use_container_width=True)

    with st.container(border=True):
        st.markdown('<div class="panel-title">Porcentaje de vivienda turística fuera de ZIT</div>', unsafe_allow_html=True)
        pct_show = pct_fuera_actual if corte_key == "actual" else pct_fuera_2023
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=pct_show,
            number={"suffix": "%", "font": {"size": 40, "color": "#f1f5f9"}},
            gauge={
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": ORANGE if pct_show >= 50 else BLUE, "thickness": 0.32},
                "bgcolor": "#232935",
                "borderwidth": 0,
            },
        ))
        gauge.add_annotation(text=f"Corte: {corte_sel}", x=0.5, y=-0.05, showarrow=False, font=dict(color=GRAY, size=12))
        st.plotly_chart(dark_fig(gauge, height=260, legend=False, margin=dict(l=20, r=20, t=10, b=10)), use_container_width=True)

with right_col:
    with st.container(border=True):
        st.markdown(f'<div class="panel-title">Mapa · Vivienda turística ({corte_sel}) vs. Zonas de Interés Turístico (ZIT)</div>', unsafe_allow_html=True)

        # puntos según el corte elegido
        fname = "vivienda_turistica_actual.geojson" if corte_key == "actual" else "vivienda_turistica_2023.geojson"
        import json
        vt_geo = json.load(open(dp.RAW / fname, encoding="utf-8"))
        _, zit_polys = dp.cargar_zit()

        lats, lons, dentro_flags, locs, sectores = [], [], [], [], []
        for f in vt_geo["features"]:
            p = f["properties"]
            lat, lon = p.get("LATITUD") or p.get("Latitud"), p.get("LONGITUD") or p.get("Longitud")
            if lat is None or lon is None:
                continue
            codigo = p.get("LOCALIDAD") or p.get("Localidad")
            nombre = dp.LOC_CODE_TO_NAME.get(int(codigo)) if codigo else None
            if localidad_sel != "Todas" and nombre != localidad_sel:
                continue
            from shapely.geometry import shape as _shape
            punto_wm = _shape(f["geometry"])
            dentro = any(poly.contains(punto_wm) for poly in zit_polys)
            sector = p.get("SECCATASTR") or p.get("Sector_Cat") or "s/d"
            lats.append(lat); lons.append(lon); dentro_flags.append(dentro); locs.append(nombre); sectores.append(sector)

        map_df = pd.DataFrame({"lat": lats, "lon": lons, "dentro_zit": dentro_flags, "localidad": locs, "sector": sectores})
        map_df["estado"] = np.where(map_df["dentro_zit"], "Dentro de ZIT", "Fuera de ZIT")

        fig_map = go.Figure()
        for estado, color in [("Dentro de ZIT", GREEN), ("Fuera de ZIT", "#f1f5f9")]:
            sub = map_df[map_df["estado"] == estado]
            customdata = np.stack([sub["localidad"], sub["sector"], sub["lat"], sub["lon"]], axis=-1)
            fig_map.add_trace(go.Scattermap(
                lat=sub["lat"], lon=sub["lon"], mode="markers", name=estado,
                marker=dict(size=9, color=color, opacity=0.8),
                customdata=customdata,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"Estado: {estado}<br>"
                    "Sector catastral: %{customdata[1]}<br>"
                    "Lat/Lon: %{customdata[2]:.5f}, %{customdata[3]:.5f}"
                    "<extra></extra>"
                ),
            ))
        for coords in dp.zit_polygons_deg():
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            fig_map.add_trace(go.Scattermap(
                lat=ys, lon=xs, mode="lines", line=dict(width=1.5, color=BLUE),
                name="ZIT (límite)", showlegend=False, hoverinfo="skip",
            ))

        center_lat = map_df["lat"].mean() if len(map_df) else 4.65
        center_lon = map_df["lon"].mean() if len(map_df) else -74.08
        fig_map.update_layout(
            map=dict(style="carto-darkmatter", center=dict(lat=center_lat, lon=center_lon),
                        zoom=10.2 if localidad_sel == "Todas" else 12.5),
            clickmode="event+select",
        )
        map_event = st.plotly_chart(
            dark_fig(fig_map, height=610, margin=dict(l=0, r=0, t=0, b=0)),
            use_container_width=True, on_select="rerun", key="mapa_principal",
        )

        punto = clicked_point(map_event)
        if punto is not None and punto.get("customdata") is not None:
            cd = punto["customdata"]
            st.markdown(
                f"📍 **Localidad:** {cd[0]}  &nbsp;|&nbsp;  "
                f"🧭 **Sector catastral:** {cd[1]}  &nbsp;|&nbsp;  "
                f"🌐 **Coordenadas:** {float(cd[2]):.5f}, {float(cd[3]):.5f}"
            )
        else:
            st.caption("💡 Haz click sobre un punto del mapa para ver su detalle aquí.")

# ---------------------------------------------------------------------------
# Fila inferior: c1,c2,c3
# ---------------------------------------------------------------------------

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    with st.container(border=True):
        st.markdown('<div class="panel-title">Porcentaje de Vivienda Turistica por Localidad</div>', unsafe_allow_html=True)
        top8 = h3.head(6)
        fig3 = go.Figure()
        colors3_23 = [GREEN if dp.normalizar(l) == dp.normalizar(localidad_sel) else GRAY for l in top8["localidad"]]
        colors3_25 = [GREEN if dp.normalizar(l) == dp.normalizar(localidad_sel) else BLUE for l in top8["localidad"]]
        fig3.add_bar(x=top8["localidad"], y=top8["pct_2023"], name="2023", marker_color=colors3_23)
        fig3.add_bar(x=top8["localidad"], y=top8["pct_2025"], name="Actual", marker_color=colors3_25)
        fig3.update_layout(barmode="group", yaxis_title="% del stock en uso turístico")
        fig3.update_xaxes(tickangle=90)
        st.plotly_chart(dark_fig(fig3, height=300), use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown(f'<div class="panel-title">Incidencia de vivienda turística en el avalúo catastral </div>', unsafe_allow_html=True)

        nombres_h4 = [dp.LOC_KEY_TO_NAME.get(k, k) for k in h4.index]
        colores_h4 = [PALETTE_20[i % len(PALETTE_20)] for i in range(len(h4))]
        es_seleccionada = [dp.normalizar(n) == dp.normalizar(localidad_sel) for n in nombres_h4]
        line_widths = [2.5 if sel else 0.5 for sel in es_seleccionada]
        line_colors = ["#ffffff" if sel else "#0b0e14" for sel in es_seleccionada]
        sizes = [15 if sel else 11 for sel in es_seleccionada]

        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=h4["vt_actual"], y=h4["avaluo_ph_m2"], mode="markers",
            customdata=nombres_h4,
            hovertemplate="<b>%{customdata}</b><br>Vivienda turística: %{x}<br>Avalúo/m²: $%{y:,.0f}<extra></extra>",
            marker=dict(size=sizes, color=colores_h4, line=dict(width=line_widths, color=line_colors)),
        ))
        fig4.update_layout(xaxis_title="Vivienda turística (unidades)", yaxis_title="Avalúo por m² (COP)")
        st.plotly_chart(dark_fig(fig4, height=300, legend=False), use_container_width=True)

        # Lista de localidades debajo de la gráfica, cada una con el color de su punto.
        leyenda_html = "<div style='display:flex; flex-wrap:wrap; gap:5px 14px; margin-top:4px;'>"
        for nombre, color in zip(nombres_h4, colores_h4):
            leyenda_html += (
                "<div style='display:flex; align-items:center; gap:6px; font-size:0.78rem; color:#cbd5e1;'>"
                f"<span style='width:10px;height:10px;border-radius:50%;background:{color};"
                "display:inline-block; flex-shrink:0;'></span>"
                f"<span>{nombre}</span></div>"
            )
        leyenda_html += "</div>"
        st.markdown(leyenda_html, unsafe_allow_html=True)

with c3:
    with st.container(border=True):
        st.markdown('<div class="panel-title">Grafico de correlación</div>', unsafe_allow_html=True)
        RENAME_H5 = {
            "vivienda_turistica": "VT",
            "alojamiento_formal": "AT",
            "gastronomia_bar": "RoB",
        }
        corr_h5_disp = corr_h5.rename(index=RENAME_H5, columns=RENAME_H5)
        fig5 = go.Figure(go.Heatmap(
            z=corr_h5_disp.values, x=corr_h5_disp.columns, y=corr_h5_disp.index, colorscale="Blues",
            zmin=0, zmax=1, text=corr_h5_disp.round(2).values, texttemplate="%{text}",
            colorbar=dict(title="Spearman"),
        ))
        st.plotly_chart(dark_fig(fig5, height=300, legend=False), use_container_width=True)
        st.caption(
            f"RoB = Restaurantes o Bares - "
            f"VT = Vivienda Turistica - "
            f"AF = Alojamiento Formal"
        )
st.write("")

# ---------------------------------------------------------------------------
# Pestañas: Extensión DBSCAN, Síntesis
# ---------------------------------------------------------------------------

tab_ext, tab_synth = st.tabs([
    "📍 Extensión · Candidatas a nueva ZIT (DBSCAN)",
    "📋 Síntesis por localidad & conclusiones",
])

with tab_ext:
    st.markdown(
        "Clustering espacial (**DBSCAN**, sobre coordenadas reales, no por sector ni localidad) "
        "para encontrar manchas geográficas concretas de vivienda turística que hoy caen "
        "mayoritariamente fuera de cualquier ZIT — candidatas directas a nueva zona planeada."
    )

    ec1, ec2, ec3, ec4 = st.columns(4)
    eps = ec1.slider("eps (radio, metros)", 50, 500, 200, step=25)
    min_samples = ec2.slider("min_samples (vecinos mínimos)", 3, 20, 6)
    umbral_n = ec3.slider("Tamaño mínimo del cluster", 5, 100, 20, step=5,
                           help="Un cluster con menos puntos que esto se clasifica como 'cluster menor', no como candidata.")
    umbral_pct = ec4.slider("% mínimo fuera de ZIT", 0, 100, 60, step=5,
                             help="Un cluster necesita al menos este % de sus puntos fuera de ZIT para ser 'candidata a nueva ZIT'.")

    with st.spinner("Ejecutando DBSCAN..."):
        puntos_vt, resumen_dbscan = dp.compute_dbscan_extension(
            eps=eps, min_samples=min_samples, umbral_n=umbral_n, umbral_pct=umbral_pct,
        )

    candidatas = resumen_dbscan[resumen_dbscan["veredicto"] == "candidata a nueva ZIT"].sort_values("n_puntos", ascending=False)
    n_aislados = (puntos_vt["cluster"] == -1).sum()

    kk1, kk2, kk3, kk4 = st.columns(4)
    kk1.metric("Clusters geográficos", int((resumen_dbscan.index >= 0).sum()) if len(resumen_dbscan) else 0)
    kk2.metric("Candidatas a nueva ZIT", len(candidatas))
    kk3.metric("Puntos en candidatas", int(candidatas["n_puntos"].sum()) if len(candidatas) else 0)
    kk4.metric("Puntos aislados", f"{n_aislados} ({n_aislados/len(puntos_vt)*100:.1f}%)" if len(puntos_vt) else "0")

    mcol, tcol = st.columns([1.6, 1], gap="medium")
    with mcol:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Clusters DBSCAN de vivienda turística vs. ZIT planeadas</div>', unsafe_allow_html=True)
            COLORS = {"candidata a nueva ZIT": ORANGE, "ya cubierta por ZIT": BLUE,
                      "cluster menor": GRAY, "aislado (sin cluster)": "#4b5563"}

            # Info del cluster (tamaño, % fuera de ZIT) pegada a cada punto, para el hover/click.
            puntos_vt_info = puntos_vt.merge(
                resumen_dbscan[["n_puntos", "pct_fuera_zit"]],
                left_on="cluster", right_index=True, how="left",
            )
            puntos_vt_info["n_puntos"] = puntos_vt_info["n_puntos"].fillna(1).astype(int)
            default_pct = np.where(puntos_vt_info["dentro_zit"], 0.0, 100.0)
            mask_sin_cluster = puntos_vt_info["pct_fuera_zit"].isna()
            puntos_vt_info.loc[mask_sin_cluster, "pct_fuera_zit"] = default_pct[mask_sin_cluster.values]
            puntos_vt_info["localidad"] = puntos_vt_info["localidad"].fillna("s/d")

            fig_db = go.Figure()
            for cat, color in COLORS.items():
                sub = puntos_vt_info[puntos_vt_info["veredicto"] == cat]
                if len(sub) == 0:
                    continue
                customdata = np.stack([sub["localidad"], sub["n_puntos"], sub["pct_fuera_zit"]], axis=-1)
                fig_db.add_trace(go.Scattermap(
                    lat=sub["lat"], lon=sub["lon"], mode="markers", name=f"{cat} (n={len(sub)})",
                    marker=dict(size=8, color=color, opacity=0.85),
                    customdata=customdata,
                    hovertemplate=(
                        f"<b>{cat}</b><br>Localidad: %{{customdata[0]}}<br>"
                        "Puntos en el cluster: %{customdata[1]}<br>"
                        "%% fuera de ZIT (cluster): %{customdata[2]:.0f}%"
                        "<extra></extra>"
                    ),
                ))
            for coords in dp.zit_polygons_deg():
                xs = [c[0] for c in coords]; ys = [c[1] for c in coords]
                fig_db.add_trace(go.Scattermap(lat=ys, lon=xs, mode="lines",
                                                    line=dict(width=1.2, color="#e5e7eb"),
                                                    showlegend=False, hoverinfo="skip"))
            fig_db.update_layout(map=dict(style="carto-darkmatter",
                                              center=dict(lat=puntos_vt["lat"].mean(), lon=puntos_vt["lon"].mean()),
                                              zoom=10),
                                  clickmode="event+select")
            db_event = st.plotly_chart(
                dark_fig(fig_db, height=520, margin=dict(l=0, r=0, t=0, b=0)),
                use_container_width=True, on_select="rerun", key="mapa_dbscan",
            )
            punto_db = clicked_point(db_event)
            if punto_db is not None and punto_db.get("customdata") is not None:
                cdb = punto_db["customdata"]
                st.markdown(
                    f"📍 **Localidad:** {cdb[0]}  &nbsp;|&nbsp;  "
                    f"🧩 **Puntos en su cluster:** {int(float(cdb[1]))}  &nbsp;|&nbsp;  "
                    f"📐 **% fuera de ZIT (cluster):** {float(cdb[2]):.0f}%"
                )
            else:
                st.caption("💡 Haz click sobre un punto del mapa para ver el detalle de su cluster aquí.")

    with tcol:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Candidatas a nueva ZIT</div>', unsafe_allow_html=True)
            if len(candidatas):
                show = candidatas[["n_puntos", "pct_fuera_zit", "localidad"]].rename(columns={
                    "n_puntos": "Puntos", "pct_fuera_zit": "% fuera ZIT", "localidad": "Localidad (moda)",
                })
                st.dataframe(show, use_container_width=True, height=380)
            else:
                st.info(
                    "Ningún cluster cumple ambos umbrales con estos parámetros. Baja "
                    "**\"Tamaño mínimo del cluster\"** o **\"% mínimo fuera de ZIT\"** con los "
                    "sliders de arriba hasta que aparezca al menos una candidata."
                )
                if len(resumen_dbscan):
                    grandes = resumen_dbscan[resumen_dbscan["n_puntos"] >= umbral_n]
                    if len(grandes):
                        mejor = grandes.sort_values("pct_fuera_zit", ascending=False).iloc[0]
                        st.caption(
                            f"Diagnóstico: el cluster con más puntos fuera de ZIT que cumple el tamaño "
                            f"mínimo actual tiene **{mejor['pct_fuera_zit']:.0f}%** fuera de ZIT y "
                            f"**{int(mejor['n_puntos'])}** puntos — baja el umbral de % a ese valor o "
                            f"menos para verlo aparecer."
                        )
                    else:
                        mas_grande = resumen_dbscan.sort_values("n_puntos", ascending=False).iloc[0]
                        st.caption(
                            f"Diagnóstico: ningún cluster llega al tamaño mínimo pedido "
                            f"({umbral_n} puntos) — el cluster más grande encontrado tiene "
                            f"**{int(mas_grande['n_puntos'])}** puntos. Baja \"Tamaño mínimo del "
                            f"cluster\" o sube \"eps\"/\"min_samples\" para agrupar más puntos juntos."
                        )
                else:
                    st.caption("Diagnóstico: DBSCAN no encontró ningún cluster con estos eps/min_samples.")

    st.caption(
        f"Veredicto: cluster con ≥{umbral_n} puntos y ≥{umbral_pct}% fuera de ZIT → *candidata a "
        "nueva ZIT*; por debajo del tamaño mínimo → *cluster menor* (se muestra por transparencia, "
        "no es una recomendación firme); puntos sin vecinos suficientes → *aislados* (más candidatos "
        "a fiscalización puntual que a zona nueva)."
    )

with tab_synth:
    st.markdown('<div class="panel-title">Tabla consolidada por localidad (H1, H3, H4, H5)</div>', unsafe_allow_html=True)
    synth_show = synth.rename(columns={
        "localidad": "Localidad", "vt_2023": "VT 2023", "vt_actual": "VT actual",
        "crecimiento_pct": "Crecim. %", "pct_stock_vivienda": "% stock vivienda",
        "avaluo_ph_m2": "Avalúo/m² (COP)", "alojamiento_formal": "Alojamiento formal",
        "gastronomia_bar": "Gastronomía/bar",
    })
    st.dataframe(
        synth_show, use_container_width=True, height=420,
        column_config={
            "Crecim. %": st.column_config.NumberColumn(format="%.1f%%"),
            "% stock vivienda": st.column_config.NumberColumn(format="%.3f%%"),
            "Avalúo/m² (COP)": st.column_config.NumberColumn(format="$ %d"),
        },
    )
    st.download_button(
        "⬇️ Descargar tabla de síntesis (CSV)",
        data=synth.to_csv(index=False).encode("utf-8"),
        file_name="turismo_vivienda_resumen_localidad.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.markdown("### Conclusiones preliminares")

    top_growth_loc = h1.sort_values("crecimiento_pct", ascending=False).index[0]
    top_growth_val = h1.loc[top_growth_loc, "crecimiento_pct"]
    peso_top_loc = h3.iloc[0]

    st.markdown(f"""
1. **H1 — {'confirmada' if crecimiento_ciudad > 0 else 'no se sostiene'}.** La vivienda turística
   creció **{crecimiento_ciudad:.0f}%** entre 2023 y hoy, con crecimientos particularmente altos en
   localidades como **{top_growth_loc}** (**{top_growth_val:.0f}%**).
2. **H2 — {'sostenida' if pct_fuera_actual > 50 else 'no se sostiene en sentido estricto'}.** El
   **{pct_fuera_actual:.1f}%** de la vivienda turística actual está fuera de las ZIT oficiales
   (vs. **{pct_fuera_2023:.1f}%** en 2023).
3. **H3 — el peso sobre el stock de vivienda** es más alto en **{peso_top_loc['localidad']}**, con
   **{peso_top_loc['pct_2025']:.2f}%** del stock residencial en uso turístico (vs.
   {peso_top_loc['pct_2023']:.2f}% en 2023).
4. **H4 — correlación con avalúo catastral:** ρ de Spearman ≈ **{corr_h4:.2f}** entre vivienda
   turística y avalúo por m² a nivel de localidad.
5. **H5 — clúster de economía turística:** correlaciones de **{corr_h5.loc['vivienda_turistica','alojamiento_formal']:.2f}**
   (alojamiento formal) y **{corr_h5.loc['vivienda_turistica','gastronomia_bar']:.2f}** (gastronomía/bar)
   con la vivienda turística — patrón consistente, no ruido.
6. **Extensión DBSCAN:** los clusters geográficos con suficientes puntos fuera de ZIT y tamaño
   relevante son candidatos concretos (lat/lon) a evaluarse como nuevas ZIT en el próximo POT — ver
   la pestaña de al lado y ajustar los umbrales según lo que arroje tu dataset real.
""")
    st.caption(
        "Advertencia estadística: las correlaciones de H4/H5 se calculan sobre ~19-20 localidades — "
        "son patrones descriptivos útiles, no evidencia con significancia estadística robusta a esa "
        "escala. Los números de esta sección se recalculan en vivo sobre los datos cargados "
        "(reales o sintéticos de demo, según el aviso al inicio de la página)."
    )
