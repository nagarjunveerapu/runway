# 🚀 Fresh Start Guide

## Step 1: Kill All Running Processes

Run this in your terminal:

```bash
chmod +x cleanup_all.sh
./cleanup_all.sh
```

Or manually:
```bash
pkill -f "react-scripts"
pkill -f "uvicorn"
lsof -ti:3000 | xargs kill -9
lsof -ti:3001 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

## Step 2: Start Backend First

```bash
cd runway-app-backend
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for: "Application startup complete" in the terminal

Backend should be accessible at: http://localhost:8000/docs

## Step 3: Start Frontend (in a NEW terminal)

```bash
cd runway-app
npm start
```

Frontend should open at: http://localhost:3000

## Step 4: Login

Use these credentials:
- **Email**: test@example.com
- **Password**: testpassword123

## Troubleshooting

If backend won't start:
```bash
cd runway-app-backend
pip install -r requirements.txt
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

If frontend won't start:
```bash
cd runway-app
npm install
npm start
```

If CORS errors persist:
- Restart the backend after the CORS fix
- Check that backend is on port 8000
- Check that frontend is on port 3000




