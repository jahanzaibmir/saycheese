#!/bin/bash
echo "🧀 Setting up SayCheese Camera Application..."
echo "👨‍💻 Developed by Jahanzaib Ashraf Mir"
echo "================================================"

# Update system
echo "🔄 Updating system packages..."
sudo apt update

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libx264-dev \
    libasound2-dev \
    v4l-utils

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install opencv-python PyQt5

# Create desktop shortcut (optional)
echo "🎯 Creating desktop shortcut..."
cat > ~/Desktop/SayCheese.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SayCheese
Comment=Fun Camera Application
Exec=python3 $(pwd)/saycheese.py
Icon=camera
Terminal=false
Categories=Graphics;
EOF

chmod +x ~/Desktop/SayCheese.desktop

echo "✅ Setup complete!"
echo ""
echo "🎉 SayCheese is ready to use!"
echo "📁 Photos/Videos will be saved to: ~/Pictures/SayCheese/"
echo ""
echo "🚀 Run the application with:"
echo "   python3 saycheese.py"
echo "   OR"
echo "   chmod +x run_saycheese.sh && ./run_saycheese.sh"
echo ""
echo "📖 Check README.md for more information"
