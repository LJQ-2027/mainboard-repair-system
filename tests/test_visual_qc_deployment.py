import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VisualQcDeploymentContractTests(unittest.TestCase):
    def test_nginx_template_protects_static_app_and_injects_verified_api_identity(self):
        template = (
            ROOT / "deploy" / "nginx" / "mb-repair-beta.locations.conf"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(template.count("auth_basic "), 2)
        self.assertIn("auth_basic_user_file /etc/nginx/.htpasswd-mb-repair-beta;", template)
        self.assertIn("proxy_pass http://127.0.0.1:3020/api/v1/visual-qc/;", template)
        self.assertIn("proxy_set_header X-Actor-Id $remote_user;", template)
        self.assertIn(
            "proxy_set_header X-Actor-Role $mb_repair_actor_role;",
            template,
        )
        self.assertIn('proxy_set_header Authorization "";', template)
        self.assertIn("client_max_body_size 20m;", template)
        self.assertIn("proxy_pass http://127.0.0.1:3010/;", template)

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
            "visual-qc-__COMMIT__",
            "DEPLOY_LOCK",
            "VENV_LEGACY_MOVED",
            "sqlite3",
            "chmod 0600",
            "rm -f \"$INPUT_DIR/.htpasswd-mb-repair-beta\"",
            "finally",
            "Authorization: Basic __TECH_AUTH__",
            "Authorization: Basic $authorization",
            "__REVIEWER_AUTH__",
            "wait_for_gateway_identity",
            '"__TECH_AUTH__" "__TECH_USER__" "technician"',
            '"__REVIEWER_AUTH__" "__REVIEWER_USER__" "reviewer"',
        ):
            self.assertIn(required, script)

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


if __name__ == "__main__":
    unittest.main()
