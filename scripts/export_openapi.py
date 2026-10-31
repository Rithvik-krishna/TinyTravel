#!/usr/bin/env python3
"""Export OpenAPI JSON schema from FastAPI app into docs/openapi.json."""
import json
import sys
from pathlib import Path

# Ensure api is importable
repo_root = Path(__file__).resolve().parents[1]
api_dir = repo_root / "api"
sys.path.insert(0, str(api_dir))

from main import app

def export_openapi():
    schema = app.openapi()
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_file = docs_dir / "openapi.json"
    out_file.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"OpenAPI schema exported to {out_file} ({out_file.stat().st_size} bytes)")

if __name__ == "__main__":
    export_openapi()
