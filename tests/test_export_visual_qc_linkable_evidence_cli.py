from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import importlib
import io
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
import unittest
from unittest import mock
from urllib import error

from tests.test_visual_qc_repair_evidence_export import server_case


EXPECTED_MAX_SERVER_CASE_RESPONSE_BYTES = 1024 * 1024


try:
    cli = importlib.import_module(
        "scripts.export_visual_qc_linkable_evidence"
    )
except ModuleNotFoundError:
    cli = None


class FakeResponse:
    def __init__(
        self,
        payload,
        *,
        status=200,
        content_type="application/json; charset=utf-8",
        content_length=None,
    ):
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.body = (
            payload
            if isinstance(payload, bytes)
            else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.read_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        self.read_calls.append(size)
        return self.body if size is None or size < 0 else self.body[:size]

    def getcode(self):
        return self.status


class CliAvailabilityTests(unittest.TestCase):
    def test_cli_module_exists(self):
        self.assertIsNotNone(cli)


@unittest.skipUnless(cli is not None, "CLI module not implemented")
class ExportVisualQcLinkableEvidenceCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="visual-qc-evidence-export-"
        )
        self.root = Path(self.temporary.name)
        self.output = self.root / "nested" / "evidence.json"

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, arguments, *, response=None, environment=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        urlopen = mock.Mock(return_value=response or FakeResponse(server_case()))
        with mock.patch.dict(os.environ, environment or {}, clear=True):
            with mock.patch(
                "scripts.export_visual_qc_linkable_evidence._open_no_redirect",
                urlopen,
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = cli.main(arguments)
        return status, stdout.getvalue(), stderr.getvalue(), urlopen

    def local_arguments(self):
        return [
            "--api-base",
            "http://127.0.0.1:3020/api/v1/visual-qc",
            "--actor-id",
            "milo-visual-data-operator",
            "--case-id",
            "vqc-case-005-page-2",
            "--physical-evidence-id",
            "physical-case005-page-2",
            "--output",
            str(self.output),
            "--allow-http-localhost",
        ]

    def assertSafeFailure(self, status, stdout, stderr, *secrets):
        self.assertNotEqual(status, 0)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertIn("code", payload)
        self.assertIn("message", payload)
        for secret in secrets:
            self.assertNotIn(secret, stderr)
        self.assertNotIn(str(self.root), stderr)
        self.assertNotIn("Traceback", stderr)

    def replace_directory_with_link(self, directory, target):
        original = directory.with_name(f"{directory.name}-original")
        directory.rename(original)
        if os.name == "nt":
            subprocess.run(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(directory),
                    str(target),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            directory.symlink_to(target, target_is_directory=True)
        return original

    def restore_replaced_directory(self, directory, original):
        if directory.exists() or directory.is_symlink():
            if os.name == "nt":
                os.rmdir(directory)
            else:
                directory.unlink()
        original.rename(directory)

    def test_localhost_actor_only_exports_once_with_get_and_headers(self):
        status, stdout, stderr, urlopen = self.run_cli(self.local_arguments())

        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        receipt = json.loads(stdout)
        snapshot = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(receipt["case_id"], "vqc-case-005-page-2")
        self.assertEqual(
            receipt["physical_evidence_snapshot_sha256"],
            snapshot["physical_evidence_snapshot_sha256"],
        )
        self.assertEqual(receipt["output"], str(self.output))
        self.assertEqual(self.output.read_bytes()[-1:], b"}")
        self.assertEqual(urlopen.call_count, 1)
        sent = urlopen.call_args.args[0]
        self.assertEqual(sent.method, "GET")
        self.assertIsNone(sent.data)
        self.assertEqual(sent.headers["Accept"], "application/json")
        self.assertEqual(
            sent.headers["X-actor-id"], "milo-visual-data-operator"
        )
        self.assertEqual(sent.headers["X-actor-role"], "reviewer")
        self.assertNotIn("Authorization", sent.headers)

    def test_https_uses_credentials_and_actor_headers(self):
        credential = self.root / "credentials.json"
        credential.write_text(
            json.dumps(
                {
                    "username": "api-user",
                    "password": "secret-password",
                    "actor_id": "credential-actor",
                }
            ),
            encoding="utf-8",
        )
        arguments = [
            "--api-base",
            "https://example.invalid/api/v1/visual-qc/",
            "--credential-file",
            str(credential),
            "--case-id",
            "vqc-case-005-page-2",
            "--physical-evidence-id",
            "physical-case005-page-2",
            "--output",
            str(self.output),
        ]
        status, stdout, stderr, urlopen = self.run_cli(arguments)

        self.assertEqual(status, 0, stderr)
        self.assertNotEqual(stdout, "")
        sent = urlopen.call_args.args[0]
        self.assertEqual(sent.method, "GET")
        self.assertEqual(sent.headers["X-actor-id"], "credential-actor")
        self.assertEqual(sent.headers["X-actor-role"], "reviewer")
        self.assertTrue(sent.headers["Authorization"].startswith("Basic "))
        self.assertNotIn("api-user", stdout)
        self.assertNotIn("secret-password", stdout)
        self.assertNotIn("Authorization", stdout)

    def test_environment_supplies_api_base_and_credentials(self):
        arguments = [
            "--case-id",
            "vqc-case-005-page-2",
            "--physical-evidence-id",
            "physical-case005-page-2",
            "--output",
            str(self.output),
        ]
        status, _stdout, stderr, urlopen = self.run_cli(
            arguments,
            environment={
                "VISUAL_QC_API_BASE": "https://example.invalid/api/v1/visual-qc",
                "VISUAL_QC_API_USERNAME": "env-user",
                "VISUAL_QC_API_PASSWORD": "env-password",
                "VISUAL_QC_API_ACTOR_ID": "env-actor",
            },
        )
        self.assertEqual(status, 0, stderr)
        self.assertEqual(
            urlopen.call_args.args[0].headers["X-actor-id"], "env-actor"
        )

    def test_remote_credentialless_and_unsafe_urls_are_rejected_before_get(self):
        urls = (
            "https://example.invalid/api/v1/visual-qc",
            "http://example.invalid/api/v1/visual-qc",
            "ftp://example.invalid/api",
            "https:///missing-host",
            "https://user:password@example.invalid/api",
            "https://example.invalid/api#fragment",
            "http://127.0.0.1:3020/api/v1/visual-qc",
        )
        for index, api_base in enumerate(urls):
            output = self.root / f"rejected-{index}.json"
            arguments = [
                "--api-base",
                api_base,
                "--actor-id",
                "milo-visual-data-operator",
                "--case-id",
                "vqc-case-005-page-2",
                "--physical-evidence-id",
                "physical-case005-page-2",
                "--output",
                str(output),
            ]
            with self.subTest(api_base=api_base):
                status, stdout, stderr, urlopen = self.run_cli(arguments)
                self.assertSafeFailure(
                    status, stdout, stderr, "user", "password"
                )
                urlopen.assert_not_called()
                self.assertFalse(output.exists())

    def test_rejects_unsafe_actor_identity_before_get(self):
        arguments = self.local_arguments()
        arguments[arguments.index("milo-visual-data-operator")] = (
            "actor\r\nAuthorization: Basic leaked"
        )
        status, stdout, stderr, urlopen = self.run_cli(arguments)
        self.assertSafeFailure(status, stdout, stderr, "Authorization", "leaked")
        self.assertEqual(json.loads(stderr)["code"], "invalid_actor_id")
        urlopen.assert_not_called()

    def test_percent_encodes_case_id_and_never_uses_mutating_method(self):
        payload = server_case()
        payload["case_id"] = "case/with spaces"
        payload["job"]["case_id"] = "case/with spaces"
        payload["server_registration_review"]["case_id"] = "case/with spaces"
        arguments = self.local_arguments()
        arguments[arguments.index("vqc-case-005-page-2")] = "case/with spaces"
        status, stdout, stderr, urlopen = self.run_cli(
            arguments, response=FakeResponse(payload)
        )
        self.assertSafeFailure(status, stdout, stderr)
        sent = urlopen.call_args.args[0]
        self.assertTrue(sent.full_url.endswith("/admin/cases/case%2Fwith%20spaces"))
        self.assertEqual(sent.method, "GET")

    def test_rejects_self_consistent_response_for_a_different_case(self):
        payload = server_case()
        payload["case_id"] = "vqc-different-case"
        payload["job"]["case_id"] = "vqc-different-case"
        payload["server_registration_review"]["case_id"] = (
            "vqc-different-case"
        )

        status, stdout, stderr, urlopen = self.run_cli(
            self.local_arguments(),
            response=FakeResponse(payload),
        )

        self.assertSafeFailure(status, stdout, stderr)
        self.assertEqual(json.loads(stderr)["code"], "identity_mismatch")
        self.assertEqual(urlopen.call_count, 1)
        self.assertFalse(self.output.exists())

    def test_rejects_redirect_without_requesting_or_disclosing_to_target(self):
        source_requests = []
        target_requests = []
        target_payload = json.dumps(
            server_case(), separators=(",", ":")
        ).encode("utf-8")

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(handler):
                target_requests.append(
                    {
                        "path": handler.path,
                        "authorization": handler.headers.get("Authorization"),
                        "actor_id": handler.headers.get("X-Actor-Id"),
                    }
                )
                handler.send_response(200)
                handler.send_header("Content-Type", "application/json")
                handler.send_header("Content-Length", str(len(target_payload)))
                handler.end_headers()
                handler.wfile.write(target_payload)

            def log_message(self, *_args):
                pass

        target_server = HTTPServer(("127.0.0.1", 0), TargetHandler)

        class SourceHandler(BaseHTTPRequestHandler):
            def do_GET(handler):
                source_requests.append(
                    {
                        "path": handler.path,
                        "authorization": handler.headers.get("Authorization"),
                        "actor_id": handler.headers.get("X-Actor-Id"),
                    }
                )
                handler.send_response(302)
                handler.send_header(
                    "Location",
                    (
                        f"http://127.0.0.1:{target_server.server_port}"
                        "/redirected"
                    ),
                )
                handler.end_headers()

            def log_message(self, *_args):
                pass

        source_server = HTTPServer(("127.0.0.1", 0), SourceHandler)
        target_thread = Thread(
            target=target_server.serve_forever, daemon=True
        )
        source_thread = Thread(
            target=source_server.serve_forever, daemon=True
        )
        target_thread.start()
        source_thread.start()
        credential = self.root / "redirect-credentials.json"
        credential.write_text(
            json.dumps(
                {
                    "username": "redirect-user",
                    "password": "redirect-secret",
                    "actor_id": "redirect-actor",
                }
            ),
            encoding="utf-8",
        )
        arguments = [
            "--api-base",
            (
                f"http://127.0.0.1:{source_server.server_port}"
                "/api/v1/visual-qc"
            ),
            "--credential-file",
            str(credential),
            "--case-id",
            "vqc-case-005-page-2",
            "--physical-evidence-id",
            "physical-case005-page-2",
            "--output",
            str(self.output),
            "--allow-http-localhost",
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = cli.main(arguments)
        finally:
            source_server.shutdown()
            target_server.shutdown()
            source_server.server_close()
            target_server.server_close()
            source_thread.join(timeout=5)
            target_thread.join(timeout=5)

        self.assertSafeFailure(
            status,
            stdout.getvalue(),
            stderr.getvalue(),
            "redirect-user",
            "redirect-secret",
        )
        self.assertEqual(
            json.loads(stderr.getvalue())["code"],
            "redirect_rejected",
        )
        self.assertEqual(len(source_requests), 1)
        self.assertTrue(source_requests[0]["authorization"].startswith("Basic "))
        self.assertEqual(source_requests[0]["actor_id"], "redirect-actor")
        self.assertEqual(target_requests, [])
        self.assertFalse(self.output.exists())

    def test_no_overwrite_and_credential_output_collision(self):
        self.output.parent.mkdir()
        self.output.write_text("existing", encoding="utf-8")
        status, stdout, stderr, urlopen = self.run_cli(self.local_arguments())
        self.assertSafeFailure(status, stdout, stderr)
        urlopen.assert_not_called()
        self.assertEqual(self.output.read_text(encoding="utf-8"), "existing")

        credential = self.root / "same.json"
        credential.write_text(
            '{"username":"u","password":"secret","actor_id":"a"}',
            encoding="utf-8",
        )
        arguments = [
            "--api-base",
            "https://example.invalid/api",
            "--credential-file",
            str(credential),
            "--case-id",
            "vqc-case-005-page-2",
            "--physical-evidence-id",
            "physical-case005-page-2",
            "--output",
            str(credential),
        ]
        status, stdout, stderr, urlopen = self.run_cli(arguments)
        self.assertSafeFailure(status, stdout, stderr, "secret")
        urlopen.assert_not_called()

    def test_malformed_response_and_http_errors_are_typed_and_leave_no_output(self):
        responses = (
            FakeResponse(b"not-json"),
            FakeResponse([]),
            FakeResponse(server_case(), content_type="text/html"),
            FakeResponse(
                {
                    **server_case(),
                    "schema_version": "VISUAL-QC-SERVER-CASE-V2",
                }
            ),
        )
        for index, response in enumerate(responses):
            self.output = self.root / f"malformed-{index}.json"
            with self.subTest(index=index):
                status, stdout, stderr, _urlopen = self.run_cli(
                    self.local_arguments(), response=response
                )
                self.assertSafeFailure(status, stdout, stderr)
                self.assertFalse(self.output.exists())

        for status_code in (401, 403, 404, 500):
            self.output = self.root / f"http-{status_code}.json"
            http_error = error.HTTPError(
                "https://example.invalid/private",
                status_code,
                "secret remote reason",
                {},
                io.BytesIO(b'{"detail":"credential secret"}'),
            )
            with mock.patch(
                "scripts.export_visual_qc_linkable_evidence._open_no_redirect",
                side_effect=http_error,
            ):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = cli.main(self.local_arguments())
            self.assertSafeFailure(
                result,
                stdout.getvalue(),
                stderr.getvalue(),
                "credential",
                "secret",
                "example.invalid",
            )
            self.assertFalse(self.output.exists())

    def test_rejects_non_json_content_type_before_reading_body(self):
        response = FakeResponse(server_case(), content_type="text/html")
        status, stdout, stderr, _urlopen = self.run_cli(
            self.local_arguments(),
            response=response,
        )
        self.assertSafeFailure(status, stdout, stderr)
        self.assertEqual(json.loads(stderr)["code"], "invalid_content_type")
        self.assertEqual(response.read_calls, [])
        self.assertFalse(self.output.exists())

    def test_rejects_oversized_declared_length_without_reading_body(self):
        response = FakeResponse(
            server_case(),
            content_length=EXPECTED_MAX_SERVER_CASE_RESPONSE_BYTES + 1,
        )
        status, stdout, stderr, _urlopen = self.run_cli(
            self.local_arguments(),
            response=response,
        )
        self.assertSafeFailure(status, stdout, stderr)
        self.assertEqual(json.loads(stderr)["code"], "response_too_large")
        self.assertEqual(response.read_calls, [])
        self.assertFalse(self.output.exists())

    def test_rejects_oversized_response_without_content_length(self):
        response = FakeResponse(
            b"x" * (EXPECTED_MAX_SERVER_CASE_RESPONSE_BYTES + 1)
        )
        status, stdout, stderr, _urlopen = self.run_cli(
            self.local_arguments(),
            response=response,
        )
        self.assertSafeFailure(status, stdout, stderr)
        self.assertEqual(json.loads(stderr)["code"], "response_too_large")
        self.assertEqual(
            response.read_calls,
            [EXPECTED_MAX_SERVER_CASE_RESPONSE_BYTES + 1],
        )
        self.assertFalse(self.output.exists())

    def test_atomic_failure_cleans_temporary_file(self):
        with mock.patch(
            "scripts.export_visual_qc_linkable_evidence.os.link",
            side_effect=OSError("private publication path failed"),
        ):
            status, stdout, stderr, _urlopen = self.run_cli(
                self.local_arguments()
            )
        self.assertSafeFailure(
            status, stdout, stderr, "private publication path"
        )
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.glob(f".{self.output.name}.*")), [])

    def test_directory_sync_failure_removes_this_run_published_output(self):
        with mock.patch(
            "scripts.export_visual_qc_linkable_evidence._fsync_directory",
            side_effect=OSError("private directory sync failed"),
        ):
            status, stdout, stderr, _urlopen = self.run_cli(
                self.local_arguments()
            )
        self.assertSafeFailure(
            status, stdout, stderr, "private directory sync failed"
        )
        self.assertFalse(self.output.exists())
        self.assertEqual(
            list(self.output.parent.glob(f".{self.output.name}.*")),
            [],
        )

    def test_parent_replaced_during_fetch_cannot_publish_outside_tree(self):
        self.output.parent.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        original = None
        replacement_prevented = False

        class SwappingResponse(FakeResponse):
            def read(response, size=-1):
                nonlocal original, replacement_prevented
                try:
                    original = self.replace_directory_with_link(
                        self.output.parent,
                        outside,
                    )
                except OSError:
                    replacement_prevented = True
                return super().read(size)

        response = SwappingResponse(server_case())
        try:
            status, stdout, stderr, _urlopen = self.run_cli(
                self.local_arguments(),
                response=response,
            )
            outside_written = (outside / self.output.name).exists()
        finally:
            if original is not None:
                self.restore_replaced_directory(
                    self.output.parent,
                    original,
                )

        if os.name == "nt":
            self.assertTrue(replacement_prevented)
            self.assertEqual(status, 0, stderr)
            self.assertEqual(stderr, "")
            self.assertNotEqual(stdout, "")
            self.assertTrue(self.output.exists())
        else:
            self.assertSafeFailure(status, stdout, stderr)
            self.assertEqual(json.loads(stderr)["code"], "unsafe_output")
        self.assertFalse(outside_written)

    def test_directory_lock_prevents_replacement_at_mkstemp(self):
        outside = self.root / "mkstemp-outside"
        outside.mkdir()
        displaced = None
        replacement_prevented = False
        original_create_temporary = cli._create_temporary_output

        def replacing_temporary(binding):
            nonlocal displaced, replacement_prevented
            try:
                displaced = self.replace_directory_with_link(
                    self.output.parent,
                    outside,
                )
            except OSError:
                replacement_prevented = True
            return original_create_temporary(binding)

        try:
            with mock.patch(
                (
                    "scripts.export_visual_qc_linkable_evidence"
                    "._create_temporary_output"
                ),
                side_effect=replacing_temporary,
            ):
                status, stdout, stderr, _urlopen = self.run_cli(
                    self.local_arguments()
                )
            outside_files = list(outside.iterdir())
        finally:
            if displaced is not None:
                self.restore_replaced_directory(
                    self.output.parent,
                    displaced,
                )

        if os.name == "nt":
            self.assertTrue(replacement_prevented)
            self.assertEqual(status, 0, stderr)
            self.assertNotEqual(stdout, "")
            self.assertTrue(self.output.exists())
        else:
            self.assertNotEqual(status, 0)
            self.assertFalse(self.output.exists())
        self.assertEqual(outside_files, [])

    def test_directory_lock_prevents_replacement_immediately_after_link(self):
        outside = self.root / "post-link-outside"
        outside.mkdir()
        displaced = None
        replacement_prevented = False
        displaced_output_existed = False
        original_link = os.link

        def replacing_link(source, destination, *args, **kwargs):
            nonlocal displaced, replacement_prevented
            original_link(source, destination, *args, **kwargs)
            try:
                displaced = self.replace_directory_with_link(
                    self.output.parent,
                    outside,
                )
            except OSError:
                replacement_prevented = True

        try:
            with mock.patch(
                "scripts.export_visual_qc_linkable_evidence.os.link",
                side_effect=replacing_link,
            ):
                status, stdout, stderr, _urlopen = self.run_cli(
                    self.local_arguments()
                )
            if displaced is not None:
                displaced_output_existed = (
                    displaced / self.output.name
                ).exists()
            outside_files = list(outside.iterdir())
        finally:
            if displaced is not None:
                self.restore_replaced_directory(
                    self.output.parent,
                    displaced,
                )

        if os.name == "nt":
            self.assertTrue(replacement_prevented)
            self.assertEqual(status, 0, stderr)
            self.assertNotEqual(stdout, "")
            self.assertTrue(self.output.exists())
        else:
            self.assertNotEqual(status, 0)
            self.assertFalse(self.output.exists())
        self.assertFalse(displaced_output_existed)
        self.assertEqual(outside_files, [])

    def test_rejects_output_symlink_and_linked_parent_when_supported(self):
        outside = self.root / "outside"
        outside.mkdir()
        target = outside / "target.json"
        target.write_text("outside", encoding="utf-8")
        linked_output = self.root / "linked-output.json"
        linked_parent = self.root / "linked-parent"
        try:
            linked_output.symlink_to(target)
            linked_parent.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available")

        for output in (linked_output, linked_parent / "new.json"):
            arguments = self.local_arguments()
            arguments[arguments.index(str(self.output))] = str(output)
            with self.subTest(output=output):
                status, stdout, stderr, urlopen = self.run_cli(arguments)
                self.assertSafeFailure(status, stdout, stderr)
                urlopen.assert_not_called()
        self.assertEqual(target.read_text(encoding="utf-8"), "outside")

    def test_rejects_mocked_reparse_parent_before_get(self):
        with mock.patch(
            "scripts.export_visual_qc_linkable_evidence._is_reparse_or_symlink",
            return_value=True,
        ):
            status, stdout, stderr, urlopen = self.run_cli(
                self.local_arguments()
            )
        self.assertSafeFailure(status, stdout, stderr)
        self.assertEqual(json.loads(stderr)["code"], "unsafe_output")
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
