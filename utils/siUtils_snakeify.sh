#!/bin/zsh
# =============================================================================
# siUtils_snakeify.sh 🛡️🐍
# -----------------------------------------------------------------------------
# Recursively convert filenames & directories to snake_case (Python-friendly).
#
# Features:
#   - camelCase → snake_case; spaces/dashes → underscores
#   - Collapses duplicate underscores, trims edges, lowercases
#   - Preserves file extensions
#   - Prevents collisions by appending _1, _2, ...
#   - Skips hidden files/dirs and critical infra/config files
#   - Skips ALL *.yaml / *.yml by default (Helm, K8s, Docker, ArgoCD, etc.)
#       • Override with: ALLOW_YAML=1
#   - Preserves literal phrase `siUtils` (never split or lowercased)
#   - Skips Python caches/bytecode (__pycache__, *.pyc, etc.)
#   - Skips test artifacts (tst / Tst / TST in name)
#   - Respects .gitignore entries at TARGET_DIR root
#   - Compatible with macOS system bash (v3.2) — no associative arrays
#
# Usage examples:
#   DRY_RUN=1 bash utils/siUtils_snakeify.sh .      # preview safely from repo root
#   bash utils/siUtils_snakeify.sh .                # actually rename from repo root
#   DRY_RUN=1 bash utils/siUtils_snakeify.sh ..     # run from /repo/utils over entire /repo
#
# Safety Notes:
#   - Hidden files (.*) are skipped.
#   - Any name containing double underscores (__*__) is skipped.
#   - YAMLs are excluded by default (Helm, K8s, Compose, Argo, etc.).
#   - Files in .gitignore are never touched (loaded from TARGET_DIR/.gitignore).
#   - Run in DRY_RUN=1 mode first to preview changes.
# =============================================================================

set -euo pipefail

# --- Helper: snakeify stem ---------------------------------------------------
snakeify_stem() {
  local stem="$1"
  # Preserve reserved camelCase phrases by masking before transforms
  stem=$(printf '%s' "$stem" | sed 's/siUtils/SIUTILS_TOKEN/g')

  # Insert underscore between lower/number -> Upper transitions
  stem=$(printf '%s' "$stem" | sed -E 's/([a-z0-9])([A-Z])/\1_\2/g')

  # Replace non-alphanumeric characters with underscores
  stem=$(printf '%s' "$stem" | tr ' ' '_' | sed -E 's/[^A-Za-z0-9_]+/_/g')

  # Collapse multiple underscores
  stem=$(printf '%s' "$stem" | sed -E 's/_+/_/g')

  # Trim leading/trailing underscores
  stem=$(printf '%s' "$stem" | sed -E 's/^_+//; s/_+$//')

  # Lowercase (mask becomes siutils_token)
  stem=$(printf '%s' "$stem" | tr '[:upper:]' '[:lower:]')

  # Ensure valid Python identifier
  [[ "$stem" =~ ^[0-9] ]] && stem="_${stem}"
  [[ -z "$stem" ]] && stem="_"

  # Restore masked phrase with original casing
  stem=$(printf '%s' "$stem" | sed 's/siutils_token/siUtils/g')
  printf '%s' "$stem"
}

# --- Helper: rename safely with collision protection -------------------------
rename_safely() {
  local old_path="$1" new_path="$2"
  [[ "$old_path" == "$new_path" ]] && return 0

  # Collision protection
  if [[ -e "$new_path" ]]; then
    local dir base stem ext i=1
    dir=$(dirname "$new_path")
    base=$(basename "$new_path")
    if [[ "$base" == *.* ]]; then
      stem="${base%.*}"; ext=".${base##*.}"
      [[ "$stem" == "$base" ]] && ext=""
    else
      stem="$base"; ext=""
    fi
    while [[ -e "$dir/${stem}_${i}${ext}" ]]; do ((i++)); done
    new_path="$dir/${stem}_${i}${ext}"
  fi

  if [[ "${DRY_RUN:-}" == "1" ]]; then
    echo "[DRY-RUN] $old_path → $new_path"
  else
    mv -v -- "$old_path" "$new_path"
  fi
}

