#!/bin/bash
# Test script for modular frontend

echo "Testing Pi Air Monitor Modular Frontend"
echo "======================================="
echo

# Check if all JavaScript modules exist
echo "Checking JavaScript modules..."
JS_DIR="static/js"
MODULES=("config.js" "utils.js" "charts.js" "hardware.js" "air-quality.js" "app.js")

ALL_EXIST=true
for module in "${MODULES[@]}"; do
    if [ -f "$JS_DIR/$module" ]; then
        echo "✅ $module exists"
    else
        echo "❌ $module missing"
        ALL_EXIST=false
    fi
done

echo
if [ "$ALL_EXIST" = true ]; then
    echo "✅ All JavaScript modules present"
else
    echo "❌ Some modules are missing"
    exit 1
fi

# Check if modular template exists
echo
echo "Checking modular template..."
if [ -f "templates/index_modular.html" ]; then
    echo "✅ index_modular.html exists"
else
    echo "❌ index_modular.html missing"
    exit 1
fi

# Start the Flask app with modular template
echo
echo "Starting Flask app with modular template..."
echo "Access the app at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo

# Activate virtual environment and run with modular flag
source venv/bin/activate
export USE_MODULAR=1
python src/app.py