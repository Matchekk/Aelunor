from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

import requests
import uvicorn

from app.runtime_config import APP_MODE_DESKTOP, APP_NAME, resolve_runtime_config


LOCK_HANDLE = None


def configure_desktop_environment() -> Path:
    os.environ.setdefault("AELUNOR_APP_MODE", APP_MODE_DESKTOP)
    config = resolve_runtime_config()
    config.user_data_dir.mkdir(parents=True, exist_ok=True)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DATA_DIR", str(config.data_dir))
    os.environ.setdefault("AELUNOR_LOG_DIR", str(config.logs_dir))
    return config.logs_dir / "aelunor-desktop.log"


def configure_logging(log_path: Path) -> None:
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        encoding="utf-8",
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def acquire_single_instance_lock(logs_dir: Path) -> bool:
    global LOCK_HANDLE
    lock_path = logs_dir / "aelunor.lock"
    LOCK_HANDLE = open(lock_path, "a+b")
    if os.name != "nt":
        return True
    try:
        import msvcrt

        msvcrt.locking(LOCK_HANDLE.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def find_free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(url: str, timeout_sec: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_sec
    last_error: Optional[BaseException] = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=1.5)
            if response.status_code < 500:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Aelunor server did not become ready at {url}: {last_error}")


def error_html(title: str, body: str, log_path: Path) -> str:
    escaped_body = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped_log = str(log_path).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{APP_NAME} Startfehler</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, sans-serif; background: #171412; color: #f4eee7; }}
    main {{ max-width: 760px; margin: 10vh auto; padding: 32px; }}
    h1 {{ font-size: 28px; }}
    pre {{ white-space: pre-wrap; background: #241f1b; border: 1px solid #6c5c4e; padding: 16px; }}
    .path {{ color: #d8bd8a; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>Aelunor konnte nicht vollstaendig gestartet werden. Details stehen im Log:</p>
    <p class="path">{escaped_log}</p>
    <pre>{escaped_body}</pre>
  </main>
</body>
</html>"""


def run() -> int:
    log_path = configure_desktop_environment()
    configure_logging(log_path)
    config = resolve_runtime_config()
    smoke_mode = os.getenv("AELUNOR_DESKTOP_SMOKE", "").strip().lower() in {"1", "true", "yes", "on"}

    if not acquire_single_instance_lock(config.logs_dir):
        if smoke_mode:
            logging.error("Aelunor is already running")
            return 2
        try:
            import webview

            webview.create_window(
                f"{APP_NAME} laeuft bereits",
                html=error_html(
                    "Aelunor laeuft bereits",
                    "Es ist bereits eine Aelunor-Instanz aktiv. Schliesse sie zuerst und starte Aelunor dann erneut.",
                    log_path,
                ),
                width=720,
                height=420,
            )
            webview.start()
        except Exception:
            logging.exception("Unable to show single-instance message")
        return 2

    if not smoke_mode:
        try:
            import webview
        except Exception as exc:
            logging.exception("pywebview is not available")
            raise RuntimeError(
                "pywebview is not installed. Install app dependencies with "
                "`python -m pip install -r requirements-app.txt`."
            ) from exc

    port = find_free_loopback_port()
    url = f"http://127.0.0.1:{port}/v1/hub"
    logging.info("Starting %s desktop mode on %s", APP_NAME, url)

    from app.main import app

    server_config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
        reload=False,
    )
    server = uvicorn.Server(server_config)
    server_thread = threading.Thread(target=server.run, name="aelunor-uvicorn", daemon=True)
    server_thread.start()

    try:
        wait_for_server(url)
    except Exception:
        logging.exception("Aelunor backend failed to start")
        if smoke_mode:
            server.should_exit = True
            server_thread.join(timeout=8)
            return 1
        webview.create_window(
            f"{APP_NAME} Startfehler",
            html=error_html("Aelunor konnte nicht starten", traceback.format_exc(), log_path),
            width=820,
            height=560,
        )
        webview.start()
        server.should_exit = True
        return 1

    if smoke_mode:
        logging.info("Aelunor desktop smoke check succeeded")
        server.should_exit = True
        server_thread.join(timeout=8)
        return 0

    window = webview.create_window(
        APP_NAME,
        url,
        width=1320,
        height=860,
        min_size=(980, 680),
    )

    def on_closed() -> None:
        logging.info("Stopping %s desktop backend", APP_NAME)
        server.should_exit = True

    window.events.closed += on_closed
    webview.start()
    server.should_exit = True
    server_thread.join(timeout=8)
    return 0


def main() -> None:
    try:
        raise SystemExit(run())
    except Exception:
        log_path = configure_desktop_environment()
        configure_logging(log_path)
        logging.exception("Fatal Aelunor desktop startup error")
        try:
            import webview

            webview.create_window(
                f"{APP_NAME} Startfehler",
                html=error_html("Aelunor konnte nicht starten", traceback.format_exc(), log_path),
                width=820,
                height=560,
            )
            webview.start()
        except Exception:
            traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
