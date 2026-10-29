#!/usr/bin/env bash
# Opt-in native guest smoke runner for a reviewed local Oreslang ML workspace.
# Linux runner only: sha256sum + timeout + git + bash.
# Usage: bash scripts/run_neural_native_guests.sh \
#   /absolute/workspace /absolute/trusted/oreslang /64-lowercase-hex-binary-sha256
# This result is EXECUTED_UNATTESTED, never automatically VERIFIED_BACKEND.
set -euo pipefail
export LC_ALL=C
die() { echo "NEURAL_GUEST_REJECTED: $*" >&2; exit 1; }
(( $# == 3 )) || die 'expected absolute workspace, absolute compiler, compiler SHA-256'
workspace=$1
compiler=$2
expected_sha=$3
sha64='^[0-9a-f]{64}$'
[[ "$workspace" = /* && -d "$workspace" && ! -L "$workspace" ]] ||
  die 'workspace must be absolute non-symlink directory'
workspace=$(cd -- "$workspace" && pwd -P)
[[ "$compiler" = /* && -f "$compiler" && -x "$compiler" && ! -L "$compiler" ]] ||
  die 'compiler must be absolute non-symlink executable'
[[ "$expected_sha" =~ $sha64 ]] || die 'expected compiler SHA-256 is invalid'
[[ "$compiler" != "$workspace/"* ]] || die 'compiler cannot be in a mutable workspace'
command -v sha256sum >/dev/null || die 'sha256sum required (Linux acceptance)'
command -v timeout >/dev/null || die 'timeout required (Linux acceptance)'
command -v cmp >/dev/null || die 'cmp required'
timeout_bin=$(command -v timeout)
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
verify="$here/verify_neural_workspace.sh"
[[ -f "$verify" && ! -L "$verify" ]] || die 'workspace verifier missing'

compiler_sha() { sha256sum -- "$compiler" | cut -d ' ' -f1; }
[[ "$(compiler_sha)" == "$expected_sha" ]] ||
  die 'compiler binary does not match supplied SHA-256'
bash "$verify" "$workspace"

outdir=$(mktemp -d)
trap 'rm -rf -- "$outdir"' EXIT
jobs=(
  'oreslang-tensor|tests/conv1d_vjp_smoke.ores|ORES_TENSOR_CONV1D_VJP_PASS'
  'oreslang-autograd|examples/tensor_training_vjp_smoke.ores|ORES_AUTOGRAD_TENSOR_TRAINING_VJP_PASS'
  'oreslang-ml|examples/train_tensor_mlp_vjp_cpu.ores|ORES_ML_TENSOR_TWO_LAYER_VJP_PASS'
  'oreslang-ml|examples/train_adamw_smoke.ores|ORES_ML_ADAMW_CHECKED_PASS'
  'oreslang-ml-neurons|examples/train_stateful_neuron_microprocs.ores|ORES_ML_STATEFUL_NEURON_BACKPROP_PASS'
)

for i in "${!jobs[@]}"; do
  IFS='|' read -r dirname source marker <<< "${jobs[$i]}"
  repo="$workspace/$dirname"
  [[ "$source" == *.ores && "$source" != /* &&
     "$source" != *'..'* && "$source" != *'//'*
  ]] || die "guest source path invalid: $source"
  [[ -f "$repo/$source" && ! -L "$repo/$source" ]] ||
    die "$dirname: source absent/symlink"
  bash "$verify" "$workspace" >/dev/null ||
    die 'source integrity changed before guest execution'
  [[ "$(compiler_sha)" == "$expected_sha" ]] ||
    die 'compiler binary changed before guest execution'
  out="$outdir/$i.stdout"
  err="$outdir/$i.stderr"
  # A private compiler is privileged input: only run pre-reviewed builds in a
  # constrained runner; this executable check is NOT a sandbox or provenance.
  # ulimit limits stdout/stderr file growth during compilation/execution.
  (
    cd -- "$repo"
    ulimit -f 64
    env -i PATH=/usr/bin:/bin LC_ALL=C TZ=UTC \
      "$timeout_bin" -k 5s 120s "$compiler" "$source" > "$out" 2> "$err"
  ) || die "$dirname/$source: native compiler/guest nonzero or timeout"
  [[ "$(wc -c < "$out")" -le 65536 && "$(wc -c < "$err")" -le 65536 ]] ||
    die "$dirname/$source: stdout/stderr bound exceeded"
  printf '%s\n' "$marker" > "$outdir/expected"
  cmp -s "$out" "$outdir/expected" ||
    die "$dirname/$source: exact expected stdout missing"
  [[ "$(compiler_sha)" == "$expected_sha" ]] ||
    die "$dirname/$source: compiler binary changed during execution"
  bash "$verify" "$workspace" >/dev/null ||
    die "$dirname/$source: repository tree changed during execution"
  source_blob=$(git -C "$repo" rev-parse --verify "HEAD:$source")
  stdout_sha=$(sha256sum -- "$out" | cut -d ' ' -f1)
  stderr_sha=$(sha256sum -- "$err" | cut -d ' ' -f1)
  printf 'NEURAL_GUEST_EXECUTED_UNATTESTED source=%s/%s git_blob=%s stdout_sha256=%s stderr_sha256=%s exit=0\n' \
    "$dirname" "$source" "$source_blob" "$stdout_sha" "$stderr_sha"
done
printf 'NEURAL_GUEST_EXECUTED_UNATTESTED checks=5 compiler_sha256=%s provenance=NOT_ATTESTED backend=UNVERIFIED\n' "$expected_sha"
