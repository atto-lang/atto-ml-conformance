#!/usr/bin/env python3
"""Opt-in execution probe for real local Oreslang source (NOT a sandbox).

Requires a caller-supplied trusted real compiler, a sibling checkout workspace
at EXACT pinned clean commit SHAs, and a reproducible source-to-binary build
attestation before results can be publicly promoted. A forged executable can
print a pass marker; this runner does not authenticate the binary's origin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import resource
import sys
import tempfile
from check_workspace_imports import validate_workspace_imports
from compiler_cli_probe import probe_compiler_cli

MAX_OUTPUT = 65536
TIMEOUT = 120
JOBS = [
    ("oreslang-tensor", "tests/smoke.ores", "ORES_ML_TENSOR_SMOKE_PASS"),
    ("oreslang-autograd", "tests/smoke.ores", "ORES_ML_AUTOGRAD_SMOKE_PASS"),
    ("oreslang-autograd", "tests/tensor_vjp_smoke.ores", "ORES_ML_TENSOR_VJP_SMOKE_PASS"),
    ("oreslang-ml", "tests/smoke.ores", "ORES_ML_TRAINING_SMOKE_PASS"),
    ("oreslang-ml", "examples/train_with_autograd.ores", "ORES_ML_AUTOGRAD_TRAINING_PASS"),
    ("oreslang-ml", "examples/train_two_layer_autograd.ores", "ORES_ML_TWO_LAYER_RELU_AUTOGRAD_PASS"),
]
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(65536)
            if not block:
                break
            h.update(block)
    return h.hexdigest()

def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(["git", "-C", str(repo), *args],
                        capture_output=True, text=True, timeout=10, check=True)
    return cp.stdout.strip()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def limit_child_output():
    # POSIX runner: constrain actual file growth, not just post-exit reads.
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))

def execute(repo: Path, source: str, compiler: Path, marker: str):
    """Invoke the admitted compiler directly; source scripts are not proof."""
    require(isinstance(source, str) and source.endswith(".ores"),
            "guest source must be a .ores file")
    candidate = repo / source
    require(not candidate.is_symlink(), "guest source must not be a symlink")
    resolved = candidate.resolve(strict=True)
    require(resolved.is_file() and repo.resolve() in resolved.parents,
            "guest source escapes the pinned repository")
    env = os.environ.copy()
    # No ORESLANG_BIN or shell-dispatch path can impersonate a guest run.
    env.pop("ORESLANG_BIN", None)
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen([str(compiler), source], cwd=repo, env=env,
                                stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                start_new_session=(os.name == "posix"), preexec_fn=limit_child_output)
        timed_out = False
        try:
            proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait()
        out_size, err_size = out.tell(), err.tell()
        require(out_size <= MAX_OUTPUT and err_size <= MAX_OUTPUT,
                "guest output exceeded 64KiB capture bound")
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode("utf-8",errors="replace")
        stderr = err.read().decode("utf-8",errors="replace")
    require(not timed_out, "guest execution timed out")
    require(proc.returncode == 0, f"{repo.name} {source}: guest exit {proc.returncode}: {stderr[-1000:]}")
    observed = stdout.splitlines()
    required = marker.split("|")
    require(all(m in observed for m in required),
            f"{repo.name} {source}: missing required guest success markers")
    return {"repo":repo.name,"source":source,"exit":proc.returncode,
            "stdout_sha256":hashlib.sha256(stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(stderr.encode()).hexdigest(),
            "stdout_bytes":out_size,"stderr_bytes":err_size,
            "exact_marker_present":True}

def admit_compiler(compiler_path: str, expected_sha256: str, workspace: Path) -> tuple[Path, str]:
    """Hash-bind executable bytes before probe; provenance remains unverified."""
    require(isinstance(expected_sha256, str) and SHA256.fullmatch(expected_sha256),
            "explicit --compiler-sha256 is required (64 lowercase hex)")
    supplied = Path(compiler_path)
    require(supplied.is_absolute() and not supplied.is_symlink(),
            "compiler must be an absolute non-symlink executable")
    compiler = supplied.resolve(strict=True)
    require(compiler.is_file() and os.access(compiler, os.X_OK),
            "compiler must be an absolute executable file")
    require(compiler != workspace and workspace not in compiler.parents,
            "compiler executable must be outside mutable source workspace")
    actual = digest(compiler)
    require(actual == expected_sha256, "compiler binary SHA-256 mismatch")
    return compiler, actual

def run(args):
    workspace = Path(args.workspace).resolve(strict=True)
    compiler, admitted_digest = admit_compiler(
        args.compiler, getattr(args, "compiler_sha256", None), workspace)
    doc = json.loads(Path(args.manifest).read_text())
    require(doc.get("schema_version") == "oreslang-ml-workspace/v1",
            "unknown manifest version")
    shas = doc.get("repositories")
    require(isinstance(shas,dict) and set(shas)=={"oreslang-tensor","oreslang-autograd","oreslang-ml"},
            "manifest must pin all three producer repos exactly")
    trees = doc.get("source_trees")
    require(isinstance(trees, dict) and set(trees) == set(shas),
            "manifest must pin each original source Git tree")
    require(all(isinstance(tree, str) and SHA40.fullmatch(tree)
                for tree in trees.values()), "invalid source tree identity")
    repos = {}
    for name, sha in shas.items():
        require(isinstance(sha,str) and SHA40.fullmatch(sha),
                "invalid git commit identity")
        repo = (workspace / name).resolve(strict=True)
        require(repo.parent == workspace, "repository path escapes sibling workspace")
        require(repo.is_dir(), "missing repository directory")
        actual = git(repo,"rev-parse","HEAD")
        require(actual == sha, f"{name}: pinned source commit mismatch")
        tree = git(repo, "show", "-s", "--format=%T", "HEAD")
        require(tree == trees[name], f"{name}: tree mismatch")
        require(not git(repo,"status","--porcelain"),
                f"{name}: dirty or untracked working tree")
        repos[name] = repo
    # Resolve cross-repo source imports and public symbols only after all three
    # checked-out commits, trees and cleanliness have been verified.
    import_closure = validate_workspace_imports(
        workspace, Path(__file__).resolve().parents[1] / "integration/ml-source-blob-lock.v1.json"
    )
    cli_probe = probe_compiler_cli(compiler, repos["oreslang-tensor"])
    jobs = [execute(repos[name],source,compiler,marker)
            for name,source,marker in JOBS]
    require(all(not git(repo, "status", "--porcelain") for repo in repos.values()),
            "guest compiler modified one or more pinned repositories")
    require(digest(compiler) == admitted_digest,
            "compiler binary changed during the workspace probe")
    return {"schema_version":"oreslang-ml-execution-probe/v1",
            "status":"EXECUTED_UNATTESTED",
            "compiler_sha256":admitted_digest,
            "source_commits":shas,
            "source_trees":trees,
            "static_import_closure":import_closure,
            "compiler_cli_admission":cli_probe,
            "checks":jobs,
            "source_binary_provenance_attested":False,
            "automated_backend_parity_attested":False,
            "warning":"Success markers are forgeable; independently verify the compiler build and logs."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",required=True)
    p.add_argument("--compiler",required=True)
    p.add_argument("--compiler-sha256",required=True,
                   help="Exact SHA-256 of independently reviewed compiler executable")
    p.add_argument("--manifest",default="manifests/p0-workspace.json")
    args=p.parse_args()
    try:
        print(json.dumps(run(args),indent=2,sort_keys=True))
    except (ValueError,OSError,subprocess.SubprocessError,KeyError,TypeError) as error:
        print("UNVERIFIED: " + str(error),file=sys.stderr)
        sys.exit(1)
