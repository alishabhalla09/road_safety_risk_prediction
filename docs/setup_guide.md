# ROADGUARD AI — Developer Setup & Deployment Guide

## System Requirements
- **OS:** Windows 10/11, Ubuntu 22.04+, or macOS
- **Python:** 3.10 or higher
- **Node.js:** v18.0.0 or higher
- **Docker:** Docker Desktop or Docker Engine with Docker Compose v2

---

## Local Development Setup

### 1. Backend Setup
```bash
# Navigate to project root
cd roadguard-ai

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies in editable mode with dev options
pip install -e .[dev]

# Set environment variables
cp .env.example .env

# Run FastAPI server
python -m uvicorn backend.app.main:app --reload --port 8000
```
API Documentation will be accessible at: `http://localhost:8000/docs`

---

### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Dependencies
npm install

# Start Vite Development Server
npm run dev
```
Dashboard UI will be accessible at: `http://localhost:5173`

---

## Docker Compose Deployment

To build and run the entire stack (PostgreSQL + FastAPI + React Frontend) in containers:

```bash
docker-compose up --build -d
```

Services exposed:
- **Frontend Dashboard:** http://localhost:5173
- **FastAPI Backend:** http://localhost:8000
- **PostgreSQL Database:** localhost:5432

---

## Running Tests & Quality Checks

```bash
# Run Unit and API Integration Tests
pytest

# Run Ruff Code Quality & Format Linter
ruff check .
```
