# DataJam Bogotá 2026 — [SIDM]

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

### 1) Descargar el proyecto
1. Ve al repositorio de GitHub.
2. Haz clic en `Code` y descarga el archivo ZIP o clónalo con Git.
3. Descomprime la carpeta en tu equipo.

### 2) Preparar el entorno local
1. Abre una terminal en la carpeta del proyecto(puedes oprimir click derecho sobre la carpeta y abrir terminal)
2. Instala las dependencias necesarias:

```powershell
py -m pip install -r requirements.txt
```

### 3) Ejecutar el notebook para obtener los datos reales
1. Abre el notebook `notebooks/01_turismo_vivienda_analisis.ipynb`.
2. Ejecuta todas las celdas para descargar los datasets del Portal de Datos Abiertos de Bogotá.
3. El notebook generará los archivos necesarios en `data/raw/turismo_vivienda/` y los resultados procesados en `data/processed/` y `outputs/`.
4. Si no tienes Jupyter o VS Code, puedes abrir ese mismo notebook en Google Colab:
   - entra a [colab.research.google.com](https://colab.research.google.com)
   - sube `notebooks/01_turismo_vivienda_analisis.ipynb`
   - ejecuta todas las celdas

> Este paso es fundamental. Si no se ejecuta este notebook, el dashboard mostrará un aviso de que está usando datos sintéticos de respaldo y no los datos reales.

### 4) Ejecutar el dashboard
Cuando los datos reales ya estén disponibles, abre una terminal dentro de la carpeta del proyecto y ejecuta:

```powershell
py -m streamlit run dashboard\app.py
```

Luego abre la URL que muestre Streamlit en el navegador, normalmente :

```text
http://localhost:8501
```

### 5) Ver la visualización final
La interfaz mostrará el dashboard con los mapas, métricas y gráficos del análisis del problema. Si el notebook no se ejecutó antes, la app mostrará la versión demo y el aviso correspondiente.

---

## Recomendaciones generales
Para una persona que quiera ver el dashboard sin inconvenientes, el flujo recomendado es:

1. Descargar el repositorio.
2. Instalar dependencias.
3. Ejecutar el notebook principal para descargar los datos reales.
4. Abrir la app con Streamlit.

De esta forma, la visualización final se verá con los datos reales y no con la versión sintética de respaldo.

## Estructura del repositorio
```
/data
  /raw                           -> datasets originales descargados (no versionados si pesan >100MB, ver .gitignore)
  /processed                     -> datasets limpios/integrados, listos para análisis (sí versionados)
/notebooks                       -> notebooks de ideación y análisis, en orden de ejecución
/dashboard
│   ├── app.py                   -> entrypoint de Streamlit
│   ├── data_processing.py       -> misma lógica del notebook cacheada
│   ├── generate_demo_data.py    -> datos sintéticos de respaldo (ver abajo)
│   └── requirements.txt
/outputs                         -> visualizaciones y resultados exportados
/docs                            -> nota técnica, formulario de caracterización y otros documentos de entrega
/pautas y contexto               -> términos de referencia, reglas, ficha metodológica del DataJam (no es parte del entregable)
requirements.txt
config.toml -> tema oscuro
README.md
```
