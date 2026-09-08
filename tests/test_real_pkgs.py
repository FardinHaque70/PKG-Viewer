import json
from pathlib import Path

import pytest

from pkgviewer.services import PackageService, classify_package, detect_region

MANIFEST = Path(__file__).with_name("real_pkg_manifest.json")


@pytest.mark.real_pkg
def test_real_package_manifest():
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not expected or not all(Path(item["path"]).is_file() for item in expected):
        pytest.skip("real PKG samples are not present")
    service = PackageService()
    for item in expected:
        document, report, summary = service.inspect(item["path"])
        assert summary.title == item["title"]
        assert summary.title_id == item["title_id"]
        assert classify_package(document) == item["type"]
        assert detect_region(document) == item["region"]
        assert summary.firmware == item["firmware"]
        assert document.metadata.get("APP_VER") == item["app_version"]
        assert summary.sdk_version in {"3.50", "5.50"}
        assert report.status.value == "Pass"
        assert {c.check_id for c in report.checks} >= {"pkg.integrity.header", "pkg.integrity.param_sfo"}
