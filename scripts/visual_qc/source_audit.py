from __future__ import annotations

import json
import os
from pathlib import Path
import re

from scripts.visual_qc.intake import (
    IntakeValidationError,
    _image_evidence,
    validate_intake_batch,
)
from scripts.visual_qc.source_library import (
    _assert_controlled_path,
    _build_archived_intake,
    _is_reparse_or_symlink,
    _resolve_library_root,
    validate_source_package,
)


SOURCE_AUDIT_SCHEMA_VERSION = "VISUAL-QC-SOURCE-AUDIT-V1"
CANONICAL_OBJECT = re.compile(
    r"^objects/originals/([0-9a-f]{2})/([0-9a-f]{64})\.(jpg|png|webp)$"
)


def _relative(path: Path, library_root: Path) -> str:
    return path.relative_to(library_root).as_posix()


def _package_error(package_id: str, exc: BaseException) -> dict:
    detail = str(exc).lower()
    if "incomplete" in detail:
        code = "incomplete_package"
        message = "Package publication is incomplete."
    elif "known reference" in detail or "revoked proxy" in detail:
        code = "revoked_proxy"
        message = "Package contains material in the current proxy inventory."
    elif any(token in detail for token in ("reparse", "symlink", "escape")):
        code = "unsafe_path"
        message = "Package contains an unsafe controlled path."
    else:
        code = "invalid_package"
        message = "Package validation failed."
    return {
        "package_id": package_id,
        "status": "invalid",
        "error_code": code,
        "message": message,
    }


def _invalid_object(path: str, code: str, message: str) -> dict:
    return {
        "object_path": path,
        "error_code": code,
        "message": message,
    }


def _library_issue(path: str, code: str, message: str) -> dict:
    return {"path": path, "error_code": code, "message": message}


def _scan_objects(originals_root: Path, library_root: Path) -> tuple[list[str], list[dict]]:
    valid_objects: list[str] = []
    invalid_objects: list[dict] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
        for entry in ordered:
            path = Path(entry.path)
            relative = _relative(path, library_root)
            if _is_reparse_or_symlink(path):
                invalid_objects.append(
                    _invalid_object(
                        relative,
                        "unsafe_path",
                        "Object path contains a symlink or reparse point.",
                    )
                )
                continue
            if entry.is_dir(follow_symlinks=False):
                visit(path)
                continue
            if not entry.is_file(follow_symlinks=False):
                invalid_objects.append(
                    _invalid_object(
                        relative,
                        "noncanonical_path",
                        "Object path is not a canonical regular file.",
                    )
                )
                continue
            match = CANONICAL_OBJECT.fullmatch(relative)
            if match is None or match.group(1) != match.group(2)[:2]:
                invalid_objects.append(
                    _invalid_object(
                        relative,
                        "noncanonical_path",
                        "Object path does not match the content-addressed layout.",
                    )
                )
                continue
            try:
                _assert_controlled_path(library_root, path, "source object path")
                evidence = _image_evidence(path)
            except (IntakeValidationError, OSError):
                invalid_objects.append(
                    _invalid_object(
                        relative,
                        "corrupt_object",
                        "Object bytes do not match a valid canonical image.",
                    )
                )
                continue
            if evidence["sha256"] != match.group(2):
                invalid_objects.append(
                    _invalid_object(
                        relative,
                        "corrupt_object",
                        "Object SHA-256 does not match its canonical path.",
                    )
                )
                continue
            valid_objects.append(relative)

    visit(originals_root)
    return sorted(valid_objects), sorted(
        invalid_objects, key=lambda row: row["object_path"]
    )


