from __future__ import annotations

import uvicorn

from app.config import load_config


def main() -> None:
    cfg = load_config()
    uvicorn.run("app.main:app", host=cfg.app.host, port=cfg.app.port, reload=False)


if __name__ == "__main__":
    main()
