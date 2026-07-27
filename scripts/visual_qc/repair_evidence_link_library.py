"""Append-only controlled library for repair-evidence link revisions."""

from __future__ import annotations

import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

if os.name == "nt":
    import msvcrt

from scripts.visual_qc.intake import (
    IntakeValidationError,
    _require_safe_id,
    write_json_atomic,
)
from scripts.visual_qc.repair_case_contract import (
    REPAIR_CASE_SCHEMA_V1,
    REPAIR_CASE_SCHEMA_V2,
)
from scripts.visual_qc.repair_case_library import validate_repair_case_revision
from scripts.visual_qc.repair_evidence_engineering import (
    board_asset_snapshot_from_context,
    load_board_asset_context,
    resolve_engineering_target_from_context,
)
from scripts.visual_qc.repair_evidence_link_contract import (
    FIXED_FALSE_BOUNDARIES,
    REPAIR_EVIDENCE_LINK_SCHEMA_VERSION,
    RepairEvidenceLinkContractError,
    canonical_sha256,
    validate_physical_evidence_snapshot,
    validate_repair_evidence_link_manifest,
)
from scripts.visual_qc.source_library import (
    _assert_controlled_path,
    _ensure_directory_durable,
    _fsync_directory,
    _is_reparse_or_symlink,
    _package_lock,
    _resolve_library_root,
    _write_completion_marker,
    validate_source_package,
)


LINK_MANIFEST_NAME = "repair-evidence-link.json"
LINK_RECORD_FIELDS = {"physical_evidence_ids", "bindings"}
INPUT_BINDING_FIELDS = {
    "binding_id",
    "repair_case_reference_id",
    "source_fact",
    "target",
    "physical_evidence_id",
    "association_status",
    "visibility_status",
    "evidence_bases",
    "supersedes_binding_id",
}
INPUT_SOURCE_FACT_FIELDS = {"kind", "fact_id"}
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_AUTHORITY_FILE_BYTES = 512 * 1024 * 1024
MAX_LINK_REVISIONS = 5000


class RepairEvidenceLinkLibraryError(ValueError):
    pass


def _error(message: str):
    raise RepairEvidenceLinkLibraryError(message)


def _read_safe_bytes(path: Path, label: str) -> bytes:
    path = Path(path).expanduser().absolute()
    for candidate in (path, *path.parents):
        if _is_reparse_or_symlink(candidate):
            _error(f"{label} contains a reparse point or symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RepairEvidenceLinkLibraryError(f"{label} is missing") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > MAX_INPUT_BYTES
        ):
            _error(f"{label} must be one bounded non-hard-linked regular file")
        content = bytearray()
        while len(content) <= MAX_INPUT_BYTES:
            chunk = os.read(
                descriptor,
                min(1024 * 1024, MAX_INPUT_BYTES + 1 - len(content)),
            )
            if not chunk:
                break
            content.extend(chunk)
        after = os.fstat(descriptor)
        identity = lambda item: (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_nlink,
            getattr(item, "st_mtime_ns", None),
        )
        if (
            len(content) > MAX_INPUT_BYTES
            or identity(before) != identity(after)
            or len(content) != after.st_size
        ):
            _error(f"{label} changed while reading or exceeds its limit")
        return bytes(content)
    finally:
        os.close(descriptor)


def _strict_json_bytes(content: bytes, label: str) -> dict:
    def object_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _error(f"{label} contains duplicate field: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=object_hook,
            parse_constant=lambda token: _error(
                f"{label} contains non-finite number: {token}"
            ),
        )
    except RepairEvidenceLinkLibraryError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepairEvidenceLinkLibraryError(
            f"{label} is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(payload, dict):
        _error(f"{label} root must be an object")
    return payload


def _read_safe_json(path: Path, label: str) -> tuple[dict, str]:
    content = _read_safe_bytes(path, label)
    return _strict_json_bytes(content, label), hashlib.sha256(content).hexdigest()


def _assert_safe_authority_path(path: Path, label: str) -> Path:
    path = Path(path).expanduser().absolute()
    for candidate in (path, *path.parents):
        if _is_reparse_or_symlink(candidate):
            _error(f"{label} contains a reparse point or symlink")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise RepairEvidenceLinkLibraryError(f"{label} is missing") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        _error(f"{label} must be one non-hard-linked regular file")
    return path


def _windows_file_identity(descriptor: int) -> tuple:
    class FileTime(ctypes.Structure):
        _fields_ = [
            ("low", ctypes.c_uint32),
            ("high", ctypes.c_uint32),
        ]

    class ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("attributes", ctypes.c_uint32),
            ("creation_time", FileTime),
            ("access_time", FileTime),
            ("write_time", FileTime),
            ("volume_serial_number", ctypes.c_uint32),
            ("size_high", ctypes.c_uint32),
            ("size_low", ctypes.c_uint32),
            ("number_of_links", ctypes.c_uint32),
            ("file_index_high", ctypes.c_uint32),
            ("file_index_low", ctypes.c_uint32),
        ]

    handle = msvcrt.get_osfhandle(descriptor)
    information = ByHandleFileInformation()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_information = kernel32.GetFileInformationByHandle
    get_information.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ByHandleFileInformation),
    ]
    get_information.restype = ctypes.c_int
    if not get_information(handle, ctypes.byref(information)):
        raise ctypes.WinError(ctypes.get_last_error())
    if information.attributes & 0x400:
        _error("authority descriptor is a reparse point")
    if information.number_of_links != 1:
        _error("authority descriptor must not be hard-linked")
    return (
        "windows",
        information.volume_serial_number,
        (information.file_index_high << 32) | information.file_index_low,
        (information.size_high << 32) | information.size_low,
        information.number_of_links,
        (information.write_time.high << 32) | information.write_time.low,
    )


