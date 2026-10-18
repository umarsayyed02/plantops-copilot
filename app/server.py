from __future__ import annotations

import os

import uvicorn


def server_port() -> int:
    value = int(os.getenv("PORT", "8000"))
    if not 1 <= value <= 65_535:
        raise ValueError("PORT must be between 1 and 65535")
    return value


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=server_port(),
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "*"),
    )


if __name__ == "__main__":
    main()
