"""Guard against accidental changes to the deposited raw inputs."""

from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_manifest(name: str) -> dict[str, str]:
    manifest = ROOT / "data" / "raw" / name
    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        expected, relative_path = line.split(maxsplit=1)
        entries[relative_path] = expected
    return entries


def test_raw_file_checksums() -> None:
    tracked = _read_manifest("checksums.sha256")
    external = _read_manifest("external_checksums.sha256")

    for relative_path, expected in tracked.items():
        path = ROOT / relative_path
        actual = sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"Raw file changed: {relative_path}"

    present_external = set()
    for relative_path, expected in external.items():
        path = ROOT / relative_path
        if not path.exists():
            continue
        present_external.add(relative_path)
        actual = sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"External raw file changed: {relative_path}"

    raw_root = ROOT / "data" / "raw"
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in raw_root.rglob("*")
        if path.is_file()
        and path.name
        not in {"README.md", "checksums.sha256", "external_checksums.sha256"}
    }
    expected_paths = set(tracked) | present_external
    assert actual_paths == expected_paths, "Add every raw input to a checksum manifest"
