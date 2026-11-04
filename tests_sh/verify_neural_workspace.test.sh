#!/usr/bin/env bash
# Source-free adversarial test of the exact-source workspace verifier.
# Generates FOUR disposable synthetic repositories; never exports any private
# project source or tests a compiler. Bash, Git and coreutils only.
set -euo pipefail
export LC_ALL=C
die() { echo "NEURAL_LOCK_TEST_FAIL: $*" >&2; exit 1; }
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/runner/scripts" "$scratch/runner/manifests" "$scratch/work space"
cp "$here/scripts/verify_neural_workspace.sh" "$scratch/runner/scripts/"
lock="$scratch/runner/manifests/neural-workspace-v1.lock"
: > "$lock"

for spec in 'oreslang-tensor:oreslang-tensor' \
            'oreslang-autograd:oreslang-autograd' \
            'oreslang-ml:oreslang-ml' \
            'oreslang-ml-neurons:oreslang-ml'; do
  directory=${spec%%:*}
  source_repo=${spec#*:}
  root="$scratch/work space/$directory"
  mkdir -p "$root"
  git -C "$root" init -q
  printf 'synthetic fixture from %s\n' "$source_repo" > "$root/fixture data.txt"
  git -C "$root" add -- .
  git -C "$root" -c user.name='Neural Contract Test' \
    -c user.email='neural-contract@example.invalid' commit -qm 'synthetic init'
  commit=$(git -C "$root" rev-parse HEAD)
  tree=$(git -C "$root" show -s --format=%T HEAD)
  printf '%s %s %s %s\n' "$directory" "$source_repo" "$commit" "$tree" >> "$lock"
done

verify() {
  bash "$scratch/runner/scripts/verify_neural_workspace.sh" "$scratch/work space"
}
expect_reject() {
  if verify > "$scratch/stdout" 2> "$scratch/stderr"; then
    die "expected source verifier to fail: $1"
  fi
  grep -q 'NEURAL_SOURCE_REJECTED' "$scratch/stderr" ||
    die "missing fail-closed rejection marker: $1"
}
verify > "$scratch/clean.out"
grep -q 'NEURAL_SOURCE_INTEGRITY_OK checked=4' "$scratch/clean.out" ||
  die 'clean four-repo workspace not accepted'

root="$scratch/work space/oreslang-tensor"
printf 'tamper\n' >> "$root/fixture data.txt"
expect_reject 'ordinary modified source'
git -C "$root" checkout -q -- 'fixture data.txt'

# Skip-worktree suppresses normal status reporting; direct blob hash MUST catch.
git -C "$root" update-index --skip-worktree 'fixture data.txt'
printf 'hidden tamper\n' >> "$root/fixture data.txt"
expect_reject 'skip-worktree hidden modification'
git -C "$root" update-index --no-skip-worktree 'fixture data.txt'
git -C "$root" checkout -q -- 'fixture data.txt'

git -C "$root" update-index --assume-unchanged 'fixture data.txt'
printf 'assumed tamper\n' >> "$root/fixture data.txt"
expect_reject 'assume-unchanged hidden modification'
git -C "$root" update-index --no-assume-unchanged 'fixture data.txt'
git -C "$root" checkout -q -- 'fixture data.txt'

printf 'extra\n' > "$root/untracked.txt"
expect_reject 'untracked file'
rm "$root/untracked.txt"

# Reject a fake Git symlink rather than accepting it as a regular blob.
ln -s 'fixture data.txt' "$root/evil-link"
git -C "$root" add evil-link
expect_reject 'dirty staged symlink'
git -C "$root" reset -q -- evil-link
rm "$root/evil-link"

# Reject tampered pinned commit/tree even with an otherwise-clean checkout.
cp "$lock" "$scratch/clean.lock"
sed -i.bak '1s/ [0-9a-f]\{40\}$/ 0000000000000000000000000000000000000000/' "$lock"
expect_reject 'incorrect pinned tree'
mv "$scratch/clean.lock" "$lock"
verify > "$scratch/clean-again.out"
grep -q 'NEURAL_SOURCE_INTEGRITY_OK checked=4' "$scratch/clean-again.out" ||
  die 'clean repaired workspace not accepted'
echo 'NEURAL_SOURCE_LOCK_NEGATIVES_PASS'
