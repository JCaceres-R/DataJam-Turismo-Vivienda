# /data/raw

Datasets originales, sin procesar, tal como se descargan del [Portal de Datos Abiertos de Bogotá](https://datosabiertos.bogota.gov.co/).

## Cómo encontrar datasets

El portal es un catálogo CKAN. Dos formas útiles de explorarlo:

- **Por categoría (grupo):** `https://datosabiertos.bogota.gov.co/group/?q=&sort=&page=1` — ver categorías y cantidad de datasets en el README principal del repo.
- **Por API (recomendado, evita adivinar URLs de descarga):**
  ```
  # Buscar datasets por palabra clave
  https://datosabiertos.bogota.gov.co/api/3/action/package_search?q=<palabra>&rows=20

  # Ver todos los recursos (formatos y enlaces de descarga reales) de un dataset conocido
  https://datosabiertos.bogota.gov.co/api/3/action/package_show?id=<slug-del-dataset>
  ```
  El `<slug-del-dataset>` es la última parte de la URL cuando se abre el dataset en el navegador (ej. `datosabiertos.bogota.gov.co/dataset/incidentes` → slug `incidentes`).

## turismo_vivienda/ — tema propuesto (activo)

Datos del notebook principal (`notebooks/01_turismo_vivienda_analisis.ipynb`). Se descargan automáticamente al ejecutar el notebook; el índice completo de fuentes con links a cada dataset y su recurso exacto está documentado ahí mismo, no repetido aquí para evitar que quede desactualizado.

`avaluo_catastral_ph_manzana_actual.geojson` pesa ~66MB y no se versiona en git (ver `.gitignore`) — se descarga solo cuando falta.

## exploratorio_seguridad_ciclovia/

Prueba de concepto técnica anterior (tema descartado a favor de turismo+vivienda), se deja como referencia. Contiene:

| Archivo | Dataset origen | Formato | Notas |
|---|---|---|---|
| `incidentes_nuse_c4.csv` | [Incidentes NUSE 123](https://datosabiertos.bogota.gov.co/dataset/incidentes) | CSV (113MB, no versionado en git) | Mensual × localidad × UPZ × tipo de incidente, 2015-2026. Encoding real: UTF-8, pero se lee como `latin-1` y luego se corrige con `.encode('latin-1').decode('utf-8')` (los nombres de localidad vienen "mojibake"). |
| `ciclovia.geojson` / `ciclovia_tramos.xlsx` | [Ciclovía Bogotá](https://datosabiertos.bogota.gov.co/dataset/cicloruta-bogota-d-c) | GeoJSON + XLSX | 16 corredores activos domingos/festivos 7:00-14:00. |
| `escenarios_deportivos.geojson` | [Escenario Deportivo en Parque IDRD](https://datosabiertos.bogota.gov.co/dataset/escenario-deportivo-en-parque-bogota-d-c) | GeoJSON | 57 escenarios, con coordenadas puntuales (`Coordenada_X`/`Coordenada_Y`). |
| `localidades_bogota.geojson` | [Localidad Bogotá D.C.](https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c) | JSON (formato Esri, no GeoJSON estándar — usa `attributes`/`geometry.rings`) | 20 polígonos de localidad, usados para asignar localidad a puntos por contención (point-in-polygon con `shapely`). |
| `poblacion_localidad_2005_2035.ods` | [Proyecciones de población por localidad](https://datosabiertos.bogota.gov.co/dataset/proyecciones-y-retroproyecciones-de-poblacion-2005-2035) | ODS | Encabezados en la fila 5 (no fila 0); columnas de población separadas por sexo y edad simple — hay que sumarlas. Útil para calcular tasas per cápita en vez de solo conteos. |

Cualquiera de estos cruces (o ninguno) puede terminar sirviendo dependiendo del tema que defina el equipo — quedan aquí documentados para no repetir la exploración.
