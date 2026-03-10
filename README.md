# AblacionCorneal

Aplicación de escritorio en Python con PySide6 para evaluar criterios de seguridad en planificación de ablación corneal. Calcula porcentaje de ablación, lecho estromal residual, paquimetría postoperatoria, factor limitante y margen de seguridad.

## Tipo de proyecto

- App de escritorio Python
- Interfaz nativa con PySide6
- No es una web estática
- No es apta para GitHub Pages

## Estado de publicación recomendado

Este proyecto debe publicarse como repositorio en GitHub y distribuirse como binario descargable mediante GitHub Releases. La app actual no se puede desplegar directamente como sitio web porque su interfaz es de escritorio.

## Requisitos

- Python 3.12 recomendado
- macOS para generar `AblacionCorneal.app`

## Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar en local

```bash
python3 main.py
```

## Tests

```bash
pytest -q
```

## Build local para macOS

```bash
./scripts/build_mac.sh
```

Salida esperada:

- `dist/AblacionCorneal.app`
- `dist/AblacionCorneal-macOS.zip`

## Publicación en GitHub

### Opción recomendada

1. Sube el repositorio a GitHub.
2. Haz push a `main` para ejecutar la CI.
3. Crea un tag de versión, por ejemplo `v1.0.0`.
4. Haz push del tag.
5. GitHub Actions generará `AblacionCorneal-macOS.zip` y lo subirá a una Release.

### Workflow incluido

- `CI`: ejecuta tests en cada push y pull request.
- `Release macOS App`: genera la app de macOS cuando subes un tag `v*`.

## Archivos que sí deben versionarse

- `main.py`
- `calculator.py`
- `styles.py`
- `requirements.txt`
- `pytest.ini`
- `README.md`
- `LICENSE`
- `AblacionCorneal.spec`
- `scripts/build_mac.sh`
- `assets/app_icon.png`
- `assets/app_icon.svg`
- `tests/test_calculator.py`
- `.github/workflows/ci.yml`
- `.github/workflows/release-macos.yml`

## Archivos que no deben versionarse

- `.venv/`
- `build/`
- `dist/`
- `__pycache__/`
- `.pytest_cache/`
- `.DS_Store`
- `.env`
- `.env.*`
- `.idea/`
- `.vscode/`

## Variables de entorno

Actualmente el proyecto no usa variables de entorno ni requiere `.env`.

## Estructura del proyecto

```text
.
├── .github/workflows/
├── assets/
├── scripts/
├── tests/
├── AblacionCorneal.spec
├── calculator.py
├── LICENSE
├── main.py
├── pytest.ini
├── README.md
├── requirements.txt
└── styles.py
```

## Posibles problemas habituales

- `python3: command not found`: instala Python 3.12 o ajusta el ejecutable disponible.
- `PySide6` no compila o falla al instalar: actualiza `pip` y recrea el entorno virtual.
- `PyInstaller` genera una app pero macOS la bloquea: abre la app manualmente o firma/notariza si vas a distribuirla ampliamente.
- El workflow de release no se ejecuta: comprueba que el tag empiece por `v`, por ejemplo `v1.0.0`.

## Disclaimer

Herramienta de apoyo clínico. No sustituye el criterio médico.
