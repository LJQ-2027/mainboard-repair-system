import tempfile
import unittest
from pathlib import Path

from ai_proxy_server import resolve_static_target


class StaticTargetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "main.html").write_text("main", encoding="utf-8")
        workbench = self.root / "assets" / "visual-qc-workbench"
        workbench.mkdir(parents=True)
        (workbench / "index.html").write_text("workbench", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def resolve(self, path):
        return resolve_static_target(path, str(self.root), "main.html")

    def test_root_uses_configured_application_index(self):
        self.assertEqual(self.resolve("/").name, "main.html")
        self.assertEqual(self.resolve("/").read_text(encoding="utf-8"), "main")

    def test_directory_route_uses_its_index_html(self):
        for path in (
            "/assets/visual-qc-workbench/",
            "/assets/visual-qc-workbench",
        ):
            target = self.resolve(path)
            self.assertEqual(target.name, "index.html")
            self.assertEqual(target.read_text(encoding="utf-8"), "workbench")

    def test_hidden_restricted_and_outside_paths_stay_unavailable(self):
        outside = self.root.parent / "outside.html"
        outside.write_text("outside", encoding="utf-8")
        try:
            self.assertIsNone(self.resolve("/.git/config"))
            self.assertIsNone(self.resolve("/assets/.secret/index.html"))
            self.assertIsNone(self.resolve("/.env"))
            self.assertIsNone(self.resolve("/../outside.html"))
        finally:
            outside.unlink()


if __name__ == "__main__":
    unittest.main()
