"""Host-side fail-closed behavioral preflight for a pinned, caller-trusted Oreslang CLI.

This does not establish compiler provenance, sandbox a malicious executable, or
prove compiler/runtime semantics. Only use in an authorized local workspace.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import resource
import signal
import subprocess
import tempfile

MAX_BYTES = 65536
PROBE_TIMEOUT = 30
EXPECTED = {
    'jvm': ('jit', 'runtime-selected'),
    'aot': ('aot', 'interpreter-no-jit'),
    'hybrid': ('hybrid', 'runtime-selected'),
}


def require(test: bool, message: str):
    if not test:
        raise ValueError('ML_COMPILER_CLI_DENIED: ' + message)


def _bound_output():
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))


def _run(compiler: Path, args: list[str], cwd: Path):
    env = os.environ.copy()
    env.pop('ORESLANG_BIN', None)
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(
            [str(compiler), *args], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=out, stderr=err, start_new_session=True, preexec_fn=_bound_output)
        try:
            process.wait(timeout=PROBE_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise ValueError('ML_COMPILER_CLI_DENIED: compiler probe timed out') from None
        require(out.tell() <= MAX_BYTES and err.tell() <= MAX_BYTES,
                'compiler probe exceeded bounded output')
        out.seek(0)
        err.seek(0)
        output, errors = out.read(), err.read()
    return process.returncode, output, errors


def probe_compiler_cli(compiler: Path, tensor_repo: Path) -> dict:
    """Require Java OresMain-compatible build-info and positive/negative --check.

    The positive file belongs to an already verified pinned, clean source checkout.
    The deliberately malformed negative lives OUTSIDE those source checkouts.
    """
    compiler = Path(compiler)
    tensor_repo = Path(tensor_repo)
    source = tensor_repo / 'tests' / 'smoke.ores'
    require(source.is_file() and not source.is_symlink() and
            tensor_repo.resolve() in source.resolve().parents,
            'missing/escaping pinned positive source')

    code, output, errors = _run(compiler, ['--build-info'], tensor_repo)
    require(code == 0 and not errors and len(output) <= 4096,
            'missing clean bounded successful --build-info response')
    def unique_fields(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate --build-info JSON key')
            result[key] = value
        return result

    def reject_nonfinite(value):
        raise ValueError('ML_COMPILER_CLI_DENIED: invalid nonfinite JSON: ' + value)

    try:
        info = json.loads(output.decode('utf-8', 'strict'),
                          object_pairs_hook=unique_fields,
                          parse_constant=reject_nonfinite)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError('ML_COMPILER_CLI_DENIED: malformed --build-info JSON') from None
    require(type(info) is dict and set(info) == {
        'build_mode', 'default_execution_mode', 'guest_execution'
    }, 'unexpected --build-info schema')
    mode = info['build_mode']
    require(type(mode) is str and mode in EXPECTED and
            (info['default_execution_mode'], info['guest_execution']) == EXPECTED[mode],
            'inconsistent build mode or execution capability')

    # The CLI contract is --check followed by a real Oreslang file.
    code, out, err = _run(compiler, ['--check', 'tests/smoke.ores'], tensor_repo)
    require(code == 0 and not out,
            'pinned positive Oreslang smoke source failed --check')

    # Do not mutate the pinned repository or create a temporary source-bearing
    # mirror in an alternate organization. This file is synthetic invalid code.
    with tempfile.TemporaryDirectory(prefix='oreslang-ml-cli-negative-') as tmp:
        negative = Path(tmp) / 'parse-negative.ores'
        negative.write_bytes(b'pub routine main( {\n')
        code, bad_out, bad_err = _run(compiler, ['--check', str(negative)], Path(tmp))
        # OresMain uses exit 1 for a source diagnostic, vs. exit 2 for bad
        # command-line usage. Reject unrelated crashes/missing binary errors.
        expected = re.compile(rb'^' + re.escape(os.fsencode(negative)) +
                              rb':[1-9][0-9]*:[1-9][0-9]*: error: ', re.MULTILINE)
        require(code == 1 and not bad_out and expected.search(bad_err) is not None,
                'malformed Oreslang source was accepted or lacked a source diagnostic')
    return {
        'status': 'CLI_BEHAVIOR_PROBED_UNATTESTED',
        'launcher_contract': 'dev.oreslang.launcher.OresMain',
        'build_info': info,
        'positive_check': {'exit': 0, 'source': 'oreslang-tensor/tests/smoke.ores'},
        'negative_check': {'rejected': True, 'nonzero_exit': True},
        'build_info_stdout_sha256': hashlib.sha256(output).hexdigest(),
        'source_binary_provenance_attested': False,
        'guest_executed': False,
    }
