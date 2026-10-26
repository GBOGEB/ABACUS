"""Dashboard-health first-red regression: percent-encoded links must resolve, not waive."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/dashboard-health.yml"
INDEX = ROOT / "docs/repo-structure/index.html"
TARGETS = (
    "DMAIC CICD Implementation Bundle.md",
    "DMAIC Implementation Files Handover.md",
    "DMAIC Implementation Manifest.md",
)


class DashboardHrefRegression(unittest.TestCase):
    def test_real_percent20_targets_exist_beneath_repo_root(self):
        html = INDEX.read_text(encoding="utf-8")
        for name in TARGETS:
            with self.subTest(name=name):
                encoded = "../../" + name.replace(" ", "%20")
                self.assertIn(encoded, html)
                self.assertTrue((INDEX.parent / "../../" / name).is_file())

    def test_health_check_checks_real_decoded_target_before_broken(self):
        src = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('decoded_target="${target//%20/ }"', src)
        self.assertIn('if [ "$decoded_target" != "$target" ] && [ -e "$decoded_target" ]; then', src)
        self.assertIn('echo "🔗 Broken:', src)
        self.assertIn('BROKEN=$((BROKEN+1))', src)

    def test_missing_encoded_link_remains_broken(self):
        href = "../../not%20an%20existing%20file.md"
        raw = INDEX.parent / href
        decoded = INDEX.parent / href.replace("%20", " ")
        self.assertFalse(raw.exists())
        self.assertFalse(decoded.exists())


if __name__ == "__main__":
    unittest.main()
