from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib import error, parse, request
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""} and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.visual_qc.intake import (
    IntakeValidationError,
    merge_receipt,
    validate_intake_batch,
    validate_intake_receipt,
    write_json_atomic,
)
from scripts.visual_qc.server.provenance import (
    QualifiedHandoffError,
    normalize_qualified_handoff,
    serialize_qualified_handoff,
)


class VisualQcIntakeTransportError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class VisualQcIntakeTransport:
    def __init__(
        self,
        api_base: str,
        *,
        actor_id: str,
        username: str,
        password: str,
        allow_http_localhost: bool = False,
        timeout_seconds: float = 60,
    ):
        parsed = parse.urlparse(api_base)
        is_localhost = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and is_localhost and allow_http_localhost
        ):
            raise ValueError(
                "Visual-QC intake requires HTTPS; HTTP is allowed only for localhost with "
                "--allow-http-localhost."
            )
        if not actor_id or not username or not password:
            raise ValueError("Actor id, username, and password are required for upload.")
        self.api_base = api_base.rstrip("/")
        self.actor_id = actor_id
        self.timeout_seconds = timeout_seconds
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self.authorization = f"Basic {token}"

    def upload(self, entry: dict, *, idempotency_key: str) -> dict:
        try:
            qualified_handoff = normalize_qualified_handoff(
                entry["qualified_handoff"]
            )
        except KeyError as exc:
            raise VisualQcIntakeTransportError(
                "physical_handoff_provenance_required",
                "Physical upload requires qualified handoff provenance.",
            ) from exc
        except QualifiedHandoffError as exc:
            raise VisualQcIntakeTransportError(
                "invalid_qualified_handoff",
                str(exc),
            ) from exc
        checklist = {
            "status": "confirmed",
            "items": entry["capture_checklist"],
            "confirmed_at": None,
        }
        fields = {
            "board_key": entry["board_key"],
            "side_id": entry["side_id"],
            "capture_stage": entry["capture_stage"],
            "evidence_role": "physical_capture",
            "capture_session_id": entry["capture_session_id"],
            "capture_setup_id": entry["capture_setup_id"],
            "capture_checklist": json.dumps(checklist, separators=(",", ":")),
            "intake_batch_id": entry["intake_batch_id"],
            "intake_entry_id": entry["entry_id"],
            "qualified_handoff": serialize_qualified_handoff(
                qualified_handoff
            ),
            "sha256": entry["sha256"],
        }
        body, content_type = self._multipart_body(entry, fields)
        return self._request_json(
            "POST",
            "/cases",
            body=body,
            headers={
                "Content-Type": content_type,
                "Idempotency-Key": idempotency_key,
            },
        )

    def get_job(self, job_id: str) -> dict:
        return self._request_json("GET", f"/jobs/{parse.quote(job_id, safe='')}")

    def _multipart_body(self, entry: dict, fields: dict) -> tuple[bytes, str]:
        content = Path(entry["file_path"]).read_bytes()
        if (
            len(content) != entry["byte_size"]
            or hashlib.sha256(content).hexdigest() != entry["sha256"]
        ):
            raise VisualQcIntakeTransportError(
                "source_changed_after_validation",
                "Visual-QC source changed after validation; upload was not attempted.",
            )
        boundary = f"visual-qc-{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("ascii"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )
        filename = Path(entry["file_path"]).name.replace('"', "")
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                (
                    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {entry['mime_type']}\r\n\r\n".encode("ascii"),
                content,
                b"\r\n",
                f"--{boundary}--\r\n".encode("ascii"),
            ]
        )
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict | None = None,
    ) -> dict:
        request_headers = {
            "Accept": "application/json",
            "Authorization": self.authorization,
            "X-Actor-Id": self.actor_id,
            "X-Actor-Role": "reviewer",
            **(headers or {}),
        }
        http_request = request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
                detail = payload.get("detail", payload)
                code = detail.get("code", f"http_{exc.code}")
                message = detail.get("message", f"Visual-QC API returned HTTP {exc.code}.")
            except (json.JSONDecodeError, AttributeError):
                code = f"http_{exc.code}"
                message = f"Visual-QC API returned HTTP {exc.code}."
            raise VisualQcIntakeTransportError(code, message) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise VisualQcIntakeTransportError(
                "transport_failure", f"Visual-QC API request failed: {type(exc).__name__}"
            ) from exc


