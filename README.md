# Voice Guide - Food Ordering Platform

A modern, AI-powered food ordering platform with intelligent recommendations using Gemini embeddings and enhanced chatbot with bilingual support (English & Urdu).

## Features

✨ **Enhanced Recommendations**
- Gemini embeddings-based similarity matching
- Order history analysis (past 30 days)
- Strict dietary restriction enforcement (vegetarian, vegan, halal, gluten-free)
- Personalized scoring based on preferences and order patterns

🤖 **Intelligent Chatbot**
- Intent detection (food recommendation, reorder, new items, specific cuisine, etc.)
- Bilingual support (English & Urdu)
- Context-aware conversations (no loops)
- Restaurant cards display after recommendations

🍽️ **Smart Features**
- Reorder favorite items with one tap
- Discover new items based on taste profile
- Cuisine-specific recommendations
- Spice level matching

## Tech Stack

**Backend:**
- FastAPI (Python 3.11)
- MongoDB with Motor (async)
- Google Gemini 2.0 Flash (embeddings & chat)
- Scikit-learn for additional ML features

**Frontend:**
- React 18
- Tailwind CSS
- Axios for API calls
- Responsive design for mobile

## Running on Your Laptop

### Prerequisites
- Python 3.11+
- Node.js 16+ and Yarn
- MongoDB 4.4+
- Gemini API Key

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the `backend` directory:
   ```env
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=voice_guide
   CORS_ORIGINS=http://localhost:3000
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   ```

5. **Start MongoDB:**
   ```bash
   # On macOS:
   brew services start mongodb-community

   # On Linux:
   sudo systemctl start mongod

   # On Windows:
   net start MongoDB
   ```

6. **Run the backend:**
   ```bash
   uvicorn server:app --host 0.0.0.0 --port 8001 --reload
   ```

   Backend will be available at: `http://localhost:8001`
   API docs at: `http://localhost:8001/docs`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   yarn install
   ```

3. **Set up environment variables:**
   Create a `.env` file in the `frontend` directory:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8001
   WDS_SOCKET_PORT=3000
   WDS_SOCKET_HOST=localhost
   ```

   **Note:** This configuration fixes the WebSocket connection errors you were seeing!

4. **Start the frontend:**
   ```bash
   yarn start
   ```

   Frontend will be available at: `http://localhost:3000`

## Running on Mobile Phone

### Option 1: Same WiFi Network (Easiest)

1. **Find your laptop's IP address:**
   ```bash
   # On macOS/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1

   # On Windows:
   ipconfig
   ```

2. **Update frontend .env:**
   ```env
   REACT_APP_BACKEND_URL=http://YOUR_LAPTOP_IP:8001
   ```

3. **Start both servers** (backend on 8001, frontend on 3000)

4. **Access from mobile browser:**
   Open your mobile browser and navigate to:
   ```
   http://YOUR_LAPTOP_IP:3000
   ```

   Example: `http://192.168.1.100:3000`

### Option 2: ngrok (For Remote Access)

1. **Install ngrok:**
   ```bash
   # Download from: https://ngrok.com/download
   ```

2. **Start backend and frontend locally**

3. **Create ngrok tunnels:**
   ```bash
   # Terminal 1 - Backend tunnel
   ngrok http 8001

   # Terminal 2 - Frontend tunnel
   ngrok http 3000
   ```

4. **Update frontend .env with ngrok backend URL:**
   ```env
   REACT_APP_BACKEND_URL=https://your-backend-url.ngrok.io
   ```

5. **Access the ngrok frontend URL from your mobile**

## Troubleshooting

### WebSocket Errors in Console
The errors `WebSocket connection to 'ws://localhost:443/ws' failed` are from React's hot-reload feature and are **NORMAL**. They don't affect your app functionality. To minimize these:

1. Make sure `.env` has:
   ```env
   WDS_SOCKET_PORT=3000
   WDS_SOCKET_HOST=localhost
   ```

2. Or add to `package.json`:
   ```json
   "start": "DANGEROUSLY_DISABLE_HOST_CHECK=true react-scripts start"
   ```

### Backend Won't Start
- Check MongoDB is running
- Verify Python version: `python --version` (should be 3.11+)
- Reinstall dependencies: `pip install -r requirements.txt`

### Frontend Won't Load
- Clear browser cache
- Delete `node_modules` and `yarn.lock`, then run `yarn install`
- Check backend is running on port 8001
- Verify `.env` has correct `REACT_APP_BACKEND_URL`

### Mobile Can't Connect
- Make sure laptop and phone are on same WiFi network
- Check firewall isn't blocking ports 3000 and 8001
- Try accessing `http://YOUR_LAPTOP_IP:8001/api/health` from mobile browser first
- Use `0.0.0.0` instead of `localhost` when starting servers

## Key Improvements

### From Previous Version:
1. **No more loops** - Context tracking prevents conversation loops
2. **Better recommendations** - Embeddings-based similarity matching
3. **Strict dietary restrictions** - Vegetarians won't see meat items
4. **Restaurant cards** - See restaurant details with recommendations
5. **Bilingual support** - Proper Urdu language detection and responses
6. **Order history integration** - Smart reorder suggestions
7. **Mobile-friendly** - Responsive design works on all screen sizes
