#!/usr/bin/env python3
"""Fail-closed static .ores import preflight for the three-repository ML workspace.

This is NOT a compiler, parser, type checker or guest-execution attestation.
No external network, copying, imports of Python sources from repos, or subprocesses.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import json
import hashlib

REPOSITORIES = ("oreslang-tensor", "oreslang-autograd", "oreslang-ml")
ALLOWED_CROSS_EDGES = frozenset({
    ("oreslang-autograd", "oreslang-tensor"),
    ("oreslang-ml", "oreslang-autograd"),
})
EXPECTED_CROSS_EDGES = ALLOWED_CROSS_EDGES
MAX_FILE_BYTES = 1_000_000
MAX_FILES_PER_REPOSITORY = 200
IMPORT_RE = re.compile(
    r'^import\s+(?P<kind>class|fnc|module)\s+'
    r'(?P<symbols>[A-Za-z_][A-Za-z_0-9]*(?:\s*,\s*[A-Za-z_][A-Za-z_0-9]*)*)'
    r'\s+from\s+[\x27\x22](?P<path>[^\x27\x22\r\n]+)[\x27\x22]\s*;\s*$'
)
PUBLIC_FUNCTION_RE = re.compile(r'(?m)^\s*pub\s+fnc\s+([A-Za-z_]\w*)\s*\(')
PUBLIC_CLASS_RE = re.compile(r'(?m)^\s*define\s+pub\s+class\s+([A-Za-z_]\w*)\b')


def require(condition: bool, msg: str):
    if not condition:
        raise ValueError("ML_IMPORT_CLOSURE_DENIED: " + msg)


def regular_inside_workspace(path: Path, root: Path):
    """No symlink anywhere from workspace root to a source/import target."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise ValueError("ML_IMPORT_CLOSURE_DENIED: path escapes pinned workspace") from None
    current = root
    require(root.is_dir() and not root.is_symlink(), "invalid workspace root")
    for component in relative.parts:
        require(component not in ("", ".", ".."), "ambiguous source path")
        current = current / component
        require(not current.is_symlink(), "symlink source/import path")
    require(path.is_file() and path.suffix == ".ores", "missing Oreslang import target")


