#!/bin/bash
# Setup script for UAE Corporate Intelligence Hub

echo "🚀 Setting up UAE Corporate Intelligence Hub..."

# Create project-specific virtual environment
VENV_NAME="intelligence-hub-env"

echo "📦 Creating virtual environment: $VENV_NAME"
python -m venv "$VENV_NAME"

# Activate virtual environment (for Unix/MacOS)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    echo "🔌 Activating virtual environment (Windows)..."
    source "$VENV_NAME/Scripts/activate"
else
    echo "🔌 Activating virtual environment (Unix/MacOS)..."
    source "$VENV_NAME/bin/activate"
fi

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "🗄️ Initializing database..."
python scripts/init_db.py

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  Windows: $VENV_NAME\Scripts\activate && python main.py"
echo "  Unix/MacOS: source $VENV_NAME/bin/activate && python main.py"
