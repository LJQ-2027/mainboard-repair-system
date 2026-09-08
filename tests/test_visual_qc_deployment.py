import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REPAIR_EVIDENCE_RUNTIME_PATHS = (
    "assets/visual-qc-workbench/app.js",
    "assets/visual-qc-workbench/index.html",
    "assets/visual-qc-workbench/repair-evidence-links.js",
    "assets/visual-qc-workbench/styles.css",
    "assets/visual-qc-workbench/visual-qc-server-client.js",
    "knowledge-base/visual-qc-linkable-physical-evidence-v1-schema.json",
    "knowledge-base/visual-qc-repair-evidence-link-v1-schema.json",
    "knowledge-base/visual-qc-repair-evidence-link-list-v1-schema.json",
    "knowledge-base/visual-qc-repair-evidence-link-detail-v1-schema.json",
    "scripts/export_visual_qc_linkable_evidence.py",
    "scripts/stage_visual_qc_repair_evidence_link.py",
    "scripts/sync_visual_qc_repair_evidence_link.py",
    "scripts/visual_qc/repair_evidence_engineering.py",
    "scripts/visual_qc/repair_evidence_export.py",
    "scripts/visual_qc/repair_evidence_link_contract.py",
    "scripts/visual_qc/repair_evidence_link_library.py",
    "scripts/visual_qc/server/api.py",
    "scripts/visual_qc/server/service.py",
    "scripts/visual_qc/server/store.py",
    "scripts/visual_qc/upgrade_preflight.py",
)


