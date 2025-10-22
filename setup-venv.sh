#!/bin/bash
# Setup script for creating virtual environment and installing dependencies

echo "Creating Python virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the BLE server:"
echo "  source venv/bin/activate"
echo "  sudo venv/bin/python3 src/ble-server.py"
echo ""
echo "To deactivate the virtual environment:"
echo "  deactivate"
