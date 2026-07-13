#!/bin/bash
set -e
VERSION="3.0"
HOME_DIR="${TOKEN_SAVER_HOME:=$HOME/.token_saver}"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"; }
command -v python3 >/dev/null || { log 'Python 3 not found'; exit 1; }
mkdir -p "$HOME_DIR"/{logs,backup,data}
chmod 700 "$HOME_DIR"

if [ -d "$HOME_DIR/token_saver/.git" ]; then
  git -C "$HOME_DIR/token_saver" pull --ff-only || log 'Update skipped; existing checkout unchanged'
elif [ -e "$HOME_DIR/token_saver" ]; then
  log "Refusing to overwrite non-git path: $HOME_DIR/token_saver"; exit 1
else
  git clone https://github.com/GlacierEQ/token_saver.git "$HOME_DIR/token_saver"
fi

cd "$HOME_DIR/token_saver"
# Runtime uses Python standard-library modules only; there is no dependency install step.
python3 token_saver_elite_cli.py help >/dev/null
log "TOKEN_SAVER v$VERSION installed and CLI verified"
log "Try: python3 $HOME_DIR/token_saver/token_saver_elite_cli.py health"
