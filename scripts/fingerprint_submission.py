"""Compute archive and metadata-independent canonical content fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(archive_path: Path) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            data = extracted.read()
            entries.append(
                {
                    "path": member.name,
                    "mode": member.mode & 0o777,
                    "size": len(data),
                    "sha256": sha256(data),
                }
            )
    canonical = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return {
        "schema_version": 1,
        "archive": str(archive_path),
        "archive_sha256": sha256(archive_path.read_bytes()),
        "canonical_content_sha256": sha256(canonical),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = fingerprint(args.archive)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
