#!/usr/bin/env bash
# Completely source-free negative/positive harness for native acceptance gate.
# Synthetic Oreslang .ores contents + a FAKE compiler. A PASS here is proof
# of shell admission behavior ONLY, never evidence of guest compilation.
set -euo pipefail
export LC_ALL=C
die() { echo "NEURAL_NATIVE_GATE_TEST_FAIL: $*" >&2; exit 1; }
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/runner/scripts" "$scratch/runner/manifests" "$scratch/ws with spaces"
cp "$here/scripts/verify_neural_workspace.sh" "$scratch/runner/scripts/"
cp "$here/scripts/run_neural_native_guests.sh" "$scratch/runner/scripts/"
lock="$scratch/runner/manifests/neural-workspace-v1.lock"
: > "$lock"

for entry in \
  'oreslang-tensor|oreslang-tensor|tests/conv1d_vjp_smoke.ores' \
  'oreslang-autograd|oreslang-autograd|examples/tensor_training_vjp_smoke.ores' \
  'oreslang-ml|oreslang-ml|examples/train_tensor_mlp_vjp_cpu.ores' \
  'oreslang-ml-neurons|oreslang-ml|examples/train_stateful_neuron_microprocs.ores'; do
  IFS='|' read -r directory origin fixture <<< "$entry"
  root="$scratch/ws with spaces/$directory"
  mkdir -p "$root/$(dirname "$fixture")"
  echo '// synthetic source: NOT real Oreslang compilation' > "$root/$fixture"
  if [[ "$directory" == oreslang-ml ]]; then
    echo '// second synthetic source' > "$root/examples/train_adamw_smoke.ores"
  fi
  git -C "$root" init -q
  git -C "$root" add .
  git -C "$root" -c user.name='Synthetic Oreslang Test' \
    -c user.email='synthetic@example.invalid' commit -qm 'synthetic test'
  sha=$(git -C "$root" rev-parse HEAD)
  tree=$(git -C "$root" show -s --format=%T HEAD)
  printf '%s %s %s %s\n' "$directory" "$origin" "$sha" "$tree" >> "$lock"
done

cat > "$scratch/fake-compiler" <<'MOCK'
#!/bin/sh
case "$1" in
  tests/conv1d_vjp_smoke.ores) echo ORES_TENSOR_CONV1D_VJP_PASS ;;
  examples/tensor_training_vjp_smoke.ores) echo ORES_AUTOGRAD_TENSOR_TRAINING_VJP_PASS ;;
  examples/train_tensor_mlp_vjp_cpu.ores) echo ORES_ML_TENSOR_TWO_LAYER_VJP_PASS ;;
  examples/train_adamw_smoke.ores) echo ORES_ML_ADAMW_CHECKED_PASS ;;
  examples/train_stateful_neuron_microprocs.ores) echo ORES_ML_STATEFUL_NEURON_BACKPROP_PASS ;;
  *) exit 21 ;;
esac
MOCK
chmod +x "$scratch/fake-compiler"
sha=$(sha256sum -- "$scratch/fake-compiler" | cut -d ' ' -f1)
gate="$scratch/runner/scripts/run_neural_native_guests.sh"
bash "$gate" "$scratch/ws with spaces" "$scratch/fake-compiler" "$sha" > "$scratch/positive.log"
grep -q 'NEURAL_GUEST_EXECUTED_UNATTESTED checks=5' "$scratch/positive.log" ||
  die 'synthetic executable did not produce explicitly unattested result'
if grep -q 'VERIFIED_BACKEND' "$scratch/positive.log"; then
  die 'forged mock output must never be promoted to VERIFIED_BACKEND'
fi

reject() {
  if bash "$gate" "$scratch/ws with spaces" "$1" "$2" \
       > "$scratch/out" 2> "$scratch/err"; then
    die "expected native admission rejection: $3"
  fi
  grep -q 'NEURAL_GUEST_REJECTED' "$scratch/err" ||
    die "native gate did not fail closed: $3"
}
reject "$scratch/fake-compiler" \
  0000000000000000000000000000000000000000000000000000000000000000 \
  'wrong compiler SHA-256'

cat > "$scratch/wrong-compiler" <<'MOCK'
#!/bin/sh
echo wrong-guest-output
MOCK
chmod +x "$scratch/wrong-compiler"
wrong_sha=$(sha256sum -- "$scratch/wrong-compiler" | cut -d ' ' -f1)
reject "$scratch/wrong-compiler" "$wrong_sha" 'incorrect success marker'

# A mock guest that changes source after printing a correct marker must be
# rejected by the *post-execution* source integrity verification.
cat > "$scratch/mutating-compiler" <<'MOCK'
#!/bin/sh
echo '// mutation by a counterfeit compiler' >> "$1"
echo ORES_TENSOR_CONV1D_VJP_PASS
MOCK
chmod +x "$scratch/mutating-compiler"
mutating_sha=$(sha256sum -- "$scratch/mutating-compiler" | cut -d ' ' -f1)
reject "$scratch/mutating-compiler" "$mutating_sha" 'compiler mutated source'
echo 'NEURAL_NATIVE_GATE_SYNTHETIC_NEGATIVES_PASS'
