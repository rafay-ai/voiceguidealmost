# DEBUGGING LOGIN/SIGNUP ISSUE - Step by Step Guide

## Current Situation
- Backend running on `http://localhost:8001`
- Frontend running on `http://localhost:3000`
- MongoDB has data (50 orders, users, restaurants, menu items)
- Login/signup hangs with loading spinner
- No errors in console or backend terminal

---

## STEP 1: Check if Backend is Accessible

**Test 1: Health Check**
```bash
# In browser, go to:
http://localhost:8001/api/health

# Expected Response:
{"status":"healthy","timestamp":"2025-11-09T..."}

# If this doesn't work, backend is not accessible from browser
```

**Test 2: Register Endpoint with curl**
```bash
# In PowerShell/CMD:
curl -X POST http://localhost:8001/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"testuser123\",\"email\":\"test@test.com\",\"password\":\"test123\"}'

# Expected: Should return JSON with token and user data
# If this works but browser doesn't, it's a frontend issue
```

---

## STEP 2: Check Browser Network Tab

1. Open your browser (where frontend is running)
2. Press **F12** to open DevTools
3. Click **Network** tab
4. Clear all requests (trash icon)
5. Try to signup again
6. Look for a request to `/auth/register` or similar

**What to check:**
- **Is the request sent?** If not, frontend code issue
- **Request URL**: Should be `http://localhost:8001/api/auth/register`
- **Status**: 
  - `(pending)` = Request stuck, not reaching backend
  - `200` = Success but response not handled
  - `500` = Backend error
  - `CORS error` = CORS configuration issue
- **Response tab**: What does the response say?

**Screenshot this and share with me!**

---

## STEP 3: Check Frontend .env Configuration

**Your current frontend/.env:**
```env
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=3000
WDS_SOCKET_HOST=localhost
```

This looks correct! ✅

---

## STEP 4: Check Backend .env Configuration

**Your backend/.env should have:**
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=voice_guide
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=AIzaSyAFRdyWUYGyaYO78vSw4iMwxd
```

**Check CORS_ORIGINS** - it should be `http://localhost:3000` exactly!

---

## STEP 5: Test MongoDB Connection

**In PowerShell:**
```powershell
# Connect to MongoDB
mongosh

# Switch to voice_guide database
use voice_guide

# Check if collections exist
show collections

# Count users
db.users.countDocuments()

# Count orders
db.orders.countDocuments()

# Exit
exit
```

---

## STEP 6: Add Logging to See What's Happening

**Option A: Check Backend Terminal During Signup**

When you click signup, you should see in backend terminal:
```
INFO: 127.0.0.1:xxxxx - "POST /api/auth/register HTTP/1.1" 200 OK
```

If you DON'T see this, the request is not reaching the backend!

**Option B: Add Console Log in Frontend**

1. Open `frontend/src/components/RegisterPage.js` (or similar)
2. Find the signup function
3. Add console.log at the start:

```javascript
const handleSubmit = async (e) => {
  e.preventDefault();
  console.log('🔵 SIGNUP STARTED');
  console.log('Backend URL:', process.env.REACT_APP_BACKEND_URL);
  
  setIsLoading(true);
  setError('');
  
  try {
    console.log('🔵 Sending request...');
    const response = await axios.post(`${process.env.REACT_APP_BACKEND_URL}/api/auth/register`, {
      username,
      email,
      password
    });
    console.log('🟢 Response received:', response);
    // ... rest of code
```

This will show you where it's stuck!

---

## STEP 7: Common Issues and Solutions

### Issue 1: Request Not Sent
**Symptom:** No network request in DevTools
**Cause:** Form validation preventing submit
**Solution:** Check form validation logic

### Issue 2: Request Pending Forever
**Symptom:** Request shows "(pending)" in Network tab
**Cause:** Backend not responding or wrong URL
**Solution:** 
- Check backend is running
- Check URL in .env
- Try curl to test backend directly

### Issue 3: CORS Error
**Symptom:** Console shows CORS error
**Cause:** CORS_ORIGINS not configured correctly
**Solution:** Update backend/.env:
```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Issue 4: 500 Internal Server Error
**Symptom:** Status 500 in Network tab
**Cause:** Backend error (check backend terminal)
**Solution:** Look at backend logs for error details

### Issue 5: MongoDB Connection Failed
**Symptom:** Backend terminal shows MongoDB connection error
**Cause:** MongoDB not running or wrong connection string
**Solution:** 
- Check MongoDB is running: `net start MongoDB`
- Or start manually: `"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath="C:\data\db"`

---

## STEP 8: Quick Test - Bypass Frontend

**Test registration directly from browser:**

1. Open browser console (F12 → Console tab)
2. Paste this code:

```javascript
fetch('http://localhost:8001/api/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'testuser' + Date.now(),
    email: 'test' + Date.now() + '@test.com',
    password: 'test123'
  })
})
.then(res => {
  console.log('Status:', res.status);
  return res.json();
})
.then(data => console.log('Response:', data))
.catch(err => console.error('Error:', err));
```

3. Press Enter
4. Check what it says

**If this works**, the issue is in your React code!
**If this fails**, the issue is backend/network!

---

## STEP 9: Check if MongoDB Service is Actually Running

**In PowerShell (as Administrator):**
```powershell
Get-Service -Name MongoDB
```

**Should show:**
```
Status   Name               DisplayName
------   ----               -----------
Running  MongoDB            MongoDB
```

**If it's "Stopped":**
```powershell
Start-Service MongoDB
```

---

## STEP 10: Last Resort - Check Firewall

**Windows Firewall might be blocking localhost connections:**

1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Check "Inbound Rules" for any rule blocking port 8001
4. Or temporarily disable firewall to test:
   - Control Panel → Windows Defender Firewall
   - Turn Windows Defender Firewall off (just for testing!)

---

## What to Do Next

**Please do these tests in order:**

1. ✅ Test: Can you access `http://localhost:8001/api/health` in browser?
2. ✅ Test: Run the curl command for register
3. ✅ Test: Check Network tab during signup
4. ✅ Test: Run the JavaScript fetch test from browser console
5. ✅ Share results with me!

**Most Likely Issues:**
1. **Backend not accessible** - Check if health endpoint works
2. **MongoDB not running** - Check service status
3. **Wrong environment variable** - Check REACT_APP_BACKEND_URL
4. **CORS blocking** - Check backend/.env CORS_ORIGINS

Once you share the results of these tests, I can pinpoint the exact issue! 🔍