def _descriptor_state(descriptor: int) -> tuple:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        _error("authority descriptor must be one regular non-hard-linked file")
    if os.name == "nt":
        return _windows_file_identity(descriptor)
    return (
        "posix",
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_nlink,
        getattr(metadata, "st_mtime_ns", None),
    )


def _open_authority_descriptor(path: Path, label: str) -> int:
    path = _assert_safe_authority_path(path, label)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RepairEvidenceLinkLibraryError(
            f"{label} could not be opened safely"
        ) from exc
    try:
        _descriptor_state(descriptor)
        _assert_safe_authority_path(path, label)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_authority_state(path: Path, label: str) -> tuple:
    path = Path(path).expanduser().absolute()
    descriptor = _open_authority_descriptor(path, label)
    try:
        before = _descriptor_state(descriptor)
        digest = hashlib.sha256()
        byte_size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            byte_size += len(chunk)
            if byte_size > MAX_AUTHORITY_FILE_BYTES:
                _error(f"{label} exceeds the authority byte limit")
            digest.update(chunk)
        after = _descriptor_state(descriptor)
        if before != after or byte_size != after[3]:
            _error(f"{label} changed while reading")
    finally:
        os.close(descriptor)

    _assert_safe_authority_path(path, label)
    path_descriptor = _open_authority_descriptor(path, label)
    try:
        path_state = _descriptor_state(path_descriptor)
    finally:
        os.close(path_descriptor)
    _assert_safe_authority_path(path, label)
    if path_state != after:
        _error(f"{label} path identity or metadata changed while reading")
    return after, digest.hexdigest()


class _AuthorityTracker:
    def __init__(self):
        self._states: dict[Path, tuple] = {}
        self._labels: dict[Path, str] = {}

    def capture(self, path: Path, label: str) -> None:
        path = Path(path).expanduser().absolute()
        state = _read_authority_state(path, label)
        previous = self._states.get(path)
        if previous is not None and previous != state:
            _error(f"{self._labels[path]} changed while validating")
        self._states[path] = state
        self._labels[path] = label

    def recheck_all(self) -> None:
        for path, expected in self._states.items():
            state = _read_authority_state(path, self._labels[path])
            if state != expected:
                _error(f"{self._labels[path]} changed while validating")


def _track_source_package_dependencies(
    *,
    package_path: Path,
    library_root: Path,
    tracker: _AuthorityTracker,
) -> None:
    tracker.capture(package_path, "source package manifest")
    raw, _ = _read_safe_json(package_path, "source package manifest")
    entries = raw.get("entries")
    if not isinstance(entries, list):
        _error("source package entries are invalid")
    paths = []
    for entry in entries:
        if not isinstance(entry, dict):
            _error("source package entry is invalid")
        paths.append(entry.get("object_path"))
        source_original = entry.get("source_original")
        if isinstance(source_original, dict):
            paths.append(source_original.get("object_path"))
    for raw_path in paths:
        if not isinstance(raw_path, str):
            _error("source package object path is invalid")
        object_path = _assert_controlled_path(
            library_root,
            library_root / raw_path,
            "source package object",
        )
        tracker.capture(object_path, "source package object")


def _track_case_dependencies(
    *,
    case: dict,
    library_root: Path,
    tracker: _AuthorityTracker,
) -> None:
    links = case.get("package_links")
    evidence = case.get("supporting_evidence")
    if not isinstance(links, list) or not isinstance(evidence, list):
        _error("repair case dependencies are invalid")
    for link in links:
        if not isinstance(link, dict) or not isinstance(
            link.get("package_id"), str
        ):
            _error("repair case package link is invalid")
        _track_source_package_dependencies(
            package_path=(
                library_root
                / "packages"
                / link["package_id"]
                / "source-package.json"
            ),
            library_root=library_root,
            tracker=tracker,
        )
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(
            item.get("object_path"), str
        ):
            _error("repair case supporting evidence is invalid")
        path = _assert_controlled_path(
            library_root,
            library_root / item["object_path"],
            "repair case supporting evidence",
        )
        tracker.capture(path, "repair case supporting evidence")


def _validated_case(
    *,
    manifest_path: Path,
    project_root: Path,
    library_root: Path,
    tracker: _AuthorityTracker | None = None,
) -> tuple[dict, str]:
    manifest_path = _assert_controlled_path(
        library_root, Path(manifest_path), "repair case manifest path"
    )
    if tracker is not None:
        tracker.capture(manifest_path, "repair case manifest")
    raw_before, digest = _read_safe_json(
        manifest_path, "repair case manifest"
    )
    if tracker is not None:
        _track_case_dependencies(
            case=raw_before,
            library_root=library_root,
            tracker=tracker,
        )
    try:
        payload = validate_repair_case_revision(
            manifest_path=manifest_path,
            project_root=project_root,
            library_root=library_root,
        )
    except (IntakeValidationError, ValueError) as exc:
        raise RepairEvidenceLinkLibraryError(
            "repair case revision is invalid"
        ) from exc
    raw_after, digest_after = _read_safe_json(
        manifest_path, "repair case manifest"
    )
    if digest_after != digest or raw_before != raw_after or payload != raw_after:
        _error("repair case revision changed while validating")
    if tracker is not None:
        _track_case_dependencies(
            case=raw_after,
            library_root=library_root,
            tracker=tracker,
        )
        tracker.capture(manifest_path, "repair case manifest")
    return payload, digest


