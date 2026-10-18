"""Fail-closed exact commit/tree/cleanliness recheck for trusted local ML workspaces.

This does not attest source-to-binary provenance or sandbox the executed compiler.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

REPOS = frozenset(('oreslang-tensor', 'oreslang-autograd', 'oreslang-ml'))


def _git(repo: Path, *args: str) -> str:
    # Caller-provided GIT_DIR/INDEX_FILE/WORK_TREE cannot re-point the checker.
    env = {'PATH': os.defpath, 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
           'GIT_NO_REPLACE_OBJECTS': '1'}
    done = subprocess.run(['git', '-C', str(repo), *args], env=env,
                          check=True, capture_output=True, text=True, timeout=10)
    return done.stdout.strip()


def verify_pinned_checkouts(repos: dict, commits: dict, trees: dict) -> None:
    if set(repos) != REPOS or set(commits) != REPOS or set(trees) != REPOS:
        raise ValueError('ML_PIN_INTEGRITY_DENIED: incomplete repository identity map')
    for name in sorted(REPOS):
        repo = Path(repos[name])
        if not repo.is_dir() or repo.is_symlink():
            raise ValueError(f'ML_PIN_INTEGRITY_DENIED: {name}: missing or symlinked checkout')
        if Path(_git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo.resolve():
            raise ValueError(f'ML_PIN_INTEGRITY_DENIED: {name}: Git root mismatch')
        if _git(repo, 'rev-parse', '--verify', 'HEAD') != commits[name]:
            raise ValueError(f'ML_PIN_INTEGRITY_DENIED: {name}: commit changed')
        if _git(repo, 'show', '-s', '--format=%T', 'HEAD') != trees[name]:
            raise ValueError(f'ML_PIN_INTEGRITY_DENIED: {name}: Git tree changed')
        if _git(repo, 'status', '--porcelain', '--untracked-files=all'):
            raise ValueError(f'ML_PIN_INTEGRITY_DENIED: {name}: checkout dirty or untracked')
