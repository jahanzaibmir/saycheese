#!/bin/bash
# SayCheese - Launch Script
# Developed by Jahanzaib Ashraf Mir

echo " SayCheese Camera Application"
echo " By Jahanzaib Ashraf Mir"
echo "================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo " Python3 is not installed. Please install it first."
    exit 1
fi

# Run the application
python3 saycheese.py
