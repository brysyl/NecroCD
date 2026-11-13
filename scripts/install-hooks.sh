#!/usr/bin/env bash
# Install NecroCD git hooks (pre-commit and post-merge).
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HOOKS="$(git rev-parse --git-path hooks)"
mkdir -p "$HOOKS"
install_hook() {
  local name="$1" script="$2"
  cat > "$HOOKS/$name" <<EOF
#!/usr/bin/env bash
exec python3 "$ROOT/.kiro/hooks/$script" "\$@"
EOF
  chmod +x "$HOOKS/$name"
  echo "Installed $name -> .kiro/hooks/$script"
}
install_hook pre-commit pre-commit-exorcism.py
install_hook post-merge post-merge-exorcism.py