class VisualQcDeploymentContractTests(unittest.TestCase):
    def test_runtime_archive_manifest_is_bounded_and_contains_required_services(self):
        manifest_path = ROOT / "deploy" / "visual-qc-runtime-files.txt"
        self.assertTrue(manifest_path.is_file())
        entries = [
            line.strip()
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(len(entries), len(set(entries)))
        for entry in entries:
            self.assertTrue((ROOT / entry).exists(), entry)
        for required in (
            "deploy/visual-qc-runtime-files.txt",
            "ai_proxy_server.py",
            "visual_qc_server.py",
            "ecosystem.config.js",
            "requirements-visual-qc.txt",
            "mainboard_repair_system_v7.4_updated.html",
            "assets",
            "data",
            "knowledge-base",
            "scripts/visual_qc",
            "scripts/audit_visual_qc_upgrade.py",
            "scripts/build_visual_qc_deployment_manifest.py",
            "scripts/import_visual_qc_batch.py",
            "scripts/validate_visual_qc_dataset.py",
            "scripts/maintain_visual_qc_server.py",
        ):
            self.assertIn(required, entries)
        for excluded in ("source-materials", "tests", "docs", "output", "reports"):
            self.assertFalse(
                any(entry == excluded or entry.startswith(f"{excluded}/") for entry in entries),
                excluded,
            )

    def test_repair_evidence_link_runtime_boundary_is_explicit(self):
        manifest_path = ROOT / "deploy" / "visual-qc-runtime-files.txt"
        entries = {
            line.strip()
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        for required in REPAIR_EVIDENCE_RUNTIME_PATHS:
            self.assertIn(required, entries)

    def test_nginx_template_exposes_technician_app_but_protects_visual_qc(self):
        template = (
            ROOT / "deploy" / "nginx" / "mb-repair-beta.locations.conf"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(template.count("auth_basic "), 2)
        self.assertIn("auth_basic_user_file /etc/nginx/.htpasswd-mb-repair-beta;", template)
        self.assertIn(
            "location ^~ /mb-repair-beta/assets/visual-qc-workbench/ {",
            template,
        )
        self.assertIn("proxy_pass http://127.0.0.1:3020/api/v1/visual-qc/;", template)
        self.assertIn("proxy_set_header X-Actor-Id $remote_user;", template)
        self.assertIn(
            "proxy_set_header X-Actor-Role $mb_repair_actor_role;",
            template,
        )
        self.assertIn('proxy_set_header Authorization "";', template)
        self.assertIn("client_max_body_size 20m;", template)
        self.assertIn("proxy_pass http://127.0.0.1:3010/;", template)
        self.assertIn(
            "return 302 /mb-repair-beta/assets/technician-pilot/;",
            template,
        )

        public_location = template.split("location /mb-repair-beta/ {", 1)[1]
        self.assertNotIn('auth_basic "Mainboard Repair Pilot";', public_location)
        self.assertNotIn("auth_basic_user_file", public_location)
        self.assertIn("auth_basic off;", public_location)

    def test_nginx_role_map_fails_closed_to_technician(self):
        role_map = (
            ROOT / "deploy" / "nginx" / "mb-repair-beta-role-map.conf"
        ).read_text(encoding="utf-8")

        self.assertIn("map $remote_user $mb_repair_actor_role", role_map)
        self.assertIn("default technician;", role_map)
        self.assertIn(
            "include /etc/nginx/mb-repair-beta-reviewers.map;",
            role_map,
        )

    def test_deploy_script_has_backup_validation_smoke_and_rollback_gates(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        for required in (
            "git archive",
            "visual-qc-runtime-files.txt",
            "$runtimePaths",
            "$commit -- @runtimePaths",
            "set -o pipefail",
            "base64 -d | bash",
            "requirements-visual-qc.txt",
            "venv-visual-qc",
            "python3-venv",
            "nginx -t",
            "pm2 save",
            "VISUAL-QC-SERVER-HEALTH-V2",
            "rollback",
            ".htpasswd-mb-repair-beta",
            "mb-repair-beta-reviewers.map",
            "QC_EXISTED",
            "visual-qc-__COMMIT_SHORT__",
            "DEPLOY_LOCK",
            "VENV_LEGACY_MOVED",
            "sqlite3",
            "chmod 0400",
            "rm -f \"$INPUT_DIR/.htpasswd-mb-repair-beta\"",
            "finally",
            "Authorization: Basic $authorization",
            "__REVIEWER_AUTH__",
            "wait_for_gateway_identity",
            "wait_for_public_technician_entry",
            '"__TECH_AUTH__" "__TECH_USER__" "technician"',
            '"__REVIEWER_AUTH__" "__REVIEWER_USER__" "reviewer"',
            "/tmp/mb-repair-public-technician-index.html",
            '"/api/v1/visual-qc/identity"',
            '"/assets/visual-qc-workbench/"',
            "RetainVisualQcVenvs",
            "RetainRollbackPackages",
            "RetentionDryRun",
            "run_deployment_retention",
            "retention_candidate bytes=",
            "retention_keep active_venv",
            "retention_keep previous_venv",
            "retention_keep rollback",
            "find \"$REMOTE_DIR/venvs\"",
            "find \"$REMOTE_DIR/rollback\"",
            "-printf '%T@ %p\\n'",
        ):
            self.assertIn(required, script)

    def test_deploy_script_rehearses_snapshot_before_application_switch(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        for required in (
            "audit_visual_qc_upgrade.py",
            "upgrade-preflight.json",
            "--source-database",
            '"$ROLLBACK_DIR/visual-qc.sqlite3"',
            "--source-data-root",
            '"$DATA_DIR"',
            "--source-app-root",
            '"$APP_DIR"',
            "--target-version",
            '"__COMMIT_FULL__"',
            "--target-archive-sha256",
            '"__ARCHIVE_SHA256__"',
            "--target-archive-bytes",
            '"__ARCHIVE_BYTES__"',
            "--target-runtime-manifest-sha256",
            '"__RUNTIME_MANIFEST_SHA256__"',
            '"$INPUT_DIR/deployment_verifier.py" report',
            "--schema",
            "--snapshot",
            "--runtime-path-count",
        ):
            self.assertIn(required, script)

        backup_ready = script.index("DATABASE_SNAPSHOT_READY=1")
        rehearsal = script.index("audit_visual_qc_upgrade.py")
        report_verification = script.index(
            '"$INPUT_DIR/deployment_verifier.py" report'
        )
        application_switch = script.index('mv "$APP_DIR" "$ROLLBACK_DIR/app"')
        self.assertLess(backup_ready, rehearsal)
        self.assertLess(rehearsal, report_verification)
        self.assertLess(report_verification, application_switch)

    def test_deploy_script_builds_and_uploads_full_identity_manifest(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn('$commit = (git rev-parse HEAD).Trim()', script)
        self.assertNotIn("git rev-parse --short HEAD", script)
        self.assertIn("$shortCommit = $commit.Substring(0, 12)", script)
        self.assertIn('git cat-file -e "${commit}:$runtimePath"', script)
        self.assertIn(
            "git archive --format=tar.gz -o $artifact $commit -- @runtimePaths",
            script,
        )
        self.assertIn("build_visual_qc_deployment_manifest.py", script)
        self.assertIn("deployment-manifest.json", script)
        self.assertIn("$deploymentManifest", script)
        self.assertIn(
            '"${target}:$remoteInputDir/deployment-manifest.json"',
            script,
        )

    def test_each_deployment_uses_a_unique_private_input_directory(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("[Guid]::NewGuid().ToString('N')", script)
        self.assertIn('$remoteInputDir = "$RemoteDir/deploy-input/$uploadId"', script)
        self.assertIn('INPUT_DIR="__INPUT_DIR__"', script)
        self.assertIn("__INPUT_DIR__", script)
        self.assertIn("chmod 0400 '$remoteInputDir'/*", script)
        self.assertIn("chmod 0500 '$remoteInputDir'", script)
        self.assertIn("rm -rf '$remoteInputDir'", script)

    def test_deployment_retention_keeps_runtime_paths_and_supports_dry_run(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        for required in (
            "RetainVisualQcVenvs must be at least 2",
            "RetainRollbackPackages must be at least 2",
            "RETENTION_DRY_RUN=\"__RETENTION_DRY_RUN__\"",
            "RETAIN_VISUAL_QC_VENVS=\"__RETAIN_VISUAL_QC_VENVS__\"",
            "RETAIN_ROLLBACK_PACKAGES=\"__RETAIN_ROLLBACK_PACKAGES__\"",
            "assert_retention_path",
            'case "$path" in',
            '"$REMOTE_DIR/deploy-input/"*',
            '"$REMOTE_DIR/venvs/visual-qc-"*',
            '"$REMOTE_DIR/rollback/"*)',
            "Refusing retention path required by runtime",
            'if [ "$RETENTION_DRY_RUN" = "1" ]; then',
            "Deployment retention dry-run complete; no files removed.",
            "Deployment retention cleanup failed after successful smoke",
        ):
            self.assertIn(required, script)

        smoke = script.index("wait_for_public_technician_entry")
        retention = script.index("if ! run_deployment_retention")
        self.assertLess(smoke, retention)

    def test_remote_archive_identity_is_verified_before_extraction(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")
        verifier = (
            ROOT / "scripts" / "visual_qc" / "deployment_verifier.py"
        ).read_text(encoding="utf-8")

        for required in (
            "__COMMIT_FULL__",
            "__ARCHIVE_SHA256__",
            "__ARCHIVE_BYTES__",
            "__RUNTIME_MANIFEST_SHA256__",
            "__RUNTIME_PATH_COUNT__",
            "deployment_verifier.py",
            "deployment_manifest.py",
            " inputs ",
        ):
            self.assertIn(required, script)
        for required in (
            "VISUAL-QC-DEPLOYMENT-MANIFEST-V1",
            "Runtime archive SHA-256 mismatch.",
            "Runtime archive byte-size mismatch.",
            "load_json_without_duplicates",
            "_validate_tar_members",
        ):
            self.assertIn(required, verifier)

        manifest_verification = script.index(
            '"$INPUT_DIR/deployment_verifier.py" inputs'
        )
        extraction = script.index('tar -xzf "$INPUT_DIR/app.tar.gz"')
        self.assertLess(manifest_verification, extraction)

    def test_extracted_runtime_boundary_is_verified_before_rehearsal(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")
        verifier = (
            ROOT / "scripts" / "visual_qc" / "deployment_verifier.py"
        ).read_text(encoding="utf-8")

        for required in (
            'echo "__COMMIT_FULL__" > "$APP_NEW/VERSION"',
            'cp -a "$DEPLOYMENT_MANIFEST" '
            '"$ROLLBACK_DIR/deployment-manifest.json"',
            " report ",
        ):
            self.assertIn(required, script)
        for required in (
            "Extracted runtime manifest SHA-256 mismatch.",
            "Extracted runtime path count mismatch.",
            "Extracted runtime path is missing:",
            'report["target"] != expected_target',
            "Draft202012Validator",
        ):
            self.assertIn(required, verifier)

        extraction = script.index('tar -xzf "$INPUT_DIR/app.tar.gz"')
        extracted_verification = script.index(
            '"$INPUT_DIR/deployment_verifier.py" extracted'
        )
        rehearsal = script.index("audit_visual_qc_upgrade.py")
        application_switch = script.index('mv "$APP_DIR" "$ROLLBACK_DIR/app"')
        self.assertLess(extraction, extracted_verification)
        self.assertLess(extracted_verification, rehearsal)
        self.assertLess(rehearsal, application_switch)

    def test_preflight_failure_does_not_restore_an_untouched_database(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn("DATABASE_MAY_BE_MUTATED=0", script)
        self.assertIn(
            'if [ "$DATABASE_MAY_BE_MUTATED" -ne 1 ]; then',
            script,
        )
        mutation_flag = script.index("DATABASE_MAY_BE_MUTATED=1")
        rehearsal = script.index("audit_visual_qc_upgrade.py")
        start_qc = script.index(
            "pm2 startOrRestart ecosystem.config.js \\\n"
            "  --only motherboard-repair-visual-qc"
        )
        self.assertLess(rehearsal, mutation_flag)
        self.assertLess(mutation_flag, start_qc)

    def test_pre_switch_failure_restarts_instead_of_deleting_existing_qc(self):
        script = (
            ROOT / "scripts" / "deploy-visual-qc-pilot.ps1"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'if [ "$DATABASE_MAY_BE_MUTATED" -eq 1 ] || '
            '[ "$VENV_SWITCHED" -eq 1 ]; then',
            script,
        )
        self.assertIn(
            'elif [ "$QC_EXISTED" -eq 1 ]; then\n'
            '      pm2 restart motherboard-repair-visual-qc || true',
            script,
        )

    def test_pm2_qc_process_uses_loopback_and_external_data_and_environment(self):
        ecosystem = (ROOT / "ecosystem.config.js").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements-visual-qc.txt").read_text(encoding="utf-8")

        self.assertIn("numpy==2.2.6", requirements)
        self.assertIn("/opt/motherboard-repair-beta/venv-visual-qc/bin/python", ecosystem)
        self.assertIn('VISUAL_QC_HOST: "127.0.0.1"', ecosystem)
        self.assertIn(
            'VISUAL_QC_DATA_ROOT: "/opt/motherboard-repair-beta/data/visual-qc"',
            ecosystem,
        )

    def test_static_service_also_binds_to_loopback(self):
        source = (ROOT / "ai_proxy_server.py").read_text(encoding="utf-8")

        self.assertIn('HOST = os.environ.get("HOST", "127.0.0.1")', source)
        self.assertIn("ThreadingHTTPServer((HOST, PORT)", source)
        ecosystem = (ROOT / "ecosystem.config.js").read_text(encoding="utf-8")
        self.assertIn('HOST: "127.0.0.1"', ecosystem)

    def test_visual_intake_has_a_server_side_data_administrator_gate(self):
        source = (ROOT / "scripts" / "visual_qc" / "server" / "api.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("data_admin_role_required", source)
        self.assertIn('X-Actor-Role', source)


if __name__ == "__main__":
    unittest.main()