def _case_reference(reference_id: str, payload: dict, digest: str) -> dict:
    return {
        "repair_case_reference_id": _require_safe_id(
            reference_id, "repair_case_reference_id"
        ),
        "repair_case_id": payload["repair_case_id"],
        "revision": payload["revision"],
        "schema_version": payload["schema_version"],
        "manifest_sha256": digest,
        "board_key": payload["board_key"],
        "board_id": payload["board_id"],
    }


def _case_path_for_reference(library_root: Path, reference: dict) -> Path:
    return (
        library_root
        / "cases"
        / reference["repair_case_id"]
        / "revisions"
        / f"{reference['revision']:04d}"
        / "repair-case.json"
    )


def _model_identity_resolved(case: dict) -> bool:
    if case["schema_version"] == REPAIR_CASE_SCHEMA_V1:
        return True
    if case["schema_version"] != REPAIR_CASE_SCHEMA_V2:
        _error("repair case schema version is unsupported")
    value = case.get("boundaries", {}).get("model_identity_resolved")
    if type(value) is not bool:
        _error("repair case model identity boundary is invalid")
    return value


def _source_fact(case: dict, selector: dict) -> dict:
    if not isinstance(selector, dict) or set(selector) != INPUT_SOURCE_FACT_FIELDS:
        _error("source fact selector fields are invalid")
    kind = selector["kind"]
    fact_id = selector["fact_id"]
    collections = {
        "reported_symptom": ("reported_symptoms", "symptom_id", "text", None),
        "finding": ("findings", "finding_id", "description", "claim_status"),
        "repair_action": ("repair_actions", "action_id", "description", None),
    }
    if kind == "outcome":
        if fact_id != "outcome":
            _error("outcome selector must use reserved fact ID")
        item = case["outcome"]
        text = (
            item["description"]
            if item["description"] is not None
            else item["status"]
        )
        claim_status = None
    elif kind in collections:
        collection, id_field, text_field, status_field = collections[kind]
        matches = [item for item in case[collection] if item[id_field] == fact_id]
        if len(matches) != 1:
            _error("source fact does not resolve exactly")
        item = matches[0]
        text = item[text_field]
        claim_status = item[status_field] if status_field else None
    else:
        _error("source fact kind is invalid")
    snapshot = {
        "kind": kind,
        "fact_id": fact_id,
        "display": {"text": text, "claim_status": claim_status},
    }
    return {**snapshot, "fact_sha256": canonical_sha256(snapshot)}


def _source_fact_proves_designator(
    case: dict, selector: dict, *, designator: str, side_id: str
) -> bool:
    kind = selector.get("kind")
    fact_id = selector.get("fact_id")
    if kind == "finding":
        matches = [
            item for item in case["findings"] if item["finding_id"] == fact_id
        ]
        if len(matches) != 1:
            return False
        fact_designator = matches[0]["designator"]
        fact_side = matches[0]["side_id"]
    elif kind == "repair_action":
        matches = [
            item
            for item in case["repair_actions"]
            if item["action_id"] == fact_id
        ]
        if len(matches) != 1:
            return False
        fact_designator = matches[0]["target_designator"]
        fact_side = matches[0]["side_id"]
    else:
        return False
    return fact_designator == designator and fact_side in {None, side_id}


def _validate_binding_record(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != LINK_RECORD_FIELDS:
        _error("binding record fields are invalid")
    ids = payload["physical_evidence_ids"]
    bindings = payload["bindings"]
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(item, str) for item in ids)
        or len(ids) != len(set(ids))
        or not isinstance(bindings, list)
        or not bindings
    ):
        _error("binding record lists are invalid")
    for raw in bindings:
        if not isinstance(raw, dict) or set(raw) != INPUT_BINDING_FIELDS:
            _error("input binding fields are invalid")
        _require_safe_id(raw["binding_id"], "binding_id")
        _require_safe_id(
            raw["repair_case_reference_id"], "repair_case_reference_id"
        )
        _require_safe_id(raw["physical_evidence_id"], "physical_evidence_id")
        if raw["physical_evidence_id"] not in ids:
            _error("binding physical evidence is not selected")
    return copy.deepcopy(payload)


def _load_physical_snapshots(
    paths: list[Path], tracker: _AuthorityTracker | None = None
) -> list[dict]:
    if not isinstance(paths, list) or not paths:
        _error("at least one physical evidence path is required")
    snapshots = []
    seen = set()
    for path in paths:
        if tracker is not None:
            tracker.capture(Path(path), "physical evidence snapshot")
        payload, _ = _read_safe_json(Path(path), "physical evidence snapshot")
        try:
            snapshot = validate_physical_evidence_snapshot(payload)
        except RepairEvidenceLinkContractError as exc:
            raise RepairEvidenceLinkLibraryError(
                "physical evidence snapshot is invalid"
            ) from exc
        evidence_id = snapshot["physical_evidence_id"]
        if evidence_id in seen:
            _error("physical evidence ID is duplicated")
        seen.add(evidence_id)
        snapshots.append(snapshot)
    return snapshots


