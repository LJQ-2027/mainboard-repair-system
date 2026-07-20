#!/usr/bin/env python3

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "scripts.visual_qc.server.api:app",
        host="0.0.0.0",
        port=int(os.environ.get("VISUAL_QC_PORT", "3020")),
        proxy_headers=True,
    )
