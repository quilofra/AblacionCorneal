# Repository Notes

## Architecture

- `shared/`: pure Python business logic reused by desktop and web.
- `desktop_app/`: PySide6 desktop interface.
- `web_app/`: FastAPI app plus browser UI in `web_app/static/`.
- `assets/`: shared branding and icons.

## Local commands

- Desktop: `python3 main.py`
- Web: `./scripts/run_web.sh`
- Tests: `pytest -q`
- macOS build: `./scripts/build_mac.sh`

## Deployment intent

- Desktop distribution goes through GitHub Releases.
- Web deployment target is Render using `render.yaml`.

## Guardrails

- Keep business rules in `shared/` whenever both clients need them.
- Do not duplicate calculation logic in browser JavaScript if the Python core can be reused through the web API.
- Do not commit `dist/`, `build/`, `.venv/`, caches or local secrets.
