from __future__ import annotations

import argparse
import json
from pathlib import Path

from visual_qc.benchmark import (
    build_proxy_benchmark,
    render_benchmark_markdown,
    run_synthetic_benchmark,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark visual QC registration with proxy evidence.")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/visual-qc-registration-benchmark.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("reports/visual-qc-registration-benchmark.md"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    bundle = {
        "schema_version": "VISUAL-QC-REGISTRATION-BENCHMARK-BUNDLE-V1",
        "field_accuracy_claim_allowed": False,
        "synthetic": run_synthetic_benchmark(project_root),
        "service_manual_proxy": build_proxy_benchmark(project_root),
    }
    output = args.output if args.output.is_absolute() else project_root / args.output
    markdown = args.markdown if args.markdown.is_absolute() else project_root / args.markdown
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    markdown.write_text(
        render_benchmark_markdown(bundle),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "synthetic": bundle["synthetic"]["summary"],
        "service_manual_proxy": bundle["service_manual_proxy"]["summary"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
