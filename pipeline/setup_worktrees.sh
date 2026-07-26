#!/usr/bin/env bash
# Git worktree setup for Maxwell OS v2.0
# =======================================
# Enables parallel work on multiple branches without cloning.
#
# Usage:
#   bash pipeline/setup_worktrees.sh
#
# Creates:
#   main/            → main branch (stable)
#   phase0-fixes/    → phase0/fix-foundation branch (current work)
#   experiments/     → experimental branch

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Maxwell OS — Git Worktree Setup ==="
echo "Repo: $REPO_ROOT"
echo ""

# 1. Ensure we're on main
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Currently on '$CURRENT_BRANCH'. Switching to main..."
    git checkout main 2>/dev/null || true
fi

# 2. Create phase0 branch if it doesn't exist
if ! git show-ref --verify --quiet refs/heads/phase0/fix-foundation; then
    echo "🌿 Creating phase0/fix-foundation branch..."
    git branch phase0/fix-foundation
else
    echo "✅ phase0/fix-foundation branch exists"
fi

# 3. Create worktrees (parallel working directories)
WORKTREE_DIR="$REPO_ROOT/../maxwell-worktrees"
mkdir -p "$WORKTREE_DIR"

for branch in main phase0/fix-foundation; do
    wt_name=$(echo "$branch" | tr '/' '-')
    wt_path="$WORKTREE_DIR/$wt_name"

    if [ -d "$wt_path" ]; then
        echo "✅ Worktree exists: $wt_path ($branch)"
    else
        echo "🌿 Creating worktree: $wt_path → $branch"
        git worktree add "$wt_path" "$branch"
    fi
done

echo ""
echo "=== Worktrees ready ==="
git worktree list
echo ""
echo "Usage:"
echo "  cd $WORKTREE_DIR/phase0-fix-foundation  # Active development"
echo "  cd $WORKTREE_DIR/main                    # Stable reference"
echo ""
echo "  # To remove a worktree:"
echo "  git worktree remove $WORKTREE_DIR/phase0-fix-foundation"