def _validate_physical_authority(
    snapshot: dict,
    *,
    case: dict,
    project_root: Path,
    library_root: Path,
    tracker: _AuthorityTracker | None = None,
) -> None:
    if (
        snapshot["board_key"] != case["board_key"]
        or snapshot["board_id"] != case["board_id"]
    ):
        _error("physical evidence board does not match repair case")
    source_hash = snapshot["qualified_handoff"][
        "source_package_manifest_sha256"
    ]
    matching_links = [
        link
        for link in case["package_links"]
        if link["source_package_manifest_sha256"] == source_hash
    ]
    if len(matching_links) != 1:
        _error("physical evidence source package is not linked by repair case")
    link = matching_links[0]
    if snapshot["intake"]["entry_id"] not in link["entry_ids"]:
        _error("physical evidence intake entry is not linked by repair case")
    package_path = (
        library_root / "packages" / link["package_id"] / "source-package.json"
    )
    if tracker is not None:
        _track_source_package_dependencies(
            package_path=package_path,
            library_root=library_root,
            tracker=tracker,
        )
    package = validate_source_package(package_path, project_root, library_root)
    if tracker is not None:
        _track_source_package_dependencies(
            package_path=package_path,
            library_root=library_root,
            tracker=tracker,
        )
    if package["batch_id"] != snapshot["intake"]["batch_id"]:
        _error("physical evidence intake batch does not match source package")
    if (
        package["capture_stage"] != snapshot["capture_stage"]
        or link["capture_stage"] != snapshot["capture_stage"]
    ):
        _error("physical evidence capture stage does not match source package")
    entries = [
        item
        for item in package["entries"]
        if item["entry_id"] == snapshot["intake"]["entry_id"]
    ]
    if len(entries) != 1 or entries[0]["side_id"] != snapshot["side_id"]:
        _error("physical evidence side does not match source package")
    if entries[0]["sha256"] != snapshot["image_sha256"]:
        _error("physical evidence image hash does not match source package")


def _reference_authorities(
    references: list[dict],
    *,
    project_root: Path,
    library_root: Path,
    tracker: _AuthorityTracker | None = None,
) -> dict[str, dict]:
    authorities = {}
    for reference in references:
        path = _case_path_for_reference(library_root, reference)
        case, digest = _validated_case(
            manifest_path=path,
            project_root=project_root,
            library_root=library_root,
            tracker=tracker,
        )
        expected = _case_reference(
            reference["repair_case_reference_id"], case, digest
        )
        if reference != expected:
            _error("repair case reference has drifted")
        authorities[reference["repair_case_reference_id"]] = case
    return authorities


def _compile_binding(
    raw: dict,
    *,
    case: dict,
    board_assets: dict,
    target_cache: dict[str, dict],
) -> dict:
    cache_key = canonical_sha256(raw["target"])
    if cache_key not in target_cache:
        target_cache[cache_key] = resolve_engineering_target_from_context(
            board_assets,
            target=raw["target"],
        )
    resolved = copy.deepcopy(target_cache[cache_key])
    if raw["target"]["kind"] == "designator":
        engineering = {
            key: value for key, value in resolved.items() if key != "side_id"
        }
        if (
            not engineering["semantic_identity_proven"]
            and _source_fact_proves_designator(
                case,
                raw["source_fact"],
                designator=engineering["designator"],
                side_id=resolved["side_id"],
            )
        ):
            engineering["semantic_identity_proven"] = True
            engineering["engineering_snapshot_sha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in engineering.items()
                    if key != "engineering_snapshot_sha256"
                }
            )
        target = {
            "kind": "designator",
            "side_id": resolved["side_id"],
            "engineering": engineering,
        }
    else:
        target = resolved
    return {
        "binding_id": raw["binding_id"],
        "repair_case_reference_id": raw["repair_case_reference_id"],
        "source_fact": _source_fact(case, raw["source_fact"]),
        "target": target,
        "physical_evidence_id": raw["physical_evidence_id"],
        "association_status": raw["association_status"],
        "visibility_status": raw["visibility_status"],
        "evidence_bases": copy.deepcopy(raw["evidence_bases"]),
        "supersedes_binding_id": raw["supersedes_binding_id"],
        "boundaries": {
            **copy.deepcopy(FIXED_FALSE_BOUNDARIES),
            "model_identity_resolved": _model_identity_resolved(case),
        },
    }


def _manifest_sha(path: Path) -> str:
    return hashlib.sha256(_read_safe_bytes(path, "link manifest")).hexdigest()


def _directory_identity(path: Path, label: str) -> tuple[int, int]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise RepairEvidenceLinkLibraryError(f"{label} is missing") from exc
    if _is_reparse_or_symlink(path) or not stat.S_ISDIR(metadata.st_mode):
        _error(f"{label} is not a safe directory")
    return metadata.st_dev, metadata.st_ino


def _capture_directory_bindings(paths: tuple[tuple[Path, str], ...]) -> tuple:
    return tuple(
        (path, label, _directory_identity(path, label))
        for path, label in paths
    )


def _validate_directory_bindings(bindings: tuple) -> None:
    for path, label, expected in bindings:
        if _directory_identity(path, label) != expected:
            _error(f"{label} identity changed during publication")


