from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import cv2
import numpy as np

from .registration import RegistrationConfig, register_board_image
from .synthetic import SyntheticTransformConfig, generate_synthetic_capture


def _repo_path(project_root: Path, browser_path: str) -> Path:
    normalized = browser_path.replace("\\", "/")
    while normalized.startswith("../"):
        normalized = normalized[3:]
    return project_root / normalized


def _load_catalog(project_root: Path) -> dict:
    path = project_root / "knowledge-base/repair-workbench-boards.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_board_sides(project_root: Path, board: dict) -> dict:
    path = _repo_path(project_root, board["side_manifest"])
    return json.loads(path.read_text(encoding="utf-8"))


def _project(matrix: list[float], points: np.ndarray) -> np.ndarray:
    homography = np.asarray(matrix, dtype=np.float64).reshape(3, 3)
    return cv2.perspectiveTransform(points.reshape(-1, 1, 2), homography).reshape(-1, 2)


def _synthetic_config(seed: int) -> SyntheticTransformConfig:
    direction = -1 if seed % 2 else 1
    return SyntheticTransformConfig(
        rotation_degrees=direction * (4 + seed % 4),
        perspective_jitter=0.045 + (seed % 3) * 0.008,
        crop_fraction=0.015 + (seed % 2) * 0.01,
        brightness_delta=-10 - seed % 12,
        contrast=0.94 + (seed % 5) * 0.025,
        shadow_strength=0.08 + (seed % 4) * 0.02,
        max_dimension=1400,
    )


def run_synthetic_benchmark(
    project_root: Path,
    *,
    board_keys: list[str] | None = None,
    seeds: list[int] | None = None,
) -> dict:
    project_root = Path(project_root).resolve()
    catalog = _load_catalog(project_root)
    selected_keys = board_keys or sorted(catalog["boards"])
    selected_seeds = seeds or [41, 82]
    cases = []
    corners = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)

    for board_key in selected_keys:
        board = catalog["boards"][board_key]
        manifest = _load_board_sides(project_root, board)
        for side in manifest["sides"]:
            reference_path = project_root / side["engineering_texture"]
            reference = cv2.imread(str(reference_path), cv2.IMREAD_COLOR)
            if reference is None:
                raise FileNotFoundError(f"Unable to load engineering texture: {reference_path}")
            for seed in selected_seeds:
                capture, synthetic = generate_synthetic_capture(
                    reference,
                    _synthetic_config(seed),
                    seed=seed,
                )
                result = register_board_image(
                    reference,
                    capture,
                    RegistrationConfig(max_dimension=1400),
                )
                mean_corner_error = None
                if result["status"] == "candidate":
                    expected = _project(synthetic["expected_board_to_image_matrix"], corners)
                    actual = _project(result["board_to_image_matrix"], corners)
                    mean_corner_error = float(np.linalg.norm(expected - actual, axis=1).mean())
                cases.append(
                    {
                        "case_id": f"{board_key}-{side['side_id']}-seed-{seed}",
                        "board_key": board_key,
                        "board_id": manifest["board_id"],
                        "side_id": side["side_id"],
                        "evidence_role": "synthetic_proxy",
                        "seed": seed,
                        "status": result["status"],
                        "failure_code": result["failure"]["code"] if result["failure"] else None,
                        "mean_corner_error": mean_corner_error,
                        "registration": result,
                        "counts_as_field_qc_evidence": False,
                    }
                )

    status_counts = Counter(case["status"] for case in cases)
    corner_errors = [case["mean_corner_error"] for case in cases if case["mean_corner_error"] is not None]
    return {
        "schema_version": "VISUAL-QC-REGISTRATION-BENCHMARK-V1",
        "evidence_role": "synthetic_proxy",
        "field_accuracy_claim_allowed": False,
        "summary": {
            "case_count": len(cases),
            "candidate_count": status_counts["candidate"],
            "manual_required_count": status_counts["manual_required"],
            "status_counts": dict(sorted(status_counts.items())),
            "mean_corner_error": float(np.mean(corner_errors)) if corner_errors else None,
            "maximum_corner_error": max(corner_errors, default=None),
        },
        "cases": cases,
    }


def _model_to_board(catalog: dict) -> dict[str, tuple[str, dict]]:
    result = {}
    for board_key, board in catalog["boards"].items():
        models = [board["model"], *board.get("compatible_models", [])]
        for model in models:
            result[model] = (board_key, board)
    return result


def _best_registration(results: list[tuple[str, dict]]) -> tuple[str, dict]:
    candidates = [item for item in results if item[1]["status"] == "candidate"]
    if candidates:
        return max(candidates, key=lambda item: item[1]["evidence"]["inlier_count"])
    return max(
        results,
        key=lambda item: max(
            (attempt.get("matches", 0) for attempt in item[1]["evidence"].get("attempts", [])),
            default=0,
        ),
    )


