# Runway Finance - Project Setup Guide

## Project Structure

The project has been restructured into two main directories:

```
runway_workspace/
├── runway-app/                  # Frontend React Application
└── runway-app-backend/          # Backend FastAPI Application
```

## Quick Start

### Option 1: Start Both Services (Recommended)

```bash
./start_all.sh
```

This will start:
- Backend API at `http://localhost:8000`
- Frontend at `http://localhost:3000`

### Option 2: Start Services Separately

#### Start Backend Only
```bash
./start_backend.sh
```
Backend runs at: `http://localhost:8000`

#### Start Frontend Only
```bash
./start_frontend.sh
```
Frontend runs at: `http://localhost:3000`

## Manual Setup (if scripts don't work)

### Backend Setup

```bash
cd runway-app-backend

# Create virtual environment (if not exists)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd runway-app

# Install dependencies (if not already installed)
npm install

# Start the development server
npm start
```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Features

### Backend (`runway-app-backend`)
- FastAPI REST API
- ML-powered transaction categorization
- Investment optimizer
- Salary sweep automation
- Loan prepayment calculator
- Net worth tracking
- FIRE calculator

### Frontend (`runway-app`)
- React-based modern UI
- Transaction management
- Analytics dashboards
- Investment optimizer
- Portfolio tracking
- Wealth management

## Database

The database file is located at:
- `runway-app-backend/data/finance.db`

## Default Test Users

1. **test@example.com** / password: `test123`
2. **test2@example.com** / password: `test123`

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use
- Ensure Python 3.8+ is installed
- Check that all dependencies are installed

### Frontend won't start
- Check if port 3000 is already in use
- Run `npm install` in the runway-app directory
- Check Node.js version (18+ recommended)

### API connection issues
- Verify backend is running on port 8000
- Check browser console for CORS errors
- Ensure API base URL is `http://localhost:8000`


