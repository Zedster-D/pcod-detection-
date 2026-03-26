# PCOD Detection Backend (FastAPI)

## Endpoints
- `POST /api/assessments`
  - Creates/saves a patient assessment and returns `score`, `risk level`, `factors`, and `recommendations`.
- `GET /api/doctor/patients`
  - Returns each patient's latest assessment summary (for a simple doctor dashboard).
- `GET /api/assessments/{assessment_id}`
  - Fetch a saved assessment.

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Database
SQLite file is created automatically as `backend/app.db` on first run.