def _read_previous_receipt(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeValidationError(f"invalid prior intake receipt: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntakeValidationError("invalid prior intake receipt: root must be an object")
    try:
        validate_intake_receipt(payload)
    except IntakeValidationError as exc:
        raise IntakeValidationError(f"invalid prior intake receipt: {exc}") from exc
    return payload


def _typed_error(exc: BaseException) -> dict:
    return {
        "code": getattr(exc, "code", "transfer_failure"),
        "message": str(exc)[:500] or type(exc).__name__,
    }


def _reconcile_job(
    row: dict,
    receipt: dict,
    receipt_path: Path,
    transport: VisualQcIntakeTransport,
    *,
    wait_for_jobs: bool,
    poll_interval_seconds: float,
    maximum_job_polls: int,
) -> None:
    attempts = maximum_job_polls if wait_for_jobs else 1
    if attempts <= 0:
        raise VisualQcIntakeTransportError(
            "job_poll_timeout", "Visual-QC processing did not reach a terminal state."
        )
    for attempt in range(attempts):
        job = transport.get_job(row["server_job_id"])
        if (
            not isinstance(job, dict)
            or job.get("job_id") != row["server_job_id"]
            or job.get("case_id") != row["server_case_id"]
        ):
            raise VisualQcIntakeTransportError(
                "job_identity_mismatch",
                "Visual-QC job identity does not match the recorded upload.",
            )
        status = job.get("status")
        if status == "succeeded":
            row.update({"state": "completed", "error": None})
            return
        if status == "failed":
            error_payload = job.get("error") or {}
            row.update(
                {
                    "state": "failed",
                    "error": {
                        "code": error_payload.get("code", "processing_failed"),
                        "message": error_payload.get(
                            "message", "Visual-QC processing failed."
                        )[:500],
                    },
                }
            )
            return
        if status not in {"queued", "running"}:
            raise VisualQcIntakeTransportError(
                "invalid_job_response", "Visual-QC job status is invalid."
            )
        row.update({"state": "processing", "error": None})
        write_json_atomic(receipt_path, receipt)
        if not wait_for_jobs:
            return
        if attempt + 1 < attempts:
            time.sleep(max(0, poll_interval_seconds))
    raise VisualQcIntakeTransportError(
        "job_poll_timeout", "Visual-QC processing did not reach a terminal state."
    )


def run_intake(
    manifest_path: Path,
    receipt_path: Path,
    transport: VisualQcIntakeTransport | None,
    *,
    dry_run: bool = False,
    wait_for_jobs: bool = False,
    continue_on_error: bool = False,
    project_root: Path = PROJECT_ROOT,
    expected_manifest_sha256: str | None = None,
    qualified_handoff_by_entry: dict[str, dict] | None = None,
    poll_interval_seconds: float = 1,
    maximum_job_polls: int = 300,
) -> dict:
    manifest_path = Path(manifest_path)
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise IntakeValidationError("intake manifest could not be read") from exc
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256
    ):
        raise IntakeValidationError("intake manifest changed after validation")
    validated = validate_intake_batch(
        manifest_path, Path(project_root), manifest_bytes=manifest_bytes
    )
    for entry in validated["entries"]:
        entry["intake_batch_id"] = validated["batch_id"]
    if qualified_handoff_by_entry is not None:
        expected_entry_ids = {
            entry["entry_id"] for entry in validated["entries"]
        }
        if set(qualified_handoff_by_entry) != expected_entry_ids:
            raise IntakeValidationError(
                "qualified handoff entries do not match the intake batch"
            )
        try:
            for entry in validated["entries"]:
                entry["qualified_handoff"] = normalize_qualified_handoff(
                    qualified_handoff_by_entry[entry["entry_id"]]
                )
        except QualifiedHandoffError as exc:
            raise IntakeValidationError(
                "qualified handoff provenance is invalid"
            ) from exc
    receipt_path = Path(receipt_path)
    receipt = merge_receipt(_read_previous_receipt(receipt_path), validated)
    write_json_atomic(receipt_path, receipt)
    if dry_run:
        return receipt
    if transport is None:
        raise ValueError("A transport is required unless dry_run is enabled.")

    entries_by_id = {entry["entry_id"]: entry for entry in validated["entries"]}
    for row in receipt["entries"]:
        try:
            if row.get("server_case_id") and row.get("server_job_id"):
                _reconcile_job(
                    row,
                    receipt,
                    receipt_path,
                    transport,
                    wait_for_jobs=wait_for_jobs,
                    poll_interval_seconds=poll_interval_seconds,
                    maximum_job_polls=maximum_job_polls,
                )
            else:
                row.update({"state": "uploading", "error": None})
                write_json_atomic(receipt_path, receipt)
                response = transport.upload(
                    entries_by_id[row["entry_id"]],
                    idempotency_key=row["idempotency_key"],
                )
                row["server_case_id"] = response["case_id"]
                row["server_job_id"] = response["job"]["job_id"]
                row["state"] = "uploaded"
                write_json_atomic(receipt_path, receipt)
                if wait_for_jobs:
                    _reconcile_job(
                        row,
                        receipt,
                        receipt_path,
                        transport,
                        wait_for_jobs=True,
                        poll_interval_seconds=poll_interval_seconds,
                        maximum_job_polls=maximum_job_polls,
                    )
            write_json_atomic(receipt_path, receipt)
        except Exception as exc:
            row.update({"state": "failed", "error": _typed_error(exc)})
            write_json_atomic(receipt_path, receipt)
            if not continue_on_error:
                break
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and resumably import an owner-managed Visual-QC photo batch."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--api-base")
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--actor-id")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--allow-http-localhost", action="store_true")
    return parser