def validate_workspace_imports(workspace: Path, source_lock: Path | None = None):
    workspace = Path(workspace).absolute()
    require(workspace.is_dir() and not workspace.is_symlink(), "invalid workspace")
    sources = {}
    owners = {}
    blobs = {}
    for repo in REPOSITORIES:
        home = workspace / repo
        require(home.is_dir() and not home.is_symlink(), "missing or symlinked repository " + repo)
        paths = sorted(home.rglob("*.ores"))
        require(0 < len(paths) <= MAX_FILES_PER_REPOSITORY, "source count outside admitted bounds " + repo)
        for path in paths:
            regular_inside_workspace(path, workspace)
            data = path.read_bytes()
            require(len(data) <= MAX_FILE_BYTES and b"\x00" not in data, "oversized/NUL Oreslang source")
            try:
                code = data.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise ValueError("ML_IMPORT_CLOSURE_DENIED: invalid source UTF-8") from None
            require(not code.startswith("\ufeff"), "source BOM")
            sources[path] = code
            owners[path] = repo
            blobs[str(path.relative_to(workspace))] = hashlib.sha1(
                b"blob " + str(len(data)).encode() + b"\0" + data
            ).hexdigest()
    edges = set()
    imports = 0
    for path, code in sources.items():
        seen = set()
        for line in code.splitlines():
            if not line.lstrip().startswith("import "):
                continue
            match = IMPORT_RE.fullmatch(line.strip())
            require(match is not None, "unrecognized Oreslang import syntax " + path.name)
            kind, route = match.group("kind"), match.group("path")
            symbols = [s.strip() for s in match.group("symbols").split(",")]
            require(len(symbols) == len(set(symbols)), "duplicate symbols in import")
            if route == "std/assert" and kind == "module" and symbols == ["Assert"]:
                imports += 1
                continue
            require(route.startswith("./") or route.startswith("../"), "unapproved external import")
            require("\\" not in route and "//" not in route and not route.endswith("/"),
                    "ambiguous import path")
            target = path.parent / (route if route.endswith(".ores") else route + ".ores")
            # Normalization is only for lexical path resolution; no file is opened
            # before checking all ancestors for symlinks in the unnormalized path.
            parts = []
            for component in target.parts:
                if component == "..":
                    if parts:
                        parts.pop()
                elif component != ".":
                    parts.append(component)
            target = Path(*parts)
            regular_inside_workspace(target, workspace)
            require(target in sources, "import target not part of pinned workspace")
            owner, provider = owners[path], owners[target]
            if owner != provider:
                require((owner, provider) in ALLOWED_CROSS_EDGES,
                        "unapproved cross-repository source edge")
                edges.add((owner, provider))
            public = (set(PUBLIC_FUNCTION_RE.findall(sources[target])) if kind == "fnc" else
                      set(PUBLIC_CLASS_RE.findall(sources[target])) if kind == "class" else set())
            require(kind != "module" and set(symbols).issubset(public),
                    "imported symbol not publicly declared in pinned provider")
            for symbol in symbols:
                signature = (kind, symbol, str(target))
                require(signature not in seen, "duplicate imported declaration")
                seen.add(signature)
            imports += len(symbols)
    require(edges == EXPECTED_CROSS_EDGES, "ML tensor/autograd import closure incomplete")
    if source_lock is not None:
        lock_path = Path(source_lock)
        require(lock_path.is_file() and not lock_path.is_symlink(), "invalid source lock")
        raw = lock_path.read_bytes()
        require(0 < len(raw) <= 16_384, "invalid lock size")
        def no_duplicate_keys(pairs):
            obj = {}
            for k, v in pairs:
                require(k not in obj, "duplicate source lock JSON key")
                obj[k] = v
            return obj
        try:
            lock = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=no_duplicate_keys)
        except (UnicodeError, json.JSONDecodeError):
            raise ValueError("ML_IMPORT_CLOSURE_DENIED: invalid source lock JSON") from None
        require(isinstance(lock, dict) and set(lock) == {
            "schemaVersion", "kind", "organization", "expectedSourceFiles",
            "expectedImports", "requiredCrossRepositoryEdges", "sourceBlobs",
            "sourceExportAuthorized", "guestExecution", "releaseReady"
        }, "invalid lock schema")
        require(lock["schemaVersion"] == 1 and type(lock["schemaVersion"]) is int and
                lock["kind"] == "PINNED_SOURCE_BLOBS_NOT_GUEST" and
                lock["organization"] == "ores-truffle-oreslang" and
                lock["sourceExportAuthorized"] is False and lock["guestExecution"] is False and
                lock["releaseReady"] is False, "source lock cannot promote execution")
        require(type(lock["expectedSourceFiles"]) is int and
                lock["expectedSourceFiles"] == len(blobs) and
                type(lock["expectedImports"]) is int and
                lock["expectedImports"] == imports, "source/import count drift")
        require(lock["requiredCrossRepositoryEdges"] == [list(x) for x in sorted(edges)],
                "source lock import edge drift")
        require(type(lock["sourceBlobs"]) is dict and lock["sourceBlobs"] == blobs,
                "source Git blobs changed or added")
    return {"status": "STATIC_IMPORT_CLOSURE_NOT_COMPILED", "source_files": len(sources),
            "imports_verified": imports, "cross_repository_edges":
                [list(x) for x in sorted(edges)],
            "source_blob_lock_validated": source_lock is not None,
            "private_source_transferred": False, "compiler_executed": False,
            "guest_executed": False, "release_ready": False}


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--workspace", required=True)
    args.add_argument("--source-lock")
    options = args.parse_args()
    print(json.dumps(validate_workspace_imports(Path(options.workspace),
                                                         Path(options.source_lock) if options.source_lock else None), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
