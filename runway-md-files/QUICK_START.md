# 🚀 Quick Start Guide - Runway Finance Authentication

## ✅ Test User Credentials

The test user has been created in the database. Use these credentials to login:

```
Username: testuser
Password: testpassword123
Email: test@example.com
```

---

## 📋 How to Run the Application

### Step 1: Start the Backend API

Open **Terminal 1** and run:

```bash
cd /Users/karthikeyaadhya/runway_workspace/runway/run_poc
python3 -m uvicorn api.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

✅ Backend is running at: **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

### Step 2: Start the Frontend React App

Open **Terminal 2** and run:

```bash
cd /Users/karthikeyaadhya/runway_workspace/FIRE/runway-app
npm install  # Only needed first time
npm start
```

You should see:
```
Compiled successfully!
You can now view runway-app in the browser:
  Local:   http://localhost:3000
```

✅ Frontend is running at: **http://localhost:3000**

---

## 🧪 Testing the Authentication

### Test 1: Login with Test User
1. Open browser: http://localhost:3000
2. You'll be redirected to: http://localhost:3000/login
3. Enter credentials:
   - Username: `testuser`
   - Password: `testpassword123`
4. Click "Sign In"
5. You should see the dashboard! ✨

### Test 2: Register New User
1. Click "Sign up" link on login page
2. Fill the form:
   - Username: `myuser123`
   - Email: `myemail@example.com`
   - Password: `mypass123` (8+ characters)
   - Confirm Password: `mypass123`
3. Click "Sign Up"
4. Automatically logged in! 🎉

### Test 3: Verify Protected Routes
- Navigate through Dashboard, Reports, Settings
- All pages should work
- Check browser DevTools → Application → Local Storage
- You'll see the JWT token stored

### Test 4: Logout
- Click "Logout" button in header
- Redirected to login page
- Re-login works perfectly

---

## 🔧 Troubleshooting

### Backend won't start?
```bash
cd /Users/karthikeyaadhya/runway_workspace/runway/run_poc
pip3 install -r requirements.txt
python3 -m uvicorn api.main:app --reload
```

### Frontend won't start?
```bash
cd /Users/karthikeyaadhya/runway_workspace/FIRE/runway-app
npm install
npm start
```

### Can't login with test user?
Reset the database:
```bash
cd /Users/karthikeyaadhya/runway_workspace/runway/run_poc
python3 reset_and_setup.py
```

### CORS errors?
Make sure backend is on port 8000 and frontend on port 3000.

---

## 📱 Screenshots of What You'll See

**Login Page:**
- Beautiful gradient background
- Username and password fields
- "Sign In" button

**Dashboard:**
- Header with Runway logo
- Logout button in top right
- Bottom navigation with Home, Reports, Add buttons

---

## 🎯 Success Checklist

- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:3000
- [ ] Can access /login page
- [ ] Can login with testuser credentials
- [ ] Can register a new user
- [ ] Can access protected routes
- [ ] Logout works and redirects to login

---

## 📚 Additional Resources

- Full documentation: `AUTHENTICATION_IMPLEMENTATION.md`
- Test guide: `HOW_TO_RUN_AND_TEST.md`
- API docs: http://localhost:8000/docs

---

## 🆘 Need Help?

If you encounter issues:
1. Check terminal output for errors
2. Check browser console (F12) for JavaScript errors
3. Verify both servers are running
4. Make sure database exists at `runway/run_poc/data/finance.db`

---

## 🎉 You're All Set!

Login Credentials:
- **Username**: testuser
- **Password**: testpassword123

Happy testing! 🚀

