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

MAX_OUTPUT = 65536
TIMEOUT = 120
JOBS = [
    ("oreslang-tensor", "scripts/test.sh", "ORES_ML_TENSOR_SMOKE_PASS"),
    ("oreslang-autograd", "scripts/test.sh", "ORES_ML_AUTOGRAD_SMOKE_PASS"),
    ("oreslang-ml", "scripts/test.sh", "ORES_ML_TRAINING_SMOKE_PASS"),
    ("oreslang-ml", "scripts/test-workspace.sh", "ORES_ML_AUTOGRAD_TRAINING_PASS"),
]
SHA40 = re.compile(r"^[0-9a-f]{40}$")

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

def execute(repo: Path, script: str, compiler: Path, marker: str):
    env = os.environ.copy()
    env["ORESLANG_BIN"] = str(compiler)
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(["sh", script], cwd=repo, env=env,
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
    require(proc.returncode == 0, f"{repo.name} {script}: guest exit {proc.returncode}: {stderr[-1000:]}")
    require(marker in stdout.splitlines(),
            f"{repo.name} {script}: missing exact guest success marker")
    return {"repo":repo.name,"script":script,"exit":proc.returncode,
            "stdout_sha256":hashlib.sha256(stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(stderr.encode()).hexdigest(),
            "stdout_bytes":out_size,"stderr_bytes":err_size,
            "exact_marker_present":True}

def run(args):
    workspace = Path(args.workspace).resolve(strict=True)
    compiler = Path(args.compiler).resolve(strict=True)
    require(compiler.is_file() and os.access(compiler,os.X_OK),
            "compiler must be an absolute executable file")
    doc = json.loads(Path(args.manifest).read_text())
    require(doc.get("schema_version") == "oreslang-ml-workspace/v1",
            "unknown manifest version")
    shas = doc.get("repositories")
    require(isinstance(shas,dict) and set(shas)=={"oreslang-tensor","oreslang-autograd","oreslang-ml"},
            "manifest must pin all three producer repos exactly")
    repos = {}
    for name, sha in shas.items():
        require(isinstance(sha,str) and SHA40.fullmatch(sha),
                "invalid git commit identity")
        repo = (workspace / name).resolve(strict=True)
        require(repo.parent == workspace, "repository path escapes sibling workspace")
        require(repo.is_dir(), "missing repository directory")
        actual = git(repo,"rev-parse","HEAD")
        require(actual == sha, f"{name}: pinned source commit mismatch")
        require(not git(repo,"status","--porcelain"),
                f"{name}: dirty or untracked working tree")
        repos[name] = repo
    jobs = [execute(repos[name],script,compiler,marker)
            for name,script,marker in JOBS]
    return {"schema_version":"oreslang-ml-execution-probe/v1",
            "status":"EXECUTED_UNATTESTED",
            "compiler_sha256":digest(compiler),
            "source_commits":shas,
            "checks":jobs,
            "source_binary_provenance_attested":False,
            "automated_backend_parity_attested":False,
            "warning":"Success markers are forgeable; independently verify the compiler build and logs."}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",required=True)
    p.add_argument("--compiler",required=True)
    p.add_argument("--manifest",default="manifests/p0-workspace.json")
    args=p.parse_args()
    try:
        print(json.dumps(run(args),indent=2,sort_keys=True))
    except (ValueError,OSError,subprocess.SubprocessError,KeyError,TypeError) as error:
        print("UNVERIFIED: " + str(error),file=sys.stderr)
        sys.exit(1)
