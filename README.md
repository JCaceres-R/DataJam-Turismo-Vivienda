# DataJam Bogotá 2026 — [Nombre del equipo]

> **Estado:** propuesta de tema lista para validar con el equipo completo (notebook ejecutado, resultados preliminares en `notebooks/01_turismo_vivienda_analisis.ipynb`). Pendiente de confirmación final antes de avanzar a dashboard, nota técnica y formulario.

## Descripción del problema abordado

**Pregunta analítica:** ¿En qué localidades de Bogotá se concentra y ha crecido más la vivienda turística tipo Airbnb, qué tanto de ese crecimiento ocurre por fuera de las Zonas de Interés Turístico (ZIT) definidas por el POT, y qué relación tiene con la disponibilidad de vivienda residencial, el avalúo catastral y la presencia de infraestructura turística formal?

Formulada con el método del taller guiado (`pautas y contexto/01.taller_datajam_bogota_problema_publico.pdf`) — ver el notebook para el detalle completo de Territorio/Fenómeno/Pregunta/Hipótesis/Variables y las 6 hipótesis de trabajo (H1-H6, la última usa un mapa auto-organizado / SOM sobre 309 sectores catastrales para encontrar perfiles de economía turística más finos que la localidad).

## Fuentes de datos utilizadas

7 fuentes del [Portal de Datos Abiertos de Bogotá](https://datosabiertos.bogota.gov.co/), integradas por localidad (cruces espaciales y por código): Vivienda Turística, Zonas de Interés Turístico, Proyecciones de Hogares y Viviendas, Localidad Bogotá D.C. (límites), Avalúo Catastral por m² en PH, Alojamiento Turístico y Gastronomía/Bar. Índice completo con links a cada dataset y su recurso exacto de descarga en `notebooks/01_turismo_vivienda_analisis.ipynb`.

Categorías disponibles en el portal (por cantidad de datasets), útiles para seguir explorando:

| Categoría | # datasets |
|---|---:|
| Ambiente y Desarrollo Sostenible | 375 |
| Salud y Protección Social | 230 |
| Economía y Finanzas | 225 |
| Función Pública | 225 |
| Ordenamiento Territorial | 185 |
| Educación | 70 |
| Cultura | 60 |
| Inclusión Social y Reconciliación | 52 |
| Mujer | 49 |
| Participación Ciudadana | 48 |
| Deporte y Recreación | 30 |
| Organismos de Control | 30 |
| Comercio, Industria y Turismo | 25 |
| Justicia y Derecho | 13 |
| Seguridad y Defensa | 12 |
| Gastos Gubernamentales | 11 |
| Ciencia, Tecnología e Innovación | 9 |

Navegar por categoría: https://datosabiertos.bogota.gov.co/group/?q=&sort=&page=1

## Metodología general

Cruce de fuentes públicas por localidad (join directo por código de localidad cuando el dataset lo trae, o point-in-polygon con `shapely` contra los límites oficiales cuando no). Cada hipótesis (H1-H5) se resuelve en su propia sección del notebook, con su fuente, su método y su lectura de resultados documentados en celdas de markdown junto al código.

## Instrucciones de despliegue
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Instrucciones de ejecución
1. `notebooks/00_ideacion_seleccion_tema.ipynb` — proceso de selección de tema (histórico).
2. `notebooks/01_turismo_vivienda_analisis.ipynb` — notebook principal. Descarga automáticamente los datasets que falten en `data/raw/turismo_vivienda/` (no requiere pasos manuales) y genera las tablas/gráficos en `data/processed/` y `outputs/`.
3. `notebooks/01_turismo_vivienda_analisis_COLAB.ipynb` — misma versión, pero standalone para correr en Google Colab (para quien no tenga el entorno local montado): subir el archivo a [colab.research.google.com](https://colab.research.google.com) (`Archivo` → `Subir cuaderno`) y `Entorno de ejecución` → `Ejecutar todas`. No depende de tener el repo clonado.

## Estructura del repositorio
```
/data
  /raw          -> datasets originales descargados (no versionados si pesan >100MB, ver .gitignore)
  /processed    -> datasets limpios/integrados, listos para análisis (sí versionados)
/notebooks      -> notebooks de ideación y análisis, en orden de ejecución
/outputs        -> visualizaciones y resultados exportados
/docs           -> nota técnica, formulario de caracterización y otros documentos de entrega
/pautas y contexto  -> términos de referencia, reglas, ficha metodológica del DataJam (no es parte del entregable)
requirements.txt
README.md
```
