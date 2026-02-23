#!/usr/bin/env bash
set -e

# Default installation directory
DEFAULT_INSTALL_DIR="$HOME/.config/crush/skills"
SKILL_NAME="autogitlog"

# Parse arguments
INSTALL_DIR="${DEFAULT_INSTALL_DIR}"
SHOW_HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            SHOW_HELP=true
            shift
            ;;
    esac
done

if [ "$SHOW_HELP" = true ]; then
    cat << EOF
Usage: ./install.sh [OPTIONS]

Install the autogitlog Crush skill.

Options:
  -d, --dir DIR    Installation directory (default: ~/.config/crush/skills)
  -h, --help       Show this help message

Examples:
  ./install.sh                           # Install to default location
  ./install.sh -d ~/.config/crush/skills # Install globally
  ./install.sh -d ./my-agent/skills      # Install to specific agent

The skill will be installed at: <DIR>/autogitlog/
EOF
    exit 0
fi

# Determine source directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SCRIPT_DIR}/${SKILL_NAME}"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory not found: ${SOURCE_DIR}"
    echo "This script should be run from the root of the autogitlog repository."
    exit 1
fi

# Create installation directory if it doesn't exist
TARGET_DIR="${INSTALL_DIR}/${SKILL_NAME}"
mkdir -p "$INSTALL_DIR"

# Check if target already exists
if [ -d "$TARGET_DIR" ]; then
    echo "Warning: ${TARGET_DIR} already exists."
    read -p "Do you want to overwrite it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    rm -rf "$TARGET_DIR"
fi

# Copy the skill
echo "Installing autogitlog skill..."
cp -r "$SOURCE_DIR" "$TARGET_DIR"

# Make scripts executable
chmod +x "${TARGET_DIR}/scripts"/*.py 2>/dev/null || true

echo "✓ Successfully installed to: ${TARGET_DIR}"
echo ""
echo "Next steps:"
echo "  1. Ensure you have Python 3, Git, and Crush installed"
echo "  2. Ask your agent: 'Set up auto git log for <directory>'"
echo ""
echo "For more information, see README.md"
