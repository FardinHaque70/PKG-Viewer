from pathlib import Path

from pkgviewer.library import discover_packages


def test_discover_packages_recursively_and_case_insensitive(tmp_path):
    (tmp_path / "a" / "nested").mkdir(parents=True)
    (tmp_path / "a" / "one.pkg").write_bytes(b"")
    (tmp_path / "a" / "nested" / "two.PKG").write_bytes(b"")
    (tmp_path / "ignore.bin").write_bytes(b"")
    result = discover_packages(tmp_path)
    assert {Path(path).name for path in result.paths} == {"one.pkg", "two.PKG"}


def test_discover_packages_rejects_file(tmp_path):
    file = tmp_path / "file.pkg"
    file.write_bytes(b"")
    try:
        discover_packages(file)
    except NotADirectoryError:
        pass
    else:
        raise AssertionError("expected NotADirectoryError")
