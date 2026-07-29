from __future__ import annotations

import copy
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib import request
from unittest.mock import patch

from scripts.visual_qc.repair_evidence_link_contract import canonical_json_bytes

from scripts import sync_visual_qc_repair_evidence_link as command


class SyncRepairEvidenceLinkCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.library = self.root / "library"
        self.manifest_path = (
            self.library
            / "repair-evidence-links"
            / "link-case005-f069-after"
            / "revisions"
            / "0001"
            / "repair-evidence-link.json"
        )
        self.manifest_path.parent.mkdir(parents=True)
        self.manifest = {
            "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-V1",
            "link_set_id": "link-case005-f069-after",
            "revision": 1,
            "repair_case_references": [
                {
                    "repair_case_reference_id": "case005-r1",
                    "repair_case_id": "case-005-bg6-f069",
                    "revision": 1,
                    "schema_version": "VISUAL-QC-REPAIR-CASE-SOURCE-V2",
                    "manifest_sha256": "a" * 64,
                    "board_key": "bg6h-f069",
                    "board_id": "BOARD-F069-MAIN-V1.2",
                }
            ],
            "board": {
                "board_key": "bg6h-f069",
                "board_id": "BOARD-F069-MAIN-V1.2",
            },
            "physical_evidence": [{"server_case_id": "server-main-page-2"}],
            "bindings": [
                {
                    "binding_id": "case005-main-page-2",
                    "association_status": "possibly_related",
                    "visibility_status": "not_assessed",
                }
            ],
        }
        self.manifest_path.write_bytes(canonical_json_bytes(self.manifest))
        self.credentials = self.root / "credentials.json"
        self.credentials.write_text(
            json.dumps(
                {
                    "username": "sync-user",
                    "password": "sync-secret",
                    "actor_id": "sync-owner",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def argv(self, *extra):
        return [
            str(self.manifest_path),
            "--library-root",
            str(self.library),
            "--api-base",
            "http://127.0.0.1:3020/api/v1/visual-qc",
            "--credential-file",
            str(self.credentials),
            "--allow-http-localhost",
            *extra,
        ]

    def response(self, *, state=None, health="active"):
        result = {
            "schema_version": "VISUAL-QC-REPAIR-EVIDENCE-LINK-DETAIL-V1",
            "link_set_id": self.manifest["link_set_id"],
            "revision": self.manifest["revision"],
            "manifest_sha256": command.canonical_sha256(self.manifest),
            "repair_case_id": "case-005-bg6-f069",
            "board": copy.deepcopy(self.manifest["board"]),
            "server_case_ids": ["server-main-page-2"],
            "counts": {
                "association": {
                    "related": 0,
                    "possibly_related": 1,
                    "not_related": 0,
                    "insufficient_evidence": 0,
                },
                "visibility": {
                    "not_assessed": 1,
                    "visible": 0,
                    "not_visible": 0,
                    "occluded": 0,
                },
                "source_fact_superseded": 0,
                "binding_superseded": 0,
            },
            "health": {"state": health, "reasons": []},
            "imported_at": "2026-07-29T10:00:00.000Z",
            "binding_states": [
                {
                    "binding_id": "case005-main-page-2",
                    "source_fact_superseded": False,
                    "replacement_fact_id": None,
                    "binding_superseded": False,
                    "replacement_binding_id": None,
                }
            ],
            "manifest": copy.deepcopy(self.manifest),
        }
        if state is not None:
            result["state"] = state
        return result

    def run_main(self, *extra):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(command.sys, "stdout", stdout), patch.object(
            command.sys, "stderr", stderr
        ):
            code = command.main(self.argv(*extra))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_validates_revision_before_exactly_one_post_and_sends_canonical_payload(self):
        sent = []

        def validate(path, *, project_root, library_root):
            self.assertEqual(path, self.manifest_path)
            self.assertEqual(library_root, self.library)
            return copy.deepcopy(self.manifest)

        def post(api_base, payload, *, actor_id, authorization):
            sent.append((api_base, payload, actor_id, authorization))
            return 201, self.response()

        with patch.object(
            command, "validate_repair_evidence_link_revision_on_disk", side_effect=validate
        ), patch.object(command, "_post_projection", side_effect=post):
            code, stdout, stderr = self.run_main()

        self.assertEqual(code, 0, stderr)
        self.assertEqual(stderr, "")
        self.assertEqual(len(sent), 1)
        api_base, payload, actor_id, authorization = sent[0]
        self.assertEqual(api_base, "http://127.0.0.1:3020/api/v1/visual-qc")
        self.assertEqual(actor_id, "sync-owner")
        self.assertTrue(authorization.startswith("Basic "))
        self.assertEqual(payload["manifest"], self.manifest)
        self.assertEqual(payload["manifest_sha256"], command.canonical_sha256(self.manifest))
        self.assertEqual(json.loads(stdout)["state"], "accepted")
        self.assertEqual(self.manifest_path.read_bytes(), canonical_json_bytes(self.manifest))

    def test_invalid_revision_prevents_network_access(self):
        with patch.object(
            command,
            "validate_repair_evidence_link_revision_on_disk",
            side_effect=command.SyncError("invalid_revision", "invalid"),
        ), patch.object(command, "_post_projection") as post:
            code, _stdout, _stderr = self.run_main()
        self.assertEqual(code, 2)
        post.assert_not_called()

    def test_manifest_changed_after_validation_prevents_network_access(self):
        def validate(*_args, **_kwargs):
            self.manifest_path.write_text('{"changed":true}', encoding="utf-8")
            return copy.deepcopy(self.manifest)

        with patch.object(
            command, "validate_repair_evidence_link_revision_on_disk", side_effect=validate
        ), patch.object(command, "_post_projection") as post:
            code, _stdout, _stderr = self.run_main()
        self.assertEqual(code, 2)
        post.assert_not_called()

    def test_local_actor_only_mode_requires_explicit_loopback_http(self):
        with patch.object(
            command, "validate_repair_evidence_link_revision_on_disk", return_value=copy.deepcopy(self.manifest)
        ), patch.object(command, "_post_projection", return_value=(200, self.response())) as post:
            local_argv = [
                str(self.manifest_path), "--library-root", str(self.library),
                "--api-base", "http://127.0.0.1:3020/api/v1/visual-qc",
                "--actor-id", "milo-visual-data-operator", "--allow-http-localhost",
            ]
            stdout = io.StringIO()
            with patch.object(command.sys, "stdout", stdout):
                code = command.main(local_argv)
        self.assertEqual(code, 0)
        self.assertEqual(post.call_args.kwargs["authorization"], None)
        self.assertEqual(json.loads(stdout.getvalue())["state"], "accepted")

        with patch.object(command, "_post_projection") as remote_post:
            code, _stdout, _stderr = self.run_main(
                "--api-base", "https://visual.example/api/v1/visual-qc",
                "--actor-id", "milo-visual-data-operator",
            )
        self.assertEqual(code, 2)
        remote_post.assert_not_called()

    def test_rejects_malformed_or_stale_server_receipt(self):
        missing_counts = self.response()
        del missing_counts["counts"]
        extra_health_field = self.response()
        extra_health_field["health"]["unexpected"] = True
        changed_manifest = self.response()
        changed_manifest["manifest"]["revision"] = 2
        for receipt in (
            {"state": "created"},
            self.response(health="stale"),
            missing_counts,
            extra_health_field,
            changed_manifest,
        ):
            with self.subTest(receipt=receipt), patch.object(
                command, "validate_repair_evidence_link_revision_on_disk", return_value=copy.deepcopy(self.manifest)
            ), patch.object(command, "_post_projection", return_value=(201, receipt)):
                code, _stdout, _stderr = self.run_main()
            self.assertEqual(code, 2)

    def test_real_server_replay_receipts_without_state_are_neutral_success(self):
        server_tests = importlib.import_module(
            "tests.test_visual_qc_repair_evidence_link_server"
        )
        probe = server_tests.VisualQcRepairEvidenceLinkApiTests(
            methodName="test_routes_require_reviewer_and_import_active_projection"
        )
        probe.setUp()
        self.addCleanup(probe.tearDown)
        first = probe.client.post(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=server_tests.HEADERS,
            json={
                "manifest": probe.manifest,
                "manifest_sha256": probe.manifest_sha256,
            },
        )
        replay = probe.client.post(
            "/api/v1/visual-qc/admin/repair-evidence-links",
            headers=server_tests.HEADERS,
            json={
                "manifest": probe.manifest,
                "manifest_sha256": probe.manifest_sha256,
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertNotIn("state", first.json())
        self.assertNotIn("state", replay.json())
        for response in (first, replay):
            receipt = command._validate_receipt(
                response.status_code,
                response.json(),
                probe.manifest,
                probe.manifest_sha256,
            )
            self.assertEqual(receipt["state"], "accepted")
            self.assertEqual(receipt["projection_state"], "active")

    def test_rejects_insecure_remote_and_credentialless_remote_before_network(self):
        with patch.object(command, "_post_projection") as post:
            code, _stdout, _stderr = self.run_main(
                "--api-base", "http://visual.example/api/v1/visual-qc"
            )
        self.assertEqual(code, 2)
        post.assert_not_called()

    def test_credentialless_remote_actor_is_rejected_by_transport_policy(self):
        with self.assertRaises(command.SyncError) as raised:
            command._transport_configuration(
                "https://visual.example/api/v1/visual-qc",
                credentials={"username": None, "password": None, "actor_id": None},
                actor_id="milo-visual-data-operator",
                allow_http_localhost=False,
            )
        self.assertEqual(raised.exception.code, "credentials_required")

    def test_post_uses_data_administrator_headers_and_never_follows_redirects(self):
        class Response:
            def getcode(self):
                return 201

            headers = {"Content-Type": "application/json"}

            def read(self, limit):
                self_outer.assertEqual(limit, command.MAX_RESPONSE_BYTES + 1)
                return canonical_json_bytes(self_outer.response())

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        self_outer = self
        captured = []

        def open_once(http_request, *, timeout):
            captured.append((http_request, timeout))
            return Response()

        with patch.object(command, "_open_no_redirect", side_effect=open_once):
            status, receipt = command._post_projection(
                "https://visual.example/api/v1/visual-qc",
                {
                    "manifest": self.manifest,
                    "manifest_sha256": command.canonical_sha256(self.manifest),
                },
                actor_id="sync-owner",
                authorization="Basic intentionally-hidden",
            )
        self.assertEqual(status, 201)
        self.assertEqual(receipt["health"]["state"], "active")
        self.assertEqual(len(captured), 1)
        sent, timeout = captured[0]
        self.assertEqual(timeout, 60)
        self.assertEqual(sent.get_method(), "POST")
        self.assertEqual(sent.headers["X-actor-id"], "sync-owner")
        self.assertEqual(sent.headers["X-actor-role"], "reviewer")
        self.assertEqual(sent.headers["Authorization"], "Basic intentionally-hidden")
        with self.assertRaises(command.SyncError) as redirected:
            command.RejectRedirectHandler().redirect_request(
                request.Request("https://source.example"), None, 302, "moved", {},
                "https://target.example",
            )
        self.assertEqual(redirected.exception.code, "redirect_rejected")

    def test_post_rejects_non_json_and_oversized_responses(self):
        class Response:
            def __init__(self, headers, content):
                self.headers = headers
                self.content = content

            def getcode(self):
                return 201

            def read(self, _limit):
                return self.content

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        payload = {"manifest": self.manifest, "manifest_sha256": command.canonical_sha256(self.manifest)}
        for response, expected_code in (
            (Response({"Content-Type": "text/plain"}, b"no"), "invalid_content_type"),
            (
                Response(
                    {"Content-Type": "application/json", "Content-Length": str(command.MAX_RESPONSE_BYTES + 1)},
                    b"{}",
                ),
                "response_too_large",
            ),
        ):
            with self.subTest(expected_code=expected_code), patch.object(
                command, "_open_no_redirect", return_value=response
            ):
                with self.assertRaises(command.SyncError) as raised:
                    command._post_projection(
                        "https://visual.example/api/v1/visual-qc", payload,
                        actor_id="sync-owner", authorization=None,
                    )
            self.assertEqual(raised.exception.code, expected_code)

        with patch.object(command, "_post_projection") as post:
            code, _stdout, _stderr = self.run_main(
                "--api-base", "https://visual.example/api/v1/visual-qc",
                "--credential-file", str(self.root / "missing.json"),
                "--actor-id", "milo-visual-data-operator",
            )
        self.assertEqual(code, 2)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
