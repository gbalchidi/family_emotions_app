#!/bin/bash

# Family Emotions App Setup Script

set -e

echo "🚀 Setting up Family Emotions App..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Create logs directory
mkdir -p logs

# Setup pre-commit hooks (if in development)
if [ "$1" = "--dev" ]; then
    echo "🔧 Setting up development tools..."
    pre-commit install
    echo "✅ Development environment ready!"
else
    echo "✅ Production environment ready!"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Start PostgreSQL and Redis"
echo "3. Run migrations: python src/main.py --mode migrate"
echo "4. Start the app: python src/main.py"
echo ""
echo "For development:"
echo "- Run with dev tools: ./scripts/setup.sh --dev"
echo "- Use docker-compose: docker-compose --profile dev up"
echo ""