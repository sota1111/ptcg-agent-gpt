import io
import tarfile
from pathlib import Path

from scripts.fingerprint_submission import fingerprint


def make_archive(path: Path, *, mtime: int) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, mode, content in [
            ("main.py", 0o644, b"answer = 42\n"),
            ("agents/x.py", 0o755, b"pass\n"),
        ]:
            info = tarfile.TarInfo(name)
            info.mode = mode
            info.mtime = mtime
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def test_canonical_fingerprint_ignores_tar_metadata(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    make_archive(first, mtime=1)
    make_archive(second, mtime=2)
    assert fingerprint(first)["archive_sha256"] != fingerprint(second)["archive_sha256"]
    assert (
        fingerprint(first)["canonical_content_sha256"]
        == fingerprint(second)["canonical_content_sha256"]
    )


def test_canonical_fingerprint_includes_mode(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    make_archive(first, mtime=1)
    make_archive(second, mtime=1)
    with tarfile.open(second, "w:gz") as archive:
        content = b"answer = 42\n"
        info = tarfile.TarInfo("main.py")
        info.mode = 0o755
        info.size = len(content)
        archive.addfile(info, io.BytesIO(content))
    assert (
        fingerprint(first)["canonical_content_sha256"]
        != fingerprint(second)["canonical_content_sha256"]
    )
