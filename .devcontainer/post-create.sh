#!/bin/bash
set -e

echo "🚀 Setting up Bloomy Python development environment..."

# Ensure we're in the workspace directory
cd /workspace

# Install Python dependencies using uv
echo "📦 Installing Python dependencies..."
uv sync --all-extras

# Set up direnv to auto-activate virtual environment
echo "🔧 Setting up direnv for virtual environment activation..."
if [ -f /workspace/.envrc ]; then
    # Check if activation script is already in .envrc
    if ! grep -q "source .venv/bin/activate" /workspace/.envrc; then
        # Add virtual environment activation at the beginning of .envrc
        echo '# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi
' | cat - /workspace/.envrc > /workspace/.envrc.tmp && mv /workspace/.envrc.tmp /workspace/.envrc
        echo "✅ Added virtual environment activation to .envrc"
    else
        echo "✅ Virtual environment activation already configured in .envrc"
    fi
else
    # Create .envrc with virtual environment activation
    echo '# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi
' > /workspace/.envrc
    echo "✅ Created .envrc with virtual environment activation"
fi

# Prompt for GitHub CLI authentication
echo "🔐 GitHub CLI Authentication"
echo "The GitHub CLI (gh) is installed for easy PR creation and repository management."
echo ""
echo -n "Would you like to authenticate with GitHub now? (y/N): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🌐 Opening GitHub authentication in your browser..."
    gh auth login --web
else
    echo "ℹ️  You can authenticate later by running: gh auth login --web"
fi

# Display success message
echo "✅ Development environment setup complete!"
echo ""
echo "🔧 Available commands:"
echo "  - pytest          # Run tests"
echo "  - ruff check .    # Lint code"
echo "  - ruff format .   # Format code"
echo "  - pyright         # Type checking"
echo "  - mkdocs serve    # Serve docs locally"
echo "  - claude          # Use Claude Code for AI-assisted coding"
echo "  - direnv allow    # Allow direnv to load .envrc"
echo "  - gh pr create    # Create a pull request using GitHub CLI"
echo ""

echo "💡 Tips:"
echo "  - The virtual environment will be auto-activated by direnv"
echo "  - Claude Code is installed and available in your PATH"
echo "  - You can configure your API key in .envrc"
echo ""