def _load_credentials(path: Path | None) -> dict:
    payload = {}
    if path is not None:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("Credential file must contain a JSON object.")
        payload.update(loaded)
    return {
        "username": payload.get("username") or os.environ.get("VISUAL_QC_API_USERNAME"),
        "password": payload.get("password") or os.environ.get("VISUAL_QC_API_PASSWORD"),
        "actor_id": payload.get("actor_id") or os.environ.get("VISUAL_QC_ACTOR_ID"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    manifest_path = arguments.manifest.resolve()
    receipt_path = (
        arguments.receipt.resolve()
        if arguments.receipt
        else manifest_path.with_name(f"{manifest_path.stem}.receipt.json")
    )
    try:
        transport = None
        if not arguments.dry_run:
            credentials = _load_credentials(arguments.credential_file)
            api_base = arguments.api_base or os.environ.get("VISUAL_QC_API_BASE")
            if not api_base:
                raise ValueError("--api-base or VISUAL_QC_API_BASE is required for upload.")
            actor_id = arguments.actor_id or credentials["actor_id"] or credentials["username"]
            transport = VisualQcIntakeTransport(
                api_base,
                actor_id=actor_id or "",
                username=credentials["username"] or "",
                password=credentials["password"] or "",
                allow_http_localhost=arguments.allow_http_localhost,
            )
        result = run_intake(
            manifest_path,
            receipt_path,
            transport,
            dry_run=arguments.dry_run,
            wait_for_jobs=arguments.wait,
            continue_on_error=arguments.continue_on_error,
        )
    except IntakeValidationError as exc:
        print(json.dumps({"status": "validation_failed", "message": str(exc)}))
        return 2
    except (OSError, ValueError, VisualQcIntakeTransportError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}))
        return 1

    counts = Counter(row["state"] for row in result["entries"])
    print(
        json.dumps(
            {
                "status": "ok" if not counts.get("failed") else "failed",
                "batch_id": result["batch_id"],
                "counts": dict(sorted(counts.items())),
                "receipt": str(receipt_path),
            },
            ensure_ascii=False,
        )
    )
    return 1 if counts.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
