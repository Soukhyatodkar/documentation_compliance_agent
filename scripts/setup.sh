#!/bin/bash
# ============================================================================
# Documentation Compliance Agent - Setup Script
# ============================================================================
# This script automates the initial setup of the project.
# Usage: bash scripts/setup.sh
# ============================================================================

set -e

echo "=========================================="
echo "Documentation Compliance Agent - Setup"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}[1/6]${NC} Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo -e "${RED}Error: Python 3.11+ required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"
echo ""

# Create virtual environment
echo -e "${YELLOW}[2/6]${NC} Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
echo -e "${YELLOW}[3/6]${NC} Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Install dependencies
echo -e "${YELLOW}[4/6]${NC} Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Install Playwright browsers
echo -e "${YELLOW}[5/6]${NC} Installing Playwright browsers..."
playwright install chromium
echo -e "${GREEN}✓ Playwright browsers installed${NC}"
echo ""

# Set up environment file
echo -e "${YELLOW}[6/6]${NC} Setting up environment configuration..."
if [ -f ".env" ]; then
    echo ".env file already exists"
else
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file (update with your values)${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys and settings"
echo "2. Start Qdrant: docker run -p 6333:6333 qdrant/qdrant:latest"
echo "3. Run validation: python src/main.py validate-config"
echo "4. Run tests: pytest"
echo ""
echo "For more info, see README.md"
echo ""