def build_proxy_benchmark(project_root: Path) -> dict:
    project_root = Path(project_root).resolve()
    catalog = _load_catalog(project_root)
    model_map = _model_to_board(catalog)
    review_path = project_root / "knowledge-base/vision-reference-review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    cases = []

    for model, model_review in review["models"].items():
        for asset_path, annotation in model_review.get("assets", {}).items():
            if annotation.get("review_status") != "approved":
                continue
            case = {
                "case_id": f"{model.lower()}-{Path(asset_path).stem}",
                "model": model,
                "asset_path": asset_path,
                "evidence_role": "service_manual_proxy",
                "reference_role": annotation.get("reference_role"),
                "board_scope": annotation.get("board_scope"),
                "declared_board_side": annotation.get("board_side", "unknown"),
                "counts_as_field_qc_evidence": False,
            }
            if model not in model_map:
                case.update(
                    status="not_comparable",
                    comparison_reason="board_reference_unavailable",
                    board_key=None,
                    selected_side_id=None,
                    registration=None,
                )
                cases.append(case)
                continue
            if (
                annotation.get("reference_role") != "installed_mainboard"
                or annotation.get("board_scope") != "main"
            ):
                case.update(
                    status="not_comparable",
                    comparison_reason="reference_role_not_isolated_mainboard",
                    board_key=model_map[model][0],
                    selected_side_id=None,
                    registration=None,
                )
                cases.append(case)
                continue

            image = cv2.imread(str(project_root / asset_path), cv2.IMREAD_COLOR)
            if image is None:
                case.update(
                    status="missing_asset",
                    comparison_reason="reviewed_asset_missing",
                    board_key=model_map[model][0],
                    selected_side_id=None,
                    registration=None,
                )
                cases.append(case)
                continue

            board_key, board = model_map[model]
            manifest = _load_board_sides(project_root, board)
            registrations = []
            for side in manifest["sides"]:
                reference = cv2.imread(
                    str(project_root / side["engineering_texture"]),
                    cv2.IMREAD_COLOR,
                )
                if reference is None:
                    continue
                registrations.append(
                    (
                        side["side_id"],
                        register_board_image(
                            reference,
                            image,
                            RegistrationConfig(max_dimension=1000),
                        ),
                    )
                )
            if not registrations:
                case.update(
                    status="not_comparable",
                    comparison_reason="engineering_texture_unavailable",
                    board_key=board_key,
                    selected_side_id=None,
                    registration=None,
                )
            else:
                side_id, result = _best_registration(registrations)
                case.update(
                    status=result["status"],
                    comparison_reason=(
                        "automatic_candidate_requires_review"
                        if result["status"] == "candidate"
                        else result["failure"]["code"]
                    ),
                    board_key=board_key,
                    selected_side_id=side_id,
                    registration=result,
                )
            cases.append(case)

    status_counts = Counter(case["status"] for case in cases)
    return {
        "schema_version": "VISUAL-QC-REGISTRATION-BENCHMARK-V1",
        "evidence_role": "service_manual_proxy",
        "field_accuracy_claim_allowed": False,
        "summary": {
            "case_count": len(cases),
            "status_counts": dict(sorted(status_counts.items())),
            "comparable_count": sum(case["status"] in {"candidate", "manual_required"} for case in cases),
            "not_comparable_count": status_counts["not_comparable"],
        },
        "cases": cases,
    }


def render_benchmark_markdown(bundle: dict) -> str:
    synthetic = bundle["synthetic"]
    proxies = bundle["service_manual_proxy"]
    lines = [
        "# Visual QC Registration Benchmark",
        "",
        "This report contains proxy engineering evidence only. It does not establish field QC accuracy.",
        "",
        "## Synthetic point-map transforms",
        "",
        f"- Cases: {synthetic['summary']['case_count']}",
        f"- Automatic candidates: {synthetic['summary']['candidate_count']}",
        f"- Manual fallback: {synthetic['summary']['manual_required_count']}",
        f"- Mean normalized corner error: {synthetic['summary']['mean_corner_error']}",
        f"- Maximum normalized corner error: {synthetic['summary']['maximum_corner_error']}",
        "",
        "## Reviewed Service Manual proxies",
        "",
        f"- Reviewed images: {proxies['summary']['case_count']}",
        f"- Comparable attempts: {proxies['summary']['comparable_count']}",
        f"- Not comparable: {proxies['summary']['not_comparable_count']}",
        f"- Status counts: {json.dumps(proxies['summary']['status_counts'], ensure_ascii=False, sort_keys=True)}",
        "",
        "## Evidence boundary",
        "",
        "- Synthetic and Service Manual images never count as physical-board accuracy evidence.",
        "- Automatic registration remains a draft candidate until human review.",
        "- Failure returns the reviewed manual four-point workflow.",
        "- A known bare-board front/back physical photo set remains the real acceptance gate.",
        "",
    ]
    return "\n".join(lines)
