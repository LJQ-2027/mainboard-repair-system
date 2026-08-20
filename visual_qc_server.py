#!/usr/bin/env python3

import os

import uvicorn


def runtime_options():
    return {
        "host": os.environ.get("VISUAL_QC_HOST", "127.0.0.1"),
        "port": int(os.environ.get("VISUAL_QC_PORT", "3020")),
    }


if __name__ == "__main__":
    uvicorn.run(
        "scripts.visual_qc.server.api:app",
        **runtime_options(),
        proxy_headers=True,
    )