def audit_source_library(project_root: Path, library_root: Path) -> dict:
    project_root = Path(project_root).resolve()
    supplied_library_root = Path(library_root).expanduser()
    if _is_reparse_or_symlink(supplied_library_root):
        raise IntakeValidationError(
            "controlled source library root contains a reparse point or symlink"
        )
    library_root = _resolve_library_root(project_root, library_root)
    if not library_root.is_dir():
        raise IntakeValidationError("controlled source library does not exist")
    _assert_controlled_path(library_root, library_root, "controlled source library")

    packages = []
    library_issues = []
    referenced_objects: set[str] = set()
    packages_root = library_root / "packages"
    if packages_root.exists():
        if _is_reparse_or_symlink(packages_root):
            library_issues.append(
                _library_issue(
                    "packages",
                    "unsafe_path",
                    "Packages root contains a symlink or reparse point.",
                )
            )
            package_entries = []
        elif not packages_root.is_dir():
            library_issues.append(
                _library_issue(
                    "packages",
                    "invalid_structure",
                    "Packages root is not a directory.",
                )
            )
            package_entries = []
        else:
            _assert_controlled_path(library_root, packages_root, "packages root")
            locks_root = packages_root / ".locks"
            if locks_root.exists():
                if _is_reparse_or_symlink(locks_root) or not locks_root.is_dir():
                    library_issues.append(
                        _library_issue(
                            "packages/.locks",
                            "unsafe_path",
                            "Package locks root is not a safe directory.",
                        )
                    )
                else:
                    for lock_entry in sorted(
                        locks_root.iterdir(), key=lambda path: path.name
                    ):
                        if _is_reparse_or_symlink(lock_entry):
                            library_issues.append(
                                _library_issue(
                                    f"packages/.locks/{lock_entry.name}",
                                    "unsafe_path",
                                    "Package lock contains a symlink or reparse point.",
                                )
                            )
                        elif not lock_entry.is_file():
                            library_issues.append(
                                _library_issue(
                                    f"packages/.locks/{lock_entry.name}",
                                    "invalid_structure",
                                    "Package lock entry is not a regular file.",
                                )
                            )
            package_entries = sorted(
                (path for path in packages_root.iterdir() if path.name != ".locks"),
                key=lambda path: path.name,
            )
        for package_dir in package_entries:
            if _is_reparse_or_symlink(package_dir):
                packages.append(
                    _package_error(
                        package_dir.name,
                        IntakeValidationError("reparse package path"),
                    )
                )
                continue
            if not package_dir.is_dir():
                packages.append(
                    {
                        "package_id": package_dir.name,
                        "status": "invalid",
                        "error_code": "invalid_package_entry",
                        "message": "Packages root contains a non-package entry.",
                    }
                )
                continue
            try:
                validated = validate_source_package(
                    package_dir / "source-package.json",
                    project_root,
                    library_root,
                )
                intake_path = package_dir / f"{validated['batch_id']}.intake.json"
                _assert_controlled_path(
                    library_root, intake_path, "source package intake path"
                )
                try:
                    intake_payload = json.loads(
                        intake_path.read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise IntakeValidationError(
                        "source package intake manifest is invalid"
                    ) from exc
                expected_intake = _build_archived_intake(
                    validated, project_root, library_root
                )
                if intake_payload != expected_intake:
                    raise IntakeValidationError(
                        "source package intake manifest does not match package"
                    )
                validate_intake_batch(intake_path, project_root)
            except (IntakeValidationError, OSError) as exc:
                packages.append(_package_error(package_dir.name, exc))
                continue
            packages.append(
                {
                    "package_id": validated["package_id"],
                    "status": "valid",
                    "entry_count": len(validated["entries"]),
                }
            )
            referenced_objects.update(
                _relative(entry["object_file"], library_root)
                for entry in validated["entries"]
            )

    objects_root = library_root / "objects"
    originals_root = objects_root / "originals"
    object_paths = []
    invalid_objects = []
    if objects_root.exists() and _is_reparse_or_symlink(objects_root):
        library_issues.append(
            _library_issue(
                "objects",
                "unsafe_path",
                "Objects root contains a symlink or reparse point.",
            )
        )
    elif objects_root.exists() and not objects_root.is_dir():
        library_issues.append(
            _library_issue(
                "objects",
                "invalid_structure",
                "Objects root is not a directory.",
            )
        )
    elif originals_root.exists():
        if _is_reparse_or_symlink(originals_root):
            library_issues.append(
                _library_issue(
                    "objects/originals",
                    "unsafe_path",
                    "Originals root contains a symlink or reparse point.",
                )
            )
        elif not originals_root.is_dir():
            library_issues.append(
                _library_issue(
                    "objects/originals",
                    "invalid_structure",
                    "Originals root is not a directory.",
                )
            )
        else:
            _assert_controlled_path(library_root, originals_root, "originals root")
            object_paths, invalid_objects = _scan_objects(
                originals_root, library_root
            )
    orphaned_objects = [
        {"object_path": path, "status": "orphaned"}
        for path in object_paths
        if path not in referenced_objects
    ]
    invalid_packages = sum(row["status"] == "invalid" for row in packages)
    incomplete_packages = sum(
        row.get("error_code") == "incomplete_package" for row in packages
    )
    library_issues = sorted(library_issues, key=lambda row: row["path"])
    status = "issues" if invalid_packages or invalid_objects or library_issues else (
        "attention" if orphaned_objects else "healthy"
    )

    return {
        "schema_version": SOURCE_AUDIT_SCHEMA_VERSION,
        "status": status,
        "counts": {
            "package_total": len(packages),
            "valid_packages": len(packages) - invalid_packages,
            "invalid_packages": invalid_packages,
            "incomplete_packages": incomplete_packages,
            "object_total": len(object_paths) + len(invalid_objects),
            "referenced_objects": len(referenced_objects),
            "invalid_objects": len(invalid_objects),
            "orphaned_objects": len(orphaned_objects),
            "library_issues": len(library_issues),
        },
        "packages": packages,
        "invalid_objects": invalid_objects,
        "orphaned_objects": orphaned_objects,
        "library_issues": library_issues,
    }
