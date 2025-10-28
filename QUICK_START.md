# 🚀 Quick Start Guide - Runway Finance

## Your project has been restructured. Here's how to start it:

### Project Structure:
```
runway_workspace/
├── runway-app/              # Frontend (React)
└── runway-app-backend/      # Backend (FastAPI)
```

## Starting the Application

### Step 1: Start Backend API

```bash
cd runway-app-backend
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Backend will be available at:** http://localhost:8000

### Step 2: Start Frontend (in a new terminal)

```bash
cd runway-app
npm start
```

**Frontend will be available at:** http://localhost:3000

## Access Points

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Default Test Users

You can login with:
- Email: `test@example.com` / Password: `test123`
- Email: `test2@example.com` / Password: `test123`

## Troubleshooting

### If backend won't start:
```bash
cd runway-app-backend
pip install -r requirements.txt
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### If frontend won't start:
```bash
cd runway-app
npm install
npm start
```

### Port already in use:
Change the port in the command:
- Backend: `--port 8001` (instead of 8000)
- Frontend: Edit `package.json` or use `PORT=3001 npm start`

## What's Included

### Backend Features
- ✅ Transaction management
- ✅ ML-powered categorization
- ✅ Investment optimizer (with Indian Clearing Corp support)
- ✅ Credit card payment detection
- ✅ Salary sweep optimizer
- ✅ Loan prepayment calculator
- ✅ Net worth tracking

### Frontend Features
- ✅ Modern React UI
- ✅ Investment Optimizer page
- ✅ Transaction analytics
- ✅ Portfolio tracking
- ✅ All optimizers

## Database Location
`runway-app-backend/data/finance.db`

---

**Created startup scripts:**
- `start_backend.sh` - Start backend only
- `start_frontend.sh` - Start frontend only  
- `start_all.sh` - Start both services


