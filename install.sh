#!/usr/bin/env bash
# KShield installer — curl -fsSL https://get.kshield.dev | bash
set -euo pipefail

REPO="YTTGlobalServices/kshield"
VERSION="${KSHIELD_VERSION:-latest}"
INSTALL_DIR="${KSHIELD_INSTALL_DIR:-/usr/local/bin}"

# ── Colours ───────────────────────────────────────────────────────────────────
BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

info()  { echo -e "  ${GREEN}✓${RESET}  $1"; }
warn()  { echo -e "  ${YELLOW}!${RESET}  $1"; }
error() { echo -e "  ${RED}✗${RESET}  $1" >&2; exit 1; }
step()  { echo -e "  ${CYAN}→${RESET}  $1"; }

echo ""
echo -e "${BOLD}${CYAN}  KShield  ·  Installer${RESET}"
echo ""

# ── Platform detection ────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin) OS_LABEL="apple-darwin" ;;
  Linux)  OS_LABEL="unknown-linux-gnu" ;;
  *)      error "Unsupported OS: $OS. Build from source: https://github.com/$REPO" ;;
esac

case "$ARCH" in
  x86_64)        ARCH_LABEL="x86_64" ;;
  arm64|aarch64) ARCH_LABEL="aarch64" ;;
  *)             error "Unsupported architecture: $ARCH" ;;
esac

PLATFORM="${ARCH_LABEL}-${OS_LABEL}"
step "Detected: $OS $ARCH"

# ── Resolve version ───────────────────────────────────────────────────────────
if [ "$VERSION" = "latest" ]; then
  step "Fetching latest release..."
  VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')"
  [ -z "$VERSION" ] && error "Could not determine latest version. Set KSHIELD_VERSION manually."
fi

info "Installing kshield $VERSION"

# ── Download ──────────────────────────────────────────────────────────────────
TARBALL="kshield-${PLATFORM}.tar.gz"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$VERSION/$TARBALL"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

step "Downloading $TARBALL..."
if ! curl -fsSL --progress-bar "$DOWNLOAD_URL" -o "$TMP_DIR/$TARBALL"; then
  error "Download failed: $DOWNLOAD_URL\n\n  If releases aren't published yet, build from source:\n    git clone https://github.com/$REPO && cd $REPO/cli && cargo build --release"
fi

# ── Install ───────────────────────────────────────────────────────────────────
tar -xzf "$TMP_DIR/$TARBALL" -C "$TMP_DIR"
BINARY="$TMP_DIR/kshield"
[ -f "$BINARY" ] || error "Binary not found in tarball"

# Try the requested install dir; fall back to ~/.local/bin if not writable
if [ -w "$INSTALL_DIR" ] || sudo -n true 2>/dev/null; then
  if [ ! -w "$INSTALL_DIR" ]; then
    sudo mv "$BINARY" "$INSTALL_DIR/kshield"
    sudo chmod +x "$INSTALL_DIR/kshield"
  else
    mv "$BINARY" "$INSTALL_DIR/kshield"
    chmod +x "$INSTALL_DIR/kshield"
  fi
else
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR"
  mv "$BINARY" "$INSTALL_DIR/kshield"
  chmod +x "$INSTALL_DIR/kshield"
  warn "Installed to $INSTALL_DIR (no sudo). Add it to PATH if needed:"
  warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

info "Installed to $INSTALL_DIR/kshield"

# ── PATH check ────────────────────────────────────────────────────────────────
if ! command -v kshield &>/dev/null; then
  warn "kshield is not yet in your PATH."
  warn "Add this to your shell profile (~/.zshrc or ~/.bashrc):"
  echo ""
  echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
  echo ""
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}  Done!${RESET}  Run this inside any git repo to get started:"
echo ""
echo -e "    ${BOLD}kshield init${RESET}"
echo ""
echo -e "  ${CYAN}→${RESET}  Docs:   https://github.com/$REPO"
echo -e "  ${CYAN}→${RESET}  Issues: https://github.com/$REPO/issues"
echo ""
