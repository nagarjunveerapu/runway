# How to Run and Test the Runway Finance App

This guide will help you set up and test the authentication system.

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ and npm installed
- Git (if cloning the repository)

## Test Credentials

After running the setup script, you'll have these credentials:

- **Username**: `testuser`
- **Password**: `testpassword123`
- **Email**: `test@example.com`

## Step-by-Step Setup

### 1. Create Test User in Database

First, let's create a test user in the database:

```bash
cd runway/run_poc
python create_test_user.py
```

This will create a user with:
- Username: testuser
- Email: test@example.com
- Password: testpassword123

### 2. Start the Backend API

**Terminal 1** - Backend Server:

```bash
# Navigate to the backend directory
cd runway/run_poc

# Install Python dependencies (if not already done)
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3. Start the Frontend React App

**Terminal 2** - Frontend Server:

```bash
# Navigate to the frontend directory
cd FIRE/runway-app

# Install npm dependencies (if not already done)
npm install

# Start the React development server
npm start
```

The frontend will automatically open at:
- **Frontend**: http://localhost:3000

You should see output like:
```
Compiled successfully!

You can now view runway-app in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000

Note that the development build is not optimized.
```

### 4. Test the Authentication

#### Test 1: Access Protected Route
1. Open http://localhost:3000 in your browser
2. You should be **automatically redirected to http://localhost:3000/login**
3. This confirms route protection is working

#### Test 2: Login with Test User
1. Enter username: `testuser`
2. Enter password: `testpassword123`
3. Click "Sign In"
4. You should be redirected to the dashboard

#### Test 3: Register a New User
1. Click "Sign up" link on the login page
2. Fill in the form:
   - Username: `myusername` (choose your own)
   - Email: `myemail@example.com`
   - Password: `mypassword123` (at least 8 characters)
   - Confirm Password: `mypassword123`
3. Click "Sign Up"
4. You'll be automatically logged in and redirected to the dashboard

#### Test 4: Test Protected Routes
1. Try accessing different pages (Dashboard, Reports, Settings)
2. All should work without requiring login again
3. Open browser DevTools (F12) and check Application → Local Storage for the token

#### Test 5: Logout and Relogin
1. Click the "Logout" button in the header
2. You should be redirected to login page
3. Enter your credentials and login again

#### Test 6: API Endpoints (Optional)
Test the API directly using curl or Postman:

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "api_test",
    "email": "api@test.com",
    "password": "testpass123"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword123"
  }'
```

This will return a JWT token.

**Get Current User:**
```bash
# Replace YOUR_TOKEN_HERE with the token from login
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Troubleshooting

### Issue: Backend won't start
**Solution:**
```bash
# Make sure you're in the right directory
cd runway/run_poc

# Check Python version
python --version  # Should be 3.8+

# Install dependencies
pip install -r requirements.txt

# Try starting again
python -m uvicorn api.main:app --reload
```

### Issue: Frontend won't start
**Solution:**
```bash
# Make sure you're in the right directory
cd FIRE/runway-app

# Check Node version
node --version  # Should be 16+

# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Try starting again
npm start
```

### Issue: "Module not found" errors
**Solution:**
- For Python: Run `pip install -r requirements.txt` in `runway/run_poc`
- For Node: Run `npm install` in `FIRE/runway-app`

### Issue: Database not found
**Solution:**
```bash
cd runway/run_poc
python create_test_user.py
```

This will create the database and test user.

### Issue: CORS errors in browser console
**Solution:**
Check that the backend is running on `http://localhost:8000` and frontend is on `http://localhost:3000`.

### Issue: Can't login with test credentials
**Solution:**
```bash
cd runway/run_poc
python create_test_user.py
```
This will recreate/update the test user.

## Project Structure

```
runway_workspace/
├── FIRE/
│   └── runway-app/          # React Frontend
│       └── src/
│           ├── context/
│           │   └── AuthContext.jsx
│           └── components/
│               └── Auth/
│                   ├── Login.jsx
│                   ├── Register.jsx
│                   └── ProtectedRoute.jsx
└── runway/
    └── run_poc/              # Python Backend
        ├── api/
        │   └── routes/
        │       └── auth.py
        ├── auth/
        │   ├── jwt.py
        │   ├── password.py
        │   └── dependencies.py
        └── storage/
            └── models.py
```

## Quick Test Checklist

- [ ] Backend server is running (http://localhost:8000)
- [ ] Frontend server is running (http://localhost:3000)
- [ ] Test user created in database
- [ ] Can access /login page
- [ ] Can login with test credentials
- [ ] Can register a new user
- [ ] Can access protected routes after login
- [ ] Logout redirects to login
- [ ] Token stored in localStorage
- [ ] API requests include Authorization header

## Next Steps

After testing the authentication system, you can:
1. Integrate with existing transaction/asset features
2. Add user-specific data filtering
3. Implement user preferences
4. Add profile management
5. Implement password reset functionality

## Support

If you encounter any issues:
1. Check the browser console for errors
2. Check the terminal output for backend errors
3. Verify both servers are running
4. Make sure the database file exists in `runway/run_poc/data/finance.db`
5. Run `python create_test_user.py` again to reset test user

## Environment Variables (Optional)

Create a `.env` file in `runway/run_poc/` for custom configuration:

```env
# Backend .env
JWT_SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=sqlite:///data/finance.db
LOG_LEVEL=INFO
```

Create a `.env` file in `FIRE/runway-app/` for frontend:

```env
# Frontend .env
REACT_APP_API_BASE_URL=http://localhost:8000
```

