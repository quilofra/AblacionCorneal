# AblacionCorneal

Repositorio dual para una calculadora clínica de seguridad en ablación corneal:

- app de escritorio en Python + PySide6
- app web en FastAPI + frontend ligero en navegador

Ambas vías reutilizan el mismo core clínico en `shared/`.

## Usar online

La versión web vive en `web_app/` y expone una calculadora real en navegador, no una landing estática.

### Ejecutar localmente

```bash
./scripts/run_web.sh
```

Después abre:

```text
http://127.0.0.1:8000
```

### Publicar la web

La ruta recomendada es Render, porque la web necesita backend Python para reutilizar el core compartido.

Archivos ya preparados:

- `render.yaml`
- `runtime.txt`
- `.env.example`

Variables opcionales para enlaces públicos:

- `GITHUB_REPO_URL`
- `DESKTOP_DOWNLOAD_URL`

URL esperada una vez desplegado en Render:

```text
https://<tu-servicio>.onrender.com
```

## Descargar app

La app nativa de escritorio sigue siendo el cliente principal para macOS.

### Ejecutar localmente

```bash
python3 main.py
```

### Generar build descargable

```bash
./scripts/build_mac.sh
```

Salida esperada:

- `dist/AblacionCorneal.app`
- `dist/AblacionCorneal-macOS.zip`

### Publicar la app descargable

La distribución se hace con GitHub Releases.

1. Haz push a `main`.
2. Crea un tag como `v1.0.0`.
3. Haz push del tag.
4. El workflow de release generará el zip de macOS y lo subirá a la release.

## Arquitectura

```text
.
├── .github/workflows/
├── assets/
├── desktop_app/
├── shared/
├── web_app/
│   └── static/
├── scripts/
├── tests/
├── AGENTS.md
├── AblacionCorneal.spec
├── LICENSE
├── main.py
├── pytest.ini
├── README.md
├── render.yaml
├── requirements.txt
└── runtime.txt
```

## Qué hay en cada parte

- `shared/`: reglas clínicas y cálculo reutilizable.
- `desktop_app/`: interfaz PySide6.
- `web_app/`: servidor FastAPI y frontend navegador.
- `main.py`: entrypoint compatible para seguir lanzando la app desktop desde raíz.

## Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Tests

```bash
pytest -q
```

## CI/CD

Workflows incluidos:

- `CI`: ejecuta `pytest -q` sobre el core compartido y la API web.
- `Release macOS App`: genera la app descargable con PyInstaller al publicar un tag `v*`.

La publicación automática de la web no está activada desde GitHub Actions porque falta la autenticación del proveedor de despliegue. La ruta de despliegue queda preparada con `render.yaml`.

## Variables de entorno

El proyecto no necesita variables para funcionar localmente, pero la web puede usarlas para mostrar enlaces públicos:

```bash
cp .env.example .env
```

Valores disponibles:

- `GITHUB_REPO_URL`
- `DESKTOP_DOWNLOAD_URL`

## Archivos que sí deben versionarse

- `desktop_app/`
- `shared/`
- `web_app/`
- `assets/`
- `tests/`
- `.github/workflows/`
- `AblacionCorneal.spec`
- `render.yaml`
- `runtime.txt`
- `README.md`
- `.gitignore`
- `LICENSE`
- `AGENTS.md`

## Archivos que no deben versionarse

- `.venv/`
- `build/`
- `dist/`
- `__pycache__/`
- `.pytest_cache/`
- `.env`
- `.DS_Store`

## Roadmap breve

- añadir descarga pública enlazada automáticamente al repositorio remoto real
- ampliar tests de UI web
- notarizar la app de macOS si se va a distribuir fuera de GitHub

## Disclaimer

Herramienta de apoyo clínico. No sustituye el criterio médico ni la decisión asistencial.
