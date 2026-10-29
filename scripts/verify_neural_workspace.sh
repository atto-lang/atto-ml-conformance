#!/usr/bin/env bash
# Exact-source verifier for a local, trusted four-checkout Oreslang ML workspace.
# This DOES NOT run an Oreslang compiler, attest binaries or authorize export.
# Usage: bash scripts/verify_neural_workspace.sh /absolute/local/workspace
set -euo pipefail
export LC_ALL=C
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_NO_REPLACE_OBJECTS=1
export GIT_OPTIONAL_LOCKS=0
# Ignore untrusted repository-local filesystem monitor configurations.
git_safe() { git -c core.fsmonitor=false "$@"; }
die() { printf 'NEURAL_SOURCE_REJECTED: %s\n' "$*" >&2; exit 1; }

if (( $# != 1 )); then
  die 'exactly one absolute local workspace path is required'
fi
workspace_input=$1
[[ "$workspace_input" = /* ]] || die 'workspace must be absolute'
[[ -d "$workspace_input" && ! -L "$workspace_input" ]] ||
  die 'workspace must be an existing non-symlink directory'
workspace=$(cd -- "$workspace_input" && pwd -P)
[[ "$workspace" = /* ]] || die 'cannot canonicalize workspace'
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
lock="$here/../manifests/neural-workspace-v1.lock"
[[ -f "$lock" && ! -L "$lock" ]] || die 'source lock missing or symlinked'
sha40='^[0123456789abcdef]{40}$'
checked=0

while read -r directory repository expected_commit expected_tree extra; do
  [[ -z "${directory:-}" || "$directory" == \#* ]] && continue
  [[ -z "${extra:-}" ]] || die 'lock has more than four fields'
  [[ "$expected_commit" =~ $sha40 && "$expected_tree" =~ $sha40 ]] ||
    die 'lock entry is not 40-hex pinned commit/tree'
  case "$directory:$repository" in
    oreslang-tensor:oreslang-tensor|oreslang-autograd:oreslang-autograd|oreslang-ml:oreslang-ml|oreslang-ml-neurons:oreslang-ml) ;;
    *) die "unrecognized workspace entry: $directory:$repository" ;;
  esac
  root="$workspace/$directory"
  [[ -d "$root" && ! -L "$root" ]] || die "$directory: absent or symlink root"
  actual_dir=$(cd -- "$root" && pwd -P)
  [[ "$actual_dir" == "$root" ]] || die "$directory: path escaped or was noncanonical"
  gitroot=$(git_safe -C "$root" rev-parse --show-toplevel) ||
    die "$directory: not a Git checkout"
  [[ "$gitroot" == "$root" ]] || die "$directory: nested/unexpected Git root"
  actual_commit=$(git_safe -C "$root" rev-parse --verify 'HEAD^{commit}') ||
    die "$directory: missing HEAD commit"
  [[ "$actual_commit" == "$expected_commit" ]] ||
    die "$directory: incorrect commit $actual_commit"
  actual_tree=$(git_safe -C "$root" show -s --format=%T HEAD) ||
    die "$directory: missing Git tree"
  [[ "$actual_tree" == "$expected_tree" ]] ||
    die "$directory: incorrect Git tree $actual_tree"
  porcelain=$(git_safe -C "$root" status --porcelain=v1 --untracked-files=all) ||
    die "$directory: git status failed"
  [[ -z "$porcelain" ]] || die "$directory: dirty or untracked working tree"

  # Git status deliberately respects skip-worktree and assume-unchanged bits.
  # Independently hash EVERY tracked on-disk blob against the locked HEAD,
  # catching modified/masked files and mismatching executable bytes.
  files=0
  listing=$(mktemp)
  git_safe -C "$root" ls-tree -rz --full-tree HEAD > "$listing" ||
    die "$directory: unable to enumerate tracked Git tree"
  while IFS= read -r -d '' entry; do
    [[ "$entry" == *$'\t'* ]] || die "$directory: malformed Git ls-tree record"
    header=${entry%%$'\t'*}
    path=${entry#*$'\t'}
    mode=${header%% *}
    object=${header#* }
    type=${object%% *}
    object_sha=${object##* }
    [[ "$type" == blob && ( "$mode" == 100644 || "$mode" == 100755 ) ]] ||
      die "$directory: submodule/symlink/special Git tree entry: $path"
    [[ "$object_sha" =~ $sha40 ]] || die "$directory: malformed blob SHA"
    [[ -f "$root/$path" && ! -L "$root/$path" ]] ||
      die "$directory: missing/nonregular/on-disk symlink $path"
    actual_blob=$(git_safe -C "$root" hash-object --no-filters -- "$path") ||
      die "$directory: failed to hash $path"
    [[ "$actual_blob" == "$object_sha" ]] ||
      die "$directory: HEAD blob mismatch in $path"
    files=$((files+1))
  done < "$listing"
  rm -f -- "$listing"
  (( files > 0 )) || die "$directory: empty or unreadable Git tree"
  printf 'NEURAL_SOURCE_OK checkout=%s commit=%s tree=%s verified_blobs=%s\n' \
    "$directory" "$actual_commit" "$actual_tree" "$files"
  checked=$((checked+1))
done < "$lock"
[[ "$checked" -eq 4 ]] || die "expected exactly four pinned producer checkouts (got $checked)"
printf 'NEURAL_SOURCE_INTEGRITY_OK checked=4 status=SOURCE_ONLY_NO_COMPILER_EXECUTION\n'
