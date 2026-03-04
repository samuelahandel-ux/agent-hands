#!/bin/bash
# Run AgentHands in development mode

cd "$(dirname "$0")/.."

# Create data directory if needed
mkdir -p data

# Install dependencies if needed
if ! pip show fastapi > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Install Playwright browsers if needed
if ! playwright --version > /dev/null 2>&1; then
    echo "Installing Playwright..."
    pip install playwright
    playwright install chromium
fi

echo "🤖 Starting AgentHands API..."
uvicorn src.main:app --reload --port 8080
