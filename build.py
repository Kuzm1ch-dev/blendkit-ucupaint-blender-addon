#!/usr/bin/env python3
"""Build the Blender extension zip: dist/blendkit_ucupaint-<version>.zip

    python build.py                 # build the current version
    python build.py --bump patch    # 1.2.1 -> 1.2.2, then build (also: minor, major)
    python build.py --set 1.3.0     # set an exact version, then build

The version lives in one place: blendkit_ucupaint/blender_manifest.toml.
Needs only Python 3.9+ (no Blender). The same zip can be made with
`blender --command extension build --source-dir blendkit_ucupaint --output-dir dist`.
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "blendkit_ucupaint"
MANIFEST = SRC / "blender_manifest.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
DIST = ROOT / "dist"
SKIP_DIRS = {"__pycache__", ".git", ".idea", ".vscode"}
SKIP_SUFFIX = {".pyc", ".pyo", ".blend1"}


def read_manifest():
    try:
        import tomllib  # Python 3.11+
        with open(MANIFEST, "rb") as f:
            return tomllib.load(f)
    except ImportError:  # older Python: the top-level keys are enough here
        text = MANIFEST.read_text(encoding="utf-8").split("\n[", 1)[0]
        return {k: v for k, v in re.findall(r'(?m)^(\w+)\s*=\s*"([^"]*)"', text)} | \
            {k: v for k, v in re.findall(r'(?m)^(\w+)\s*=\s*(\[[^\]]*\])', text)}


def set_version(new):
    if not re.fullmatch(r"\d+\.\d+\.\d+", new):
        sys.exit(f"bad version: {new} (expected X.Y.Z)")
    text = MANIFEST.read_text(encoding="utf-8")
    text, n = re.subn(r'(?m)^version\s*=\s*"[^"]*"', f'version = "{new}"', text, count=1)
    if n != 1:
        sys.exit("version line not found in blender_manifest.toml")
    MANIFEST.write_text(text, encoding="utf-8")


def bumped(version, part):
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def build():
    m = read_manifest()
    for key in ("id", "version", "name", "maintainer", "blender_version_min", "license"):
        if key not in m:
            sys.exit(f"blender_manifest.toml: missing '{key}'")
    version = m["version"]
    if CHANGELOG.exists() and f"## {version}" not in CHANGELOG.read_text(encoding="utf-8"):
        print(f"warning: CHANGELOG.md has no '## {version}' section")
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{m['id']}-{version}.zip"
    files = sorted(p for p in SRC.rglob("*")
                   if p.is_file() and not (SKIP_DIRS & set(p.relative_to(SRC).parts)) and p.suffix not in SKIP_SUFFIX)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(SRC).as_posix())  # manifest at the zip root, as Blender expects
        if (ROOT / "LICENSE").exists():
            z.write(ROOT / "LICENSE", "LICENSE")
    print(f"{out.relative_to(ROOT)}  ({len(files)} files, v{version})")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--bump", choices=["major", "minor", "patch"], help="raise the version, then build")
    g.add_argument("--set", metavar="X.Y.Z", help="set the version, then build")
    a = ap.parse_args()
    if a.bump:
        set_version(bumped(read_manifest()["version"], a.bump))
    elif a.set:
        set_version(a.set)
    build()


if __name__ == "__main__":
    main()
