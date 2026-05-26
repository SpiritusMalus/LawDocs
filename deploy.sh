#!/bin/bash

set -e

MODE=${1:-full}

case "$MODE" in
  full)
    echo "🔨 Full rebuild (no cache)..."
    dc down
    dc up -d --build
    ;;
  cache)
    echo "⚡ Build with cache..."
    dc down
    dc build
    dc up -d
    ;;
  code)
    echo "🔄 Code restart (no rebuild)..."
    dc down
    dc up -d
    ;;
  *)
    echo "Usage: $0 [full|cache|code]"
    echo ""
    echo "  full   — full rebuild, no cache (default)"
    echo "  cache  — rebuild using Docker layer cache"
    echo "  code   — restart containers without rebuilding"
    exit 1
    ;;
esac

echo "✅ Done."
