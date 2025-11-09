#!/bin/bash

# Voice Guide - Local Setup Script
# This script helps you set up the project on your laptop

echo "🚀 Voice Guide - Local Setup"
echo "=============================="
echo ""

# Colors for output
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "${RED}❌ Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo "📋 Checking prerequisites..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "${RED}❌ Python 3 is not installed${NC}"
    echo "   Please install Python 3.11+ from https://www.python.org/"
    exit 1
else
    PYTHON_VERSION=$(python3 --version)
    echo "${GREEN}✅ $PYTHON_VERSION${NC}"
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "${RED}❌ Node.js is not installed${NC}"
    echo "   Please install Node.js 16+ from https://nodejs.org/"
    exit 1
else
    NODE_VERSION=$(node --version)
    echo "${GREEN}✅ Node.js $NODE_VERSION${NC}"
fi

# Check Yarn
if ! command -v yarn &> /dev/null; then
    echo "${YELLOW}⚠️  Yarn is not installed. Installing...${NC}"
    npm install -g yarn
else
    YARN_VERSION=$(yarn --version)
    echo "${GREEN}✅ Yarn $YARN_VERSION${NC}"
fi

# Check MongoDB
if ! command -v mongod &> /dev/null; then
    echo "${YELLOW}⚠️  MongoDB is not installed or not in PATH${NC}"
    echo "   Please install MongoDB from https://www.mongodb.com/try/download/community"
    echo "   You can continue setup and install MongoDB later"
else
    echo "${GREEN}✅ MongoDB installed${NC}"
fi

echo ""
echo "📦 Setting up Backend..."
echo ""

# Backend setup
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=voice_guide
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
EOF
    echo "${YELLOW}⚠️  Please edit backend/.env and add your GEMINI_API_KEY${NC}"
else
    echo "${GREEN}✅ .env file exists${NC}"
fi

cd ..

echo ""
echo "📦 Setting up Frontend..."
echo ""

# Frontend setup
cd frontend

# Install dependencies
echo "Installing Node dependencies..."
yarn install

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "${YELLOW}⚠️  .env file not found. Creating for local development...${NC}"
    cat > .env << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
WDS_SOCKET_HOST=localhost
EOF
    echo "${GREEN}✅ Created .env for local development${NC}"
else
    echo "${GREEN}✅ .env file exists${NC}"
fi

cd ..

echo ""
echo "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Make sure MongoDB is running:"
echo "   ${YELLOW}mongod${NC}"
echo ""
echo "2. Add your Gemini API key to backend/.env"
echo ""
echo "3. Start the backend (in one terminal):"
echo "   ${YELLOW}cd backend${NC}"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo "   ${YELLOW}uvicorn server:app --host 0.0.0.0 --port 8001 --reload${NC}"
echo ""
echo "4. Start the frontend (in another terminal):"
echo "   ${YELLOW}cd frontend${NC}"
echo "   ${YELLOW}yarn start${NC}"
echo ""
echo "5. Open your browser to:"
echo "   ${GREEN}http://localhost:3000${NC}"
echo ""
echo "📱 To access from mobile (same WiFi):"
echo "   1. Find your laptop IP: ${YELLOW}ifconfig | grep inet${NC}"
echo "   2. Update frontend/.env: ${YELLOW}REACT_APP_BACKEND_URL=http://YOUR_IP:8001${NC}"
echo "   3. Access from mobile: ${GREEN}http://YOUR_IP:3000${NC}"
echo ""
echo "Need help? Check README.md for detailed instructions!"
echo ""
