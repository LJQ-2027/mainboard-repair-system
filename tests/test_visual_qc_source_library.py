from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import cv2
import jsonschema
import numpy as np
import scripts.visual_qc.source_library as source_library_module

from scripts.visual_qc.intake import (
    IntakeValidationError,
    validate_intake_batch,
    write_json_atomic,
)
from scripts.visual_qc.source_library import (
    ENTRY_FIELDS,
    PACKAGE_FIELDS,
    SOURCE_PACKAGE_SCHEMA_VERSION,
    build_source_package,
    stage_source_package,
    validate_source_package,
)
from scripts.visual_qc.proxy_inventory import _collect_proxy_paths, known_proxy_hashes


ROOT = Path(__file__).resolve().parents[1]


def encode_image(extension, *, width=180, height=120, value=170):
    image = np.full((height, width, 3), value, dtype=np.uint8)
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise RuntimeError(f"Unable to encode test image: {extension}")
    return encoded.tobytes()


class VisualQcSourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library = self.root / "controlled-library"
        self.front = self.root / "incoming-front.jpeg"
        self.back = self.root / "incoming-back.png"
        self.front.write_bytes(encode_image(".jpg", value=180))
        self.back.write_bytes(encode_image(".png", value=120))

    def tearDown(self):
        for link in reversed(getattr(self, "directory_links", [])):
            if link.exists():
                os.rmdir(link)
        self.temp_dir.cleanup()

    def create_directory_link(self, link, target):
        target.mkdir(parents=True, exist_ok=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if result.returncode != 0:
                self.skipTest(f"Unable to create test junction: {result.stderr}")
        else:
            link.symlink_to(target, target_is_directory=True)
        self.directory_links = getattr(self, "directory_links", [])
        self.directory_links.append(link)

    def options(self, **overrides):
        options = {
            "project_root": ROOT,
            "library_root": self.library,
            "package_id": "km4-unit-001-source",
            "batch_id": "km4-unit-001-batch",
            "board_key": "km4-f151",
            "capture_session_id": "km4-unit-001",
            "capture_stage": "before_repair",
            "capture_setup_id": "standard-bench",
            "image_assignments": [
                ("main_page_2", self.back),
                ("main_page_1", self.front),
            ],
            "milo_physical_source_confirmed": True,
            "capture_checklist_confirmed": True,
        }
        options.update(overrides)
        return options

    def test_build_source_package_is_deterministic_and_content_addressed(self):
        first = build_source_package(**self.options())
        second = build_source_package(**self.options())

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], SOURCE_PACKAGE_SCHEMA_VERSION)
        self.assertEqual(first["source_origin"], "milo_supplied")
        self.assertIs(first["physical_source_confirmed"], True)
        self.assertEqual(first["board_key"], "km4-f151")
        self.assertEqual(first["board_id"], "BOARD-KM4-F151-MAIN-V1.2")
        self.assertEqual(first["capture_stage"], "before_repair")
        self.assertEqual(
            [entry["side_id"] for entry in first["entries"]],
            ["main_page_1", "main_page_2"],
        )

        front = first["entries"][0]
        front_hash = hashlib.sha256(self.front.read_bytes()).hexdigest()
        self.assertEqual(front["original_filename"], "incoming-front.jpeg")
        self.assertEqual(front["mime_type"], "image/jpeg")
        self.assertEqual(front["width"], 180)
        self.assertEqual(front["height"], 120)
        self.assertEqual(front["byte_size"], len(self.front.read_bytes()))
        self.assertEqual(front["sha256"], front_hash)
        self.assertEqual(
            front["object_path"],
            f"objects/originals/{front_hash[:2]}/{front_hash}.jpg",
        )
        self.assertNotIn("source_path", json.dumps(first))
        self.assertNotIn("created_at", first)
        self.assertRegex(first["proxy_inventory_sha256"], r"^[0-9a-f]{64}$")

    def test_runtime_contract_matches_and_satisfies_json_schema(self):
        payload = build_source_package(**self.options())
        schema = json.loads(
            (
                ROOT
                / "knowledge-base"
                / "visual-qc-source-package-v1-schema.json"
            ).read_text(encoding="utf-8")
        )

        jsonschema.Draft202012Validator(schema).validate(payload)
        self.assertEqual(set(schema["required"]), PACKAGE_FIELDS)
        self.assertEqual(
            set(schema["properties"]["entries"]["items"]["required"]),
            ENTRY_FIELDS,
        )

    def test_runtime_rejects_uppercase_proxy_inventory_hash(self):
        payload = build_source_package(**self.options())
        payload["proxy_inventory_sha256"] = payload[
            "proxy_inventory_sha256"
        ].upper()
        manifest_path = self.materialize_package(payload)

        with self.assertRaisesRegex(IntakeValidationError, "proxy_inventory_sha256"):
            validate_source_package(manifest_path, ROOT, self.library)

    def test_windows_equivalent_package_ids_are_rejected_before_writes(self):
        for package_id in ("alias.", "CON", "nul.txt", "LPT1"):
            with self.subTest(package_id=package_id):
                with self.assertRaisesRegex(IntakeValidationError, "unsafe package_id"):
                    stage_source_package(**self.options(package_id=package_id))
        self.assertFalse(self.library.exists())

    def test_package_requires_explicit_physical_source_confirmation(self):
        with self.assertRaisesRegex(
            IntakeValidationError, "Milo-supplied physical source confirmation"
        ):
            build_source_package(
                **self.options(milo_physical_source_confirmed=False)
            )

    def test_library_root_must_be_outside_the_repository(self):
        with self.assertRaisesRegex(IntakeValidationError, "outside the project repository"):
            build_source_package(
                **self.options(library_root=ROOT / ".local" / "visual-source-library")
            )
        self.assertFalse((ROOT / ".local" / "visual-source-library").exists())

    def test_existing_intake_validation_rejects_duplicates_and_invalid_images(self):
        with self.assertRaisesRegex(IntakeValidationError, "duplicate side_id"):
            build_source_package(
                **self.options(
                    image_assignments=[
                        ("main_page_1", self.front),
                        ("main_page_1", self.back),
                    ]
                )
            )

        with self.assertRaisesRegex(IntakeValidationError, "duplicate resolved image path"):
            build_source_package(
                **self.options(
                    image_assignments=[
                        ("main_page_1", self.front),
                        ("main_page_2", self.root / "." / self.front.name),
                    ]
                )
            )

        broken = self.root / "broken.jpg"
        broken.write_bytes(b"not-an-image")
        with self.assertRaisesRegex(IntakeValidationError, "image signature"):
            build_source_package(
                **self.options(image_assignments=[("main_page_1", broken)])
            )

    def test_known_proxy_bytes_remain_blocked_after_external_copy(self):
        proxy = (
            ROOT
            / "assets"
            / "vision-reference-gallery"
            / "km4"
            / "embedded"
            / "page-003-image-02.jpg"
        )
        copied = self.root / "renamed-photo.jpg"
        copied.write_bytes(proxy.read_bytes())

        with self.assertRaisesRegex(
            IntakeValidationError, "known reference or proxy image"
        ):
            build_source_package(
                **self.options(image_assignments=[("main_page_1", copied)])
            )

    def materialize_package(self, payload):
        package_dir = self.library / "packages" / payload["package_id"]
        package_dir.mkdir(parents=True)
        source_by_side = {
            "main_page_1": self.front,
            "main_page_2": self.back,
        }
        for entry in payload["entries"]:
            destination = self.library / entry["object_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_by_side[entry["side_id"]].read_bytes())
        manifest_path = package_dir / "source-package.json"
        write_json_atomic(manifest_path, payload)
        (package_dir / ".complete").write_text("complete\n", encoding="ascii")
        return manifest_path

    def test_validate_source_package_verifies_objects_and_board_identity(self):
        payload = build_source_package(**self.options())
        manifest_path = self.materialize_package(payload)

        validated = validate_source_package(manifest_path, ROOT, self.library)

        self.assertEqual(validated["package_id"], payload["package_id"])
        self.assertEqual(len(validated["entries"]), 2)
        self.assertEqual(
            validated["entries"][0]["object_file"],
            (self.library / payload["entries"][0]["object_path"]).resolve(),
        )

    def test_validate_source_package_rejects_missing_completion_marker(self):
        payload = build_source_package(**self.options())
        manifest_path = self.materialize_package(payload)
        (manifest_path.parent / ".complete").unlink()

        with self.assertRaisesRegex(IntakeValidationError, "incomplete"):
            validate_source_package(manifest_path, ROOT, self.library)

    def test_validate_source_package_checks_completion_marker_leaf(self):
        payload = build_source_package(**self.options())
        manifest_path = self.materialize_package(payload)
        marker = manifest_path.parent / ".complete"
        marker.unlink()
        self.create_directory_link(marker, self.root / "outside-marker")

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink"):
            validate_source_package(manifest_path, ROOT, self.library)

    def test_validate_source_package_rejects_path_escape_and_corruption(self):
        payload = build_source_package(**self.options())
        manifest_path = self.materialize_package(payload)

        escaped = json.loads(manifest_path.read_text(encoding="utf-8"))
        escaped["entries"][0]["object_path"] = "../outside.jpg"
        write_json_atomic(manifest_path, escaped)
        with self.assertRaisesRegex(IntakeValidationError, "object_path"):
            validate_source_package(manifest_path, ROOT, self.library)

        write_json_atomic(manifest_path, payload)
        object_path = self.library / payload["entries"][0]["object_path"]
        object_path.write_bytes(b"corrupted")
        with self.assertRaisesRegex(IntakeValidationError, "object integrity"):
            validate_source_package(manifest_path, ROOT, self.library)

    def test_package_validator_rejects_junction_escape(self):
        payload = build_source_package(**self.options())
        source_by_side = {
            "main_page_1": self.front,
            "main_page_2": self.back,
        }
        for entry in payload["entries"]:
            destination = self.library / entry["object_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_by_side[entry["side_id"]].read_bytes())
        outside = self.root / "outside-package"
        outside.mkdir()
        write_json_atomic(outside / "source-package.json", payload)
        (outside / ".complete").write_text("complete\n", encoding="ascii")
        link = self.library / "packages" / payload["package_id"]
        self.create_directory_link(link, outside)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink|escape"):
            validate_source_package(link / "source-package.json", ROOT, self.library)

    def test_staging_rejects_packages_root_junction_without_external_writes(self):
        outside = self.root / "outside-packages"
        self.create_directory_link(self.library / "packages", outside)

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink|escape"):
            stage_source_package(**self.options())

        self.assertEqual(list(outside.iterdir()), [])

    def test_staging_rejects_reparse_package_lock_leaf(self):
        locks = self.library / "packages" / ".locks"
        locks.mkdir(parents=True)
        outside = self.root / "outside-lock"
        self.create_directory_link(
            locks / "km4-unit-001-source.lock", outside
        )

        with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink|escape"):
            stage_source_package(**self.options())

        self.assertEqual(list(outside.iterdir()), [])

    def test_staging_rechecks_new_object_directory_before_writing(self):
        outside = self.root / "outside-object-prefix"
        original_ensure = source_library_module._ensure_directory_durable
        swapped = False

        def swap_after_creation(path):
            nonlocal swapped
            original_ensure(path)
            path = Path(path)
            if not swapped and path.parent.name == "originals":
                os.rmdir(path)
                self.create_directory_link(path, outside)
                swapped = True

        with patch(
            "scripts.visual_qc.source_library._ensure_directory_durable",
            side_effect=swap_after_creation,
        ):
            with self.assertRaisesRegex(IntakeValidationError, "reparse|symlink|escape"):
                stage_source_package(**self.options())

        self.assertTrue(swapped)
        self.assertEqual(list(outside.iterdir()), [])

    def test_stage_preserves_exact_bytes_and_creates_compatible_manifests(self):
        original_front = self.front.read_bytes()
        original_back = self.back.read_bytes()

        result = stage_source_package(**self.options())

        self.assertEqual(result["state"], "created")
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual(
            result["source_package_path"],
            (
                self.library
                / "packages"
                / "km4-unit-001-source"
                / "source-package.json"
            ).resolve(),
        )
        self.assertEqual(
            result["intake_manifest_path"],
            (
                self.library
                / "packages"
                / "km4-unit-001-source"
                / "km4-unit-001-batch.intake.json"
            ).resolve(),
        )
        validated_source = validate_source_package(
            result["source_package_path"], ROOT, self.library
        )
        validated_intake = validate_intake_batch(result["intake_manifest_path"], ROOT)
        self.assertEqual(len(validated_source["entries"]), 2)
        self.assertEqual(len(validated_intake["entries"]), 2)
        by_side = {entry["side_id"]: entry for entry in validated_source["entries"]}
        self.assertEqual(
            by_side["main_page_1"]["object_file"].read_bytes(), original_front
        )
        self.assertEqual(
            by_side["main_page_2"]["object_file"].read_bytes(), original_back
        )
        self.assertEqual(self.front.read_bytes(), original_front)
        self.assertEqual(self.back.read_bytes(), original_back)

    def test_identical_stage_is_idempotently_reused(self):
        created = stage_source_package(**self.options())
        first_source_bytes = created["source_package_path"].read_bytes()
        first_intake_bytes = created["intake_manifest_path"].read_bytes()

        reused = stage_source_package(**self.options())

        self.assertEqual(reused["state"], "reused")
        self.assertEqual(reused["source_package_path"].read_bytes(), first_source_bytes)
        self.assertEqual(reused["intake_manifest_path"].read_bytes(), first_intake_bytes)

    def test_existing_package_rejects_changed_content_or_metadata(self):
        created = stage_source_package(**self.options())
        committed = created["source_package_path"].read_bytes()

        changed = self.root / "changed-front.jpeg"
        changed.write_bytes(encode_image(".jpg", value=40))
        with self.assertRaisesRegex(IntakeValidationError, "package conflict"):
            stage_source_package(
                **self.options(
                    image_assignments=[
                        ("main_page_1", changed),
                        ("main_page_2", self.back),
                    ]
                )
            )
        with self.assertRaisesRegex(IntakeValidationError, "package conflict"):
            stage_source_package(
                **self.options(capture_stage="after_repair")
            )
        self.assertEqual(created["source_package_path"].read_bytes(), committed)

    def test_corrupted_existing_object_fails_closed(self):
        result = stage_source_package(**self.options())
        payload = json.loads(result["source_package_path"].read_text(encoding="utf-8"))
        object_file = self.library / payload["entries"][0]["object_path"]
        object_file.write_bytes(b"corrupted")

        with self.assertRaisesRegex(IntakeValidationError, "object integrity"):
            stage_source_package(**self.options())

    def test_conflicting_preexisting_object_is_not_replaced(self):
        payload = build_source_package(**self.options())
        object_file = self.library / payload["entries"][0]["object_path"]
        object_file.parent.mkdir(parents=True)
        object_file.write_bytes(b"PROTECTED")

        with self.assertRaisesRegex(IntakeValidationError, "object integrity"):
            stage_source_package(**self.options())

        self.assertEqual(object_file.read_bytes(), b"PROTECTED")
        self.assertFalse(
            (self.library / "packages" / payload["package_id"]).exists()
        )

    def test_intake_failure_does_not_publish_partial_package(self):
        with patch(
            "scripts.visual_qc.source_library.create_validated_intake_manifest",
            side_effect=IntakeValidationError("injected intake failure"),
        ):
            with self.assertRaisesRegex(IntakeValidationError, "injected intake failure"):
                stage_source_package(**self.options())

        self.assertFalse(
            (self.library / "packages" / "km4-unit-001-source").exists()
        )

    def test_proxy_inventory_update_revokes_existing_package_and_intake(self):
        result = stage_source_package(**self.options())
        payload = json.loads(result["source_package_path"].read_text(encoding="utf-8"))
        revoked_hash = payload["entries"][0]["sha256"]

        with patch(
            "scripts.visual_qc.source_library.known_proxy_hashes",
            return_value=frozenset({revoked_hash}),
        ):
            with self.assertRaisesRegex(IntakeValidationError, "known reference|revoked"):
                validate_source_package(
                    result["source_package_path"], ROOT, self.library
                )

        with patch(
            "scripts.visual_qc.intake.known_proxy_hashes",
            return_value=frozenset({revoked_hash}),
        ):
            with self.assertRaisesRegex(IntakeValidationError, "known reference|revoked"):
                validate_intake_batch(result["intake_manifest_path"], ROOT)

    def test_staging_flushes_object_and_package_directory_metadata(self):
        with patch(
            "scripts.visual_qc.source_library._fsync_directory",
            wraps=lambda path: None,
        ) as flush:
            stage_source_package(**self.options())

        flushed = {Path(call.args[0]).resolve() for call in flush.call_args_list}
        package_dir = (
            self.library / "packages" / "km4-unit-001-source"
        ).resolve()
        self.assertIn(package_dir, flushed)
        self.assertIn(package_dir.parent, flushed)
        self.assertIn(self.library.resolve(), flushed)
        self.assertIn((self.library / "objects").resolve(), flushed)
        self.assertIn((self.library / "objects" / "originals").resolve(), flushed)
        payload = build_source_package(**self.options())
        for entry in payload["entries"]:
            self.assertIn((self.library / entry["object_path"]).parent.resolve(), flushed)

    def test_package_directory_is_flushed_before_and_after_completion_marker(self):
        events = []

        def record_marker(path):
            path = Path(path)
            path.write_text("complete\n", encoding="ascii")
            events.append(("marker", path.resolve()))

        with patch(
            "scripts.visual_qc.source_library._fsync_directory",
            side_effect=lambda path: events.append(("flush", Path(path).resolve())),
        ), patch(
            "scripts.visual_qc.source_library._write_completion_marker",
            side_effect=record_marker,
        ):
            stage_source_package(**self.options())

        package_dir = (self.library / "packages" / "km4-unit-001-source").resolve()
        marker_index = events.index(("marker", package_dir / ".complete"))
        self.assertIn(("flush", package_dir), events[:marker_index])
        self.assertIn(("flush", package_dir), events[marker_index + 1 :])

    def test_proxy_inventory_fails_closed_for_missing_or_replaced_source(self):
        proxy = self.root / "proxy.jpg"
        proxy.write_bytes(b"approved-proxy")
        inventory = self.root / "knowledge-base" / "visual-qc-proxy-inventory-v1.json"
        inventory.parent.mkdir()
        inventory.write_text(
            json.dumps(
                {
                    "schema_version": "VISUAL-QC-PROXY-INVENTORY-V1",
                    "entries": [
                        {
                            "path": "proxy.jpg",
                            "sha256": hashlib.sha256(proxy.read_bytes()).hexdigest(),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with patch(
            "scripts.visual_qc.proxy_inventory._configured_proxy_paths",
            return_value={proxy},
        ):
            self.assertEqual(len(known_proxy_hashes(self.root)), 1)
            proxy.unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                known_proxy_hashes(self.root)
            proxy.write_bytes(b"replaced")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                known_proxy_hashes(self.root)

    def test_proxy_path_collection_keeps_declared_missing_sources(self):
        missing = self.root / "assets" / "missing-proxy.jpg"
        paths = set()

        _collect_proxy_paths(
            {
                "assets": {
                    "assets/missing-proxy.jpg": {"review_status": "approved"}
                }
            },
            self.root.resolve(),
            paths,
        )

        self.assertEqual(paths, {missing.resolve()})

    def test_proxy_path_collection_rejects_repository_escape(self):
        with self.assertRaisesRegex(ValueError, "escapes project root"):
            _collect_proxy_paths(
                {
                    "assets": {
                        "../outside-proxy.jpg": {"review_status": "approved"}
                    }
                },
                self.root.resolve(),
                set(),
            )


class VisualQcSourcePackageCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library = self.root / "library"
        self.front = self.root / "front.jpg"
        self.back = self.root / "back.png"
        self.front.write_bytes(encode_image(".jpg", value=150))
        self.back.write_bytes(encode_image(".png", value=90))
        self.script = ROOT / "scripts" / "stage_visual_qc_source_package.py"

    def tearDown(self):
        self.temp_dir.cleanup()

    def command(self, *extra):
        return [
            sys.executable,
            str(self.script),
            "--library-root",
            str(self.library),
            "--package-id",
            "km4-cli-source",
            "--batch-id",
            "km4-cli-batch",
            "--board-key",
            "km4-f151",
            "--capture-session-id",
            "km4-cli-unit",
            "--capture-stage",
            "before_repair",
            "--image",
            f"main_page_1={self.front}",
            "--image",
            f"main_page_2={self.back}",
            *extra,
        ]

    def run_cli(self, *extra):
        return subprocess.run(
            self.command(*extra),
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_direct_invocation_creates_then_reuses_the_package(self):
        confirmations = (
            "--confirm-milo-physical-source",
            "--confirm-capture-checklist",
        )
        created = self.run_cli(*confirmations)

        self.assertEqual(created.returncode, 0, created.stderr or created.stdout)
        created_payload = json.loads(created.stdout)
        self.assertEqual(created_payload["status"], "ok")
        self.assertEqual(created_payload["state"], "created")
        self.assertEqual(created_payload["package_id"], "km4-cli-source")
        self.assertEqual(created_payload["batch_id"], "km4-cli-batch")
        self.assertEqual(created_payload["entry_count"], 2)
        self.assertTrue(Path(created_payload["source_package"]).is_file())
        self.assertTrue(Path(created_payload["intake_manifest"]).is_file())

        reused = self.run_cli(*confirmations)
        self.assertEqual(reused.returncode, 0, reused.stderr or reused.stdout)
        self.assertEqual(json.loads(reused.stdout)["state"], "reused")

    def test_cli_requires_both_explicit_confirmations_without_writes(self):
        result = self.run_cli("--confirm-capture-checklist")

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "validation_failed")
        self.assertIn("Milo-supplied physical source", payload["message"])
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.library.exists())

    def test_parser_errors_are_machine_readable_and_do_not_create_library(self):
        cases = [
            [sys.executable, str(self.script)],
            [
                *self.command(
                    "--confirm-milo-physical-source",
                    "--confirm-capture-checklist",
                ),
                "--capture-stage",
                "invalid-stage",
            ],
        ]
        for command in cases:
            with self.subTest(command=command):
                result = subprocess.run(
                    command,
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(
                    json.loads(result.stdout)["status"], "validation_failed"
                )
                self.assertEqual(result.stderr, "")
                self.assertFalse(self.library.exists())

    def test_unexpected_catalog_json_error_is_still_machine_readable(self):
        from scripts import stage_visual_qc_source_package as command_module

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(
            command_module,
            "stage_source_package",
            side_effect=json.JSONDecodeError("broken catalog", "{", 1),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = command_module.main(
                self.command(
                    "--confirm-milo-physical-source",
                    "--confirm-capture-checklist",
                )[2:]
            )

        self.assertEqual(exit_code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "failed")
        self.assertIn("broken catalog", payload["message"])
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
