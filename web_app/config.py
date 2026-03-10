from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WebSettings:
    app_name: str
    github_repo_url: str | None
    desktop_download_url: str | None


def load_settings() -> WebSettings:
    github_repo_url = os.getenv("GITHUB_REPO_URL", "").strip() or None
    desktop_download_url = os.getenv("DESKTOP_DOWNLOAD_URL", "").strip() or None

    if desktop_download_url is None and github_repo_url:
        desktop_download_url = f"{github_repo_url.rstrip('/')}/releases/latest"

    return WebSettings(
        app_name="AblacionCorneal",
        github_repo_url=github_repo_url,
        desktop_download_url=desktop_download_url,
    )