def build_repair_evidence_link_revision(
    *,
    project_root: Path,
    library_root: Path,
    link_set_id: str,
    repair_case_manifest_path: Path,
    physical_evidence_paths: list[Path],
    binding_record: dict,
    previous_manifest_path: Path | None = None,
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    link_set_id = _require_safe_id(link_set_id, "link_set_id")
    tracker = _AuthorityTracker()
    record = _validate_binding_record(binding_record)
    incoming_physical = _load_physical_snapshots(
        physical_evidence_paths, tracker
    )
    if set(record["physical_evidence_ids"]) != {
        item["physical_evidence_id"] for item in incoming_physical
    }:
        _error("binding record physical evidence selection does not match inputs")

    current_case, current_case_sha = _validated_case(
        manifest_path=repair_case_manifest_path,
        project_root=project_root,
        library_root=library_root,
        tracker=tracker,
    )
    previous = None
    previous_sha = None
    if previous_manifest_path is not None:
        previous_sha_before = _manifest_sha(Path(previous_manifest_path))
        previous = validate_repair_evidence_link_revision_on_disk(
            Path(previous_manifest_path),
            project_root=project_root,
            library_root=library_root,
        )
        if previous["link_set_id"] != link_set_id:
            _error("previous manifest belongs to another link set")
        previous_sha = _manifest_sha(Path(previous_manifest_path))
        if previous_sha != previous_sha_before:
            _error("previous link manifest changed while validating")
    revision = 1 if previous is None else previous["revision"] + 1

    board_assets = load_board_asset_context(
        project_root, current_case["board_key"]
    )
    board = board_asset_snapshot_from_context(board_assets)
    if (
        current_case["board_id"] != board["board_id"]
        or (previous is not None and previous["board"] != board)
    ):
        _error("repair case or historical board snapshot does not match")

    references = (
        [] if previous is None else copy.deepcopy(previous["repair_case_references"])
    )
    reference_by_id = {
        item["repair_case_reference_id"]: item for item in references
    }
    current_revision = (
        current_case["repair_case_id"],
        current_case["revision"],
        current_case_sha,
    )
    existing_current = next(
        (
            item
            for item in references
            if (
                item["repair_case_id"],
                item["revision"],
                item["manifest_sha256"],
            )
            == current_revision
        ),
        None,
    )
    incoming_reference_ids = {
        item["repair_case_reference_id"] for item in record["bindings"]
    }
    if existing_current is not None:
        if incoming_reference_ids != {
            existing_current["repair_case_reference_id"]
        }:
            _error("binding repair-case reference ID does not match exact revision")
    else:
        if len(incoming_reference_ids) != 1:
            _error("one new repair-case revision requires one reference ID")
        new_reference_id = next(iter(incoming_reference_ids))
        if new_reference_id in reference_by_id:
            _error("repair-case reference ID conflicts with history")
        if references and any(
            item["repair_case_id"] != current_case["repair_case_id"]
            for item in references
        ):
            _error("link set cannot cross repair cases")
        if references and current_case["revision"] <= max(
            item["revision"] for item in references
        ):
            _error("repair-case references must append a newer revision")
        reference = _case_reference(
            new_reference_id, current_case, current_case_sha
        )
        references.append(reference)
        reference_by_id[new_reference_id] = reference

    authorities = _reference_authorities(
        references,
        project_root=project_root,
        library_root=library_root,
        tracker=tracker,
    )
    physical = [] if previous is None else copy.deepcopy(previous["physical_evidence"])
    physical_by_id = {item["physical_evidence_id"]: item for item in physical}
    for snapshot in incoming_physical:
        _validate_physical_authority(
            snapshot,
            case=current_case,
            project_root=project_root,
            library_root=library_root,
            tracker=tracker,
        )
        evidence_id = snapshot["physical_evidence_id"]
        if evidence_id in physical_by_id:
            if physical_by_id[evidence_id] != snapshot:
                _error("physical evidence ID conflicts with history")
        else:
            physical.append(snapshot)
            physical_by_id[evidence_id] = snapshot

    bindings = [] if previous is None else copy.deepcopy(previous["bindings"])
    binding_ids = {item["binding_id"] for item in bindings}
    target_cache: dict[str, dict] = {}
    for raw in record["bindings"]:
        if raw["binding_id"] in binding_ids:
            _error("binding ID conflicts with history")
        case = authorities.get(raw["repair_case_reference_id"])
        if case is None:
            _error("binding repair-case reference does not resolve")
        compiled = _compile_binding(
            raw,
            case=case,
            board_assets=board_assets,
            target_cache=target_cache,
        )
        evidence = physical_by_id.get(compiled["physical_evidence_id"])
        if evidence is None:
            _error("binding physical evidence does not resolve")
        target_side = compiled["target"]["side_id"]
        if evidence["side_id"] != target_side:
            _error("binding target and physical evidence sides differ")
        bindings.append(compiled)
        binding_ids.add(compiled["binding_id"])

    if previous is not None and (
        references == previous["repair_case_references"]
        and physical == previous["physical_evidence"]
        and bindings == previous["bindings"]
    ):
        _error("link revision adds no evidence or association")
    manifest = {
        "schema_version": REPAIR_EVIDENCE_LINK_SCHEMA_VERSION,
        "link_set_id": link_set_id,
        "revision": revision,
        "previous_manifest_sha256": previous_sha,
        "source_origin": "codex_operator",
        "repair_case_references": references,
        "board": board,
        "physical_evidence": physical,
        "bindings": bindings,
        "boundaries": copy.deepcopy(FIXED_FALSE_BOUNDARIES),
    }
    try:
        validated = validate_repair_evidence_link_manifest(manifest)
    except RepairEvidenceLinkContractError as exc:
        raise RepairEvidenceLinkLibraryError(
            f"repair evidence link manifest is invalid: {exc.code}"
        ) from exc
    tracker.recheck_all()
    return validated


def _scan_revision_directories(
    *,
    revisions_root: Path,
    library_root: Path,
    tracker: _AuthorityTracker,
) -> dict[int, Path]:
    revisions = {}
    for item in revisions_root.iterdir():
        if not item.name.isdigit():
            continue
        if (
            len(item.name) != 4
            or _is_reparse_or_symlink(item)
            or not item.is_dir()
        ):
            _error("link revision chain contains an unsafe revision path")
        revision = int(item.name)
        if revision < 1 or revision in revisions:
            _error("link revision chain contains a fork")
        revisions[revision] = item
        if len(revisions) > MAX_LINK_REVISIONS:
            _error("link revision chain exceeds its revision limit")
    if (
        not revisions
        or min(revisions) != 1
        or max(revisions) != len(revisions)
    ):
        _error("link revision chain has a gap or fork")
    for revision, directory in revisions.items():
        marker = _assert_controlled_path(
            library_root,
            directory / ".complete",
            "link completion marker",
        )
        tracker.capture(marker, "link completion marker")
        if _read_safe_bytes(marker, "link completion marker") != b"complete\n":
            _error(f"link revision {revision} is incomplete")
    return revisions


def _assert_append_only(previous: dict, current: dict) -> None:
    if (
        current["revision"] != previous["revision"] + 1
        or current["link_set_id"] != previous["link_set_id"]
        or current["source_origin"] != previous["source_origin"]
        or current["board"] != previous["board"]
    ):
        _error("link revision identity or sequence is invalid")
    for field in ("repair_case_references", "physical_evidence", "bindings"):
        if current[field][: len(previous[field])] != previous[field]:
            _error(f"link revision mutates historical {field}")
    if (
        len(current["repair_case_references"])
        == len(previous["repair_case_references"])
        and len(current["physical_evidence"]) == len(previous["physical_evidence"])
        and len(current["bindings"]) == len(previous["bindings"])
    ):
        _error("link revision adds no evidence or association")


def _validate_revision_chain_iterative(
    *,
    manifest_path: Path,
    library_root: Path,
    tracker: _AuthorityTracker,
) -> dict:
    revisions_root = manifest_path.parents[1]
    expected_root = (
        library_root
        / "repair-evidence-links"
        / manifest_path.parents[2].name
        / "revisions"
    )
    if revisions_root != expected_root:
        _error("link manifest path does not belong to the controlled library")
    try:
        head_revision = int(manifest_path.parent.name)
    except ValueError as exc:
        raise RepairEvidenceLinkLibraryError(
            "link manifest revision path is invalid"
        ) from exc
    if (
        head_revision < 1
        or head_revision > MAX_LINK_REVISIONS
        or manifest_path.name != LINK_MANIFEST_NAME
    ):
        _error("link manifest revision path is invalid")

    revisions = _scan_revision_directories(
        revisions_root=revisions_root,
        library_root=library_root,
        tracker=tracker,
    )
    if head_revision not in revisions:
        _error("requested link revision is missing")

    previous = None
    previous_sha = None
    head = None
    for revision in range(1, head_revision + 1):
        current_path = revisions[revision] / LINK_MANIFEST_NAME
        current_path = _assert_controlled_path(
            library_root, current_path, "link manifest path"
        )
        tracker.capture(current_path, "link manifest")
        payload, current_sha = _read_safe_json(
            current_path, "link manifest"
        )
        try:
            current = validate_repair_evidence_link_manifest(payload)
        except RepairEvidenceLinkContractError as exc:
            raise RepairEvidenceLinkLibraryError(
                f"link manifest contract is invalid: {exc.code}"
            ) from exc
        if (
            current["revision"] != revision
            or current["link_set_id"] != manifest_path.parents[2].name
        ):
            _error("link manifest path does not match identity and revision")
        if revision == 1:
            if current["previous_manifest_sha256"] is not None:
                _error("revision 1 must not have a parent link hash")
        else:
            if current["previous_manifest_sha256"] != previous_sha:
                _error("previous link manifest hash does not match chain")
            _assert_append_only(previous, current)
        tracker.capture(current_path, "link manifest")
        previous = current
        previous_sha = current_sha
        head = current
    if revisions[head_revision] / LINK_MANIFEST_NAME != manifest_path:
        _error("requested link manifest path is not canonical")
    return head


def _track_board_assets(
    project_root: Path, board: dict, tracker: _AuthorityTracker
) -> None:
    tracker.capture(
        project_root / Path(board["catalog_asset"]["path"]),
        "board catalog asset",
    )
    for item in board["compiled_sources"]:
        tracker.capture(
            project_root / Path(item["path"]),
            f"compiled board asset {item['kind']}",
        )


def _validate_head_authorities(
    manifest: dict,
    *,
    project_root: Path,
    library_root: Path,
    tracker: _AuthorityTracker,
) -> None:
    _track_board_assets(project_root, manifest["board"], tracker)
    board_assets = load_board_asset_context(
        project_root, manifest["board"]["board_key"]
    )
    current_board = board_asset_snapshot_from_context(board_assets)
    if current_board != manifest["board"]:
        _error("board asset snapshot has drifted")
    _track_board_assets(project_root, current_board, tracker)

    authorities = _reference_authorities(
        manifest["repair_case_references"],
        project_root=project_root,
        library_root=library_root,
        tracker=tracker,
    )
    physical_by_id = {
        item["physical_evidence_id"]: item
        for item in manifest["physical_evidence"]
    }
    for snapshot in manifest["physical_evidence"]:
        matching_cases = [
            case
            for case in authorities.values()
            if any(
                link["source_package_manifest_sha256"]
                == snapshot["qualified_handoff"][
                    "source_package_manifest_sha256"
                ]
                for link in case["package_links"]
            )
        ]
        if not matching_cases:
            _error("physical evidence authority is missing")
        for authority in matching_cases:
            _validate_physical_authority(
                snapshot,
                case=authority,
                project_root=project_root,
                library_root=library_root,
                tracker=tracker,
            )

    target_cache: dict[str, dict] = {}
    for binding in manifest["bindings"]:
        case = authorities[binding["repair_case_reference_id"]]
        if binding["source_fact"] != _source_fact(
            case,
            {
                "kind": binding["source_fact"]["kind"],
                "fact_id": binding["source_fact"]["fact_id"],
            },
        ):
            _error("binding source fact has drifted")
        expected_identity = _model_identity_resolved(case)
        if (
            binding["boundaries"]["model_identity_resolved"]
            is not expected_identity
        ):
            _error("binding model identity boundary has drifted")
        target = binding["target"]
        selector = {
            "kind": target["kind"],
            "side_id": target["side_id"],
        }
        if target["kind"] == "board_region":
            selector["region"] = target["region"]
        elif target["kind"] == "designator":
            selector["designator"] = target["engineering"]["designator"]
        cache_key = canonical_sha256(selector)
        if cache_key not in target_cache:
            target_cache[cache_key] = resolve_engineering_target_from_context(
                board_assets,
                target=selector,
            )
        resolved = copy.deepcopy(target_cache[cache_key])
        expected_target = resolved
        if target["kind"] == "designator":
            engineering = {
                key: value
                for key, value in resolved.items()
                if key != "side_id"
            }
            selector_fact = {
                "kind": binding["source_fact"]["kind"],
                "fact_id": binding["source_fact"]["fact_id"],
            }
            if (
                not engineering["semantic_identity_proven"]
                and _source_fact_proves_designator(
                    case,
                    selector_fact,
                    designator=engineering["designator"],
                    side_id=resolved["side_id"],
                )
            ):
                engineering["semantic_identity_proven"] = True
                engineering["engineering_snapshot_sha256"] = canonical_sha256(
                    {
                        key: value
                        for key, value in engineering.items()
                        if key != "engineering_snapshot_sha256"
                    }
                )
            expected_target = {
                "kind": "designator",
                "side_id": resolved["side_id"],
                "engineering": engineering,
            }
        if target != expected_target:
            _error("binding engineering target has drifted")
        evidence = physical_by_id[binding["physical_evidence_id"]]
        if evidence["side_id"] != target["side_id"]:
            _error("binding target and physical evidence sides differ")

    _track_board_assets(project_root, current_board, tracker)
    final_assets = load_board_asset_context(
        project_root, manifest["board"]["board_key"]
    )
    final_board = board_asset_snapshot_from_context(final_assets)
    if final_board != current_board:
        _error("board assets changed while validating")
    _track_board_assets(project_root, final_board, tracker)


def validate_repair_evidence_link_revision_on_disk(
    manifest_path: Path, *, project_root: Path, library_root: Path
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    manifest_path = _assert_controlled_path(
        library_root, Path(manifest_path), "link manifest path"
    )
    tracker = _AuthorityTracker()
    manifest = _validate_revision_chain_iterative(
        manifest_path=manifest_path,
        library_root=library_root,
        tracker=tracker,
    )
    _validate_head_authorities(
        manifest,
        project_root=project_root,
        library_root=library_root,
        tracker=tracker,
    )
    tracker.recheck_all()
    return manifest


def _terminal_replacement(
    start: str, replacements: dict[str, str], label: str
) -> str | None:
    current = start
    seen = {start}
    replacement = replacements.get(current)
    while replacement is not None:
        if replacement in seen:
            _error(f"{label} replacement chain contains a cycle")
        seen.add(replacement)
        current = replacement
        replacement = replacements.get(current)
    return None if current == start else current


def derive_repair_evidence_link_states_on_disk(
    manifest_path: Path, *, project_root: Path, library_root: Path
) -> dict:
    """Expose correction and binding replacement states without mutating V1."""

    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    manifest = validate_repair_evidence_link_revision_on_disk(
        manifest_path,
        project_root=project_root,
        library_root=library_root,
    )
    authorities = _reference_authorities(
        manifest["repair_case_references"],
        project_root=project_root,
        library_root=library_root,
    )
    correction_by_id = {}
    source_replacements = {}
    ordered_references = sorted(
        manifest["repair_case_references"], key=lambda item: item["revision"]
    )
    for reference in ordered_references:
        case = authorities[reference["repair_case_reference_id"]]
        for correction in case["corrections"]:
            correction_id = correction["correction_id"]
            existing = correction_by_id.get(correction_id)
            if existing is not None and existing != correction:
                _error("repair case correction history has drifted")
            correction_by_id[correction_id] = correction
            target = correction["corrects_fact_id"]
            replacement = correction["replacement_fact_id"]
            prior = source_replacements.get(target)
            if prior is not None and prior != replacement:
                _error("source fact has multiple active corrections")
            source_replacements[target] = replacement

    binding_replacements = {}
    for binding in manifest["bindings"]:
        parent = binding["supersedes_binding_id"]
        if parent is not None:
            prior = binding_replacements.get(parent)
            if prior is not None and prior != binding["binding_id"]:
                _error("binding has multiple active replacements")
            binding_replacements[parent] = binding["binding_id"]

    states = []
    for binding in manifest["bindings"]:
        replacement_fact_id = _terminal_replacement(
            binding["source_fact"]["fact_id"],
            source_replacements,
            "source fact",
        )
        replacement_binding_id = _terminal_replacement(
            binding["binding_id"],
            binding_replacements,
            "binding",
        )
        states.append(
            {
                "binding_id": binding["binding_id"],
                "source_fact_superseded": replacement_fact_id is not None,
                "replacement_fact_id": replacement_fact_id,
                "binding_superseded": replacement_binding_id is not None,
                "replacement_binding_id": replacement_binding_id,
            }
        )
    revalidated = validate_repair_evidence_link_revision_on_disk(
        manifest_path,
        project_root=project_root,
        library_root=library_root,
    )
    if revalidated != manifest:
        _error("link revision changed while deriving supersession states")
    return {
        "link_set_id": manifest["link_set_id"],
        "revision": manifest["revision"],
        "bindings": states,
    }


def _result(state: str, manifest_path: Path, manifest: dict) -> dict:
    return {
        "state": state,
        "link_set_id": manifest["link_set_id"],
        "revision": manifest["revision"],
        "manifest_sha256": _manifest_sha(manifest_path),
        "manifest_path": manifest_path.resolve(),
        "repair_case_reference_count": len(manifest["repair_case_references"]),
        "physical_evidence_count": len(manifest["physical_evidence"]),
        "binding_count": len(manifest["bindings"]),
    }


def publish_repair_evidence_link_revision(
    *,
    project_root: Path,
    library_root: Path,
    link_set_id: str,
    repair_case_manifest_path: Path,
    physical_evidence_paths: list[Path],
    binding_record_path: Path,
    previous_manifest_path: Path | None = None,
) -> dict:
    project_root = Path(project_root).resolve()
    library_root = _resolve_library_root(project_root, library_root)
    link_set_id = _require_safe_id(link_set_id, "link_set_id")
    binding_record, _ = _read_safe_json(
        Path(binding_record_path), "binding record"
    )
    links_root = _assert_controlled_path(
        library_root,
        library_root / "repair-evidence-links",
        "repair evidence link library",
    )
    _ensure_directory_durable(links_root)
    link_root = _assert_controlled_path(
        library_root, links_root / link_set_id, "repair evidence link set"
    )
    _ensure_directory_durable(link_root)
    revisions_root = _assert_controlled_path(
        library_root, link_root / "revisions", "repair evidence link revisions"
    )
    _ensure_directory_durable(revisions_root)

    with _package_lock(links_root, link_set_id):
        controlled_directories = (
            (library_root, "controlled source library"),
            (links_root, "repair evidence link library"),
            (link_root, "repair evidence link set"),
            (revisions_root, "repair evidence link revisions"),
        )
        for path, label in controlled_directories:
            _assert_controlled_path(library_root, path, label)
        directory_bindings = _capture_directory_bindings(
            controlled_directories
        )
        manifest = build_repair_evidence_link_revision(
            project_root=project_root,
            library_root=library_root,
            link_set_id=link_set_id,
            repair_case_manifest_path=repair_case_manifest_path,
            physical_evidence_paths=physical_evidence_paths,
            binding_record=binding_record,
            previous_manifest_path=previous_manifest_path,
        )
        _validate_directory_bindings(directory_bindings)
        target = _assert_controlled_path(
            library_root,
            revisions_root / f"{manifest['revision']:04d}",
            "repair evidence link revision",
        )
        manifest_path = target / LINK_MANIFEST_NAME
        if target.exists():
            _validate_directory_bindings(directory_bindings)
            existing = validate_repair_evidence_link_revision_on_disk(
                manifest_path,
                project_root=project_root,
                library_root=library_root,
            )
            if existing != manifest:
                _error(f"repair evidence link revision conflict: {link_set_id}")
            return _result("existing", manifest_path, existing)

        numeric = sorted(
            item
            for item in revisions_root.iterdir()
            if item.name.isdigit()
        )
        expected_names = [
            f"{revision:04d}" for revision in range(1, manifest["revision"])
        ]
        if [item.name for item in numeric] != expected_names:
            _error("repair evidence link revision chain has a gap or fork")
        _validate_directory_bindings(directory_bindings)
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{manifest['revision']:04d}.",
                suffix=".staging",
                dir=revisions_root,
            )
        )
        temporary_identity = _directory_identity(
            temporary, "temporary link revision"
        )
        published_incomplete = False
        published_identity = None
        try:
            write_json_atomic(temporary / LINK_MANIFEST_NAME, manifest)
            _fsync_directory(temporary)
            _validate_directory_bindings(directory_bindings)
            if (
                _directory_identity(temporary, "temporary link revision")
                != temporary_identity
            ):
                _error("temporary link revision identity changed")
            try:
                temporary.rename(target)
            except FileExistsError as exc:
                raise RepairEvidenceLinkLibraryError(
                    f"repair evidence link revision conflict: {link_set_id}"
                ) from exc
            published_incomplete = True
            published_identity = _directory_identity(
                target, "published link revision"
            )
            _validate_directory_bindings(directory_bindings)
            _fsync_directory(revisions_root)
            _write_completion_marker(target / ".complete")
            _fsync_directory(target)
            _fsync_directory(revisions_root)
            _validate_directory_bindings(directory_bindings)
            if (
                _directory_identity(target, "published link revision")
                != published_identity
            ):
                _error("published link revision identity changed")
            published_incomplete = False
        except BaseException:
            try:
                directories_stable = (
                    _validate_directory_bindings(directory_bindings) is None
                )
            except RepairEvidenceLinkLibraryError:
                directories_stable = False
            if published_incomplete and directories_stable and target.exists():
                try:
                    same_target = (
                        published_identity is not None
                        and _directory_identity(
                            target, "published link revision"
                        )
                        == published_identity
                    )
                except RepairEvidenceLinkLibraryError:
                    same_target = False
                if same_target and not (target / ".complete").exists():
                    shutil.rmtree(target)
                    _fsync_directory(revisions_root)
            raise
        finally:
            try:
                directories_stable = (
                    _validate_directory_bindings(directory_bindings) is None
                )
                same_temporary = (
                    temporary.exists()
                    and _directory_identity(
                        temporary, "temporary link revision"
                    )
                    == temporary_identity
                )
            except RepairEvidenceLinkLibraryError:
                directories_stable = False
                same_temporary = False
            if directories_stable and same_temporary:
                shutil.rmtree(temporary, ignore_errors=True)

    validated = validate_repair_evidence_link_revision_on_disk(
        manifest_path,
        project_root=project_root,
        library_root=library_root,
    )
    return _result("created", manifest_path, validated)