# --- Helper: snakeify filename (stem + ext) ----------------------------------
snakeify_filename() {
  local base="$1" stem ext
  if [[ "$base" == *.* ]]; then
    stem="${base%.*}"; ext="${base##*.}"
    [[ "$stem" == "$base" ]] && ext=""
  else
    stem="$base"; ext=""
  fi
  stem=$(snakeify_stem "$stem")
  [[ -n "$ext" ]] && printf '%s.%s' "$stem" "$ext" || printf '%s' "$stem"
}

# --- Main logic --------------------------------------------------------------
TARGET_DIR="${1:-.}"
echo ">>> Starting snake_case normalization in: $TARGET_DIR"
[[ "${DRY_RUN:-}" == "1" ]] && echo ">>> DRY-RUN mode enabled"

# --- Load .gitignore patterns from TARGET_DIR (portable, bash 3.2 safe) -----
GITIGNORE_PATTERNS=()  # always initialize (avoids nounset on empty array)
GITIGNORE_FILE="$TARGET_DIR/.gitignore"
if [[ -f "$GITIGNORE_FILE" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    GITIGNORE_PATTERNS+=("$line")
  done < "$GITIGNORE_FILE"
fi

is_gitignored() {
  local path="$1" pattern
  local rel="${path#${TARGET_DIR%/}/}"
  for pattern in "${GITIGNORE_PATTERNS[@]}"; do
    [[ "$rel" == "$pattern" ]] && return 0
    [[ "$rel" == */"$pattern" ]] && return 0
    [[ "$(basename "$rel")" == "$pattern" ]] && return 0
  done
  return 1
}

# --- FILES ------------------------------------------------------------------
find "$TARGET_DIR" -depth \
  \( -path '*/.git*' -o -path '*/.*' -o -path '*/__pycache__*' \) -prune -o \
  -type f ! -name ".DS_Store" -print0 |
while IFS= read -r -d '' f; do
  dir=$(dirname "$f"); base=$(basename "$f")

  # Skip hidden files
  [[ "$base" == .* ]] && continue
  # Skip .gitignored files
  is_gitignored "$f" && continue
  # Skip any file with double-underscores
  [[ "$base" == *__*__* ]] && continue
  # Skip Python bytecode/extensions
  case "$base" in *.pyc|*.pyo|*.pyd) continue ;; esac
  # Skip test-related files
  [[ "$base" == *tst* || "$base" == *Tst* || "$base" == *TST* ]] && continue
  # Skip YAML/YML unless explicitly overridden
  if [[ "${ALLOW_YAML:-0}" -ne 1 ]]; then [[ "$base" == *.ya?ml ]] && continue; fi
  # Compose/Helm/K8s safeties
  case "$base" in
    docker-compose*.yml|docker-compose*.yaml|compose*.yml|compose*.yaml) continue ;;
    Chart.yaml|requirements.yaml|values.yaml|values-*.yaml|*.helmignore) continue ;;
    .env|.gitignore|.gitattributes|Makefile|README.md|LICENSE|pyproject.toml|package.json|requirements.txt) continue ;;
  esac

  newbase=$(snakeify_filename "$base"); newpath="$dir/$newbase"
  rename_safely "$f" "$newpath"
done

# --- DIRECTORIES ------------------------------------------------------------
find "$TARGET_DIR" -depth \
  \( -path '*/.git*' -o -path '*/.*' -o -path '*/__pycache__*' \) -prune -o \
  -type d -print0 |
while IFS= read -r -d '' d; do
  [[ "$d" == "." ]] && continue
  parent=$(dirname "$d"); base=$(basename "$d")
  [[ "$base" == .* ]] && continue
  is_gitignored "$d" && continue
  case "$base" in
    __pycache__|__*__|.git|venv|.venv|node_modules|.pytest_cache|.mypy_cache|.ruff_cache|charts|helm|k8s|kubernetes|manifests|deploy|ops|.github|.gitlab)
      continue ;;
  esac
  newbase=$(snakeify_stem "$base"); newpath="$parent/$newbase"
  rename_safely "$d" "$newpath"
done

echo ">>> Snake-case normalization complete."
[[ "${DRY_RUN:-}" == "1" ]] && echo ">>> (No files were changed — dry run only)"
