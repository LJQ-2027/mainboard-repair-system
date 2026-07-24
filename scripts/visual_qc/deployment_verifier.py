from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile

try:
    from scripts.visual_qc.deployment_manifest import (
        _hash_regular_file,
        _parse_runtime_paths,
        _read_regular_file,
        validate_deployment_manifest,
    )
except ModuleNotFoundError:
    from deployment_manifest import (  # type: ignore[no-redef]
        _hash_regular_file,
        _parse_runtime_paths,
        _read_regular_file,
        validate_deployment_manifest,
    )


def load_json_without_duplicates(path: Path):
    def object_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"JSON contains duplicate field: {key}")
            result[key] = value
        return result

    try:
        content = _read_regular_file(path).decode("utf-8")
        return json.loads(content, object_pairs_hook=object_hook)
    except UnicodeError as exc:
        raise ValueError(f"JSON file must be UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON file is invalid: {path}") from exc


def _validate_tar_members(archive_path: Path) -> None:
    names = set()
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive:
                name = member.name
                path = PurePosixPath(name)
                if (
                    not name
                    or "\x00" in name
                    or "\\" in name
                    or path.is_absolute()
                    or any(part in {"", ".", ".."} for part in path.parts)
                    or not (member.isfile() or member.isdir())
                    or name in names
                ):
                    raise ValueError(f"Archive contains unsafe tar member: {name}")
                names.add(name)
    except (tarfile.TarError, OSError) as exc:
        raise ValueError("Runtime archive is not a valid gzip tar file.") from exc
    if not names:
        raise ValueError("Runtime archive contains no members.")


def verify_input_bundle(
    *,
    manifest_path: Path,
    archive_path: Path,
    expected_manifest: dict,
) -> dict:
    expected = validate_deployment_manifest(expected_manifest)
    manifest = validate_deployment_manifest(
        load_json_without_duplicates(manifest_path)
    )
    if manifest != expected:
        raise ValueError("Deployment manifest does not match expected evidence.")
    archive_evidence = _hash_regular_file(archive_path)
    if archive_evidence["byte_size"] != manifest["archive_bytes"]:
        raise ValueError("Runtime archive byte-size mismatch.")
    if archive_evidence["sha256"] != manifest["archive_sha256"]:
        raise ValueError("Runtime archive SHA-256 mismatch.")
    _validate_tar_members(archive_path)
    return manifest


def _is_junction(path: Path) -> bool:
    checker = getattr(os.path, "isjunction", None)
    return bool(checker and checker(path))


def _verify_regular_tree(app_root: Path) -> None:
    stack = [app_root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                if entry.is_symlink() or _is_junction(path):
                    raise ValueError(
                        f"Extracted runtime contains a symbolic link: {path}"
                    )
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode):
                    stack.append(path)
                elif not stat.S_ISREG(mode):
                    raise ValueError(
                        f"Extracted runtime contains a special file: {path}"
                    )


def verify_extracted_runtime(
    *,
    app_root: Path,
    expected_manifest: dict,
) -> dict:
    expected = validate_deployment_manifest(expected_manifest)
    app_root = Path(app_root)
    try:
        root_mode = app_root.lstat().st_mode
    except OSError as exc:
        raise ValueError(
            "Extracted application root is missing or unsafe."
        ) from exc
    if (
        not stat.S_ISDIR(root_mode)
        or app_root.is_symlink()
        or _is_junction(app_root)
    ):
        raise ValueError("Extracted application root is missing or unsafe.")
    app_root = app_root.resolve(strict=True)
    _verify_regular_tree(app_root)
    runtime_manifest = app_root / "deploy" / "visual-qc-runtime-files.txt"
    content = _read_regular_file(runtime_manifest)
    if hashlib.sha256(content).hexdigest() != expected[
        "runtime_manifest_sha256"
    ]:
        raise ValueError("Extracted runtime manifest SHA-256 mismatch.")
    paths = _parse_runtime_paths(content)
    if len(paths) != expected["runtime_path_count"]:
        raise ValueError("Extracted runtime path count mismatch.")
    for value in paths:
        candidate = app_root / value
        try:
            candidate.resolve().relative_to(app_root)
        except ValueError as exc:
            raise ValueError(
                f"Extracted runtime path escapes root: {value}"
            ) from exc
        if (
            not candidate.exists()
            or candidate.is_symlink()
            or _is_junction(candidate)
        ):
            raise ValueError(f"Extracted runtime path is missing: {value}")
    return expected


def verify_upgrade_report(
    *,
    report_path: Path,
    schema_path: Path,
    snapshot_path: Path,
    expected_manifest: dict,
) -> dict:
    try:
        import jsonschema
    except ImportError as exc:
        raise ValueError(
            "JSON Schema validator is unavailable in candidate runtime."
        ) from exc

    expected = validate_deployment_manifest(expected_manifest)
    report = load_json_without_duplicates(report_path)
    schema = load_json_without_duplicates(schema_path)
    try:
        jsonschema.Draft202012Validator(schema).validate(report)
    except jsonschema.ValidationError as exc:
        raise ValueError("Upgrade report Schema validation failed.") from exc
    if report["status"] != "passed":
        raise ValueError("Upgrade preflight report did not pass.")
    if any(check["status"] != "passed" for check in report["checks"]):
        raise ValueError("Upgrade preflight contains a failed check.")
    snapshot_sha256 = _hash_regular_file(snapshot_path)["sha256"]
    if report["source"]["snapshot_sha256"] != snapshot_sha256:
        raise ValueError(
            "Upgrade preflight source snapshot does not match rollback."
        )
    expected_target = {
        "version": expected["commit_sha"],
        "archive_sha256": expected["archive_sha256"],
        "archive_bytes": expected["archive_bytes"],
        "runtime_manifest_sha256": expected["runtime_manifest_sha256"],
    }
    if report["target"] != expected_target:
        raise ValueError(
            "Upgrade preflight target does not match deployment manifest."
        )
    return report


def _expected_manifest(arguments) -> dict:
    return {
        "schema_version": "VISUAL-QC-DEPLOYMENT-MANIFEST-V1",
        "commit_sha": arguments.commit_sha,
        "archive_sha256": arguments.archive_sha256,
        "archive_bytes": arguments.archive_bytes,
        "runtime_manifest_sha256": arguments.runtime_manifest_sha256,
        "runtime_path_count": arguments.runtime_path_count,
    }


def _add_evidence_arguments(parser) -> None:
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--archive-bytes", required=True, type=int)
    parser.add_argument("--runtime-manifest-sha256", required=True)
    parser.add_argument("--runtime-path-count", required=True, type=int)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify byte-bound Visual-QC deployment evidence."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inputs = commands.add_parser("inputs")
    inputs.add_argument("--manifest", required=True, type=Path)
    inputs.add_argument("--archive", required=True, type=Path)
    _add_evidence_arguments(inputs)

    extracted = commands.add_parser("extracted")
    extracted.add_argument("--app-root", required=True, type=Path)
    _add_evidence_arguments(extracted)

    report = commands.add_parser("report")
    report.add_argument("--report", required=True, type=Path)
    report.add_argument("--schema", required=True, type=Path)
    report.add_argument("--snapshot", required=True, type=Path)
    _add_evidence_arguments(report)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    expected = _expected_manifest(arguments)
    try:
        if arguments.command == "inputs":
            verify_input_bundle(
                manifest_path=arguments.manifest,
                archive_path=arguments.archive,
                expected_manifest=expected,
            )
        elif arguments.command == "extracted":
            verify_extracted_runtime(
                app_root=arguments.app_root,
                expected_manifest=expected,
            )
        else:
            verify_upgrade_report(
                report_path=arguments.report,
                schema_path=arguments.schema,
                snapshot_path=arguments.snapshot,
                expected_manifest=expected,
            )
    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "verification_failed", "message": str(exc)},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            {"status": "passed", "command": arguments.command},
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
