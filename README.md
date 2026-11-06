# Air Quality Monitoring of Five Pakistani Cities — ETL + EDA

Complete project: Open-Meteo Air Quality API → raw CSV → Pandas cleaning → Pydantic validation → SQLite/SQLAlchemy → FastAPI → React dashboard. Matplotlib/Seaborn EDA reports are generated from the database.

Cities: Lahore, Islamabad, Rawalpindi, Sialkot, Karachi. Variables: PM10, PM2.5, CO, NO2, SO2, O3.

## Run (Windows)
1. Python 3.10+ and Node.js 18+ required.
2. Backend from project root:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```
API docs: http://127.0.0.1:8000/docs. First startup runs ETL if database is empty.
3. Frontend in a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
4. EDA after data collection:
```powershell
python backend\scripts\run_eda.py
```
Outputs are in `backend/reports/`.

## API
`GET /health`, `GET /api/cities`, `GET /api/summary`, `GET /api/records?city=Lahore`, `GET /api/etl/status`, `POST /api/etl/run`.

## Deploy
Deploy `frontend` to Vercel or Netlify. Build: `npm run build`; output: `dist`. Set `VITE_API_BASE_URL` to the separately deployed FastAPI backend URL. Set backend `FRONTEND_ORIGINS` to your frontend origin. A local SQLite database is not available to a cloud frontend; host the backend with persistent disk or use a managed database for production.

## GitHub
```bash
git init
git add .
git commit -m "Build five-city air quality ETL and EDA"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/air-quality-monitoring.git
git push -u origin main
```

## Interpretation
Open-Meteo air-quality values are model-based estimates, not necessarily direct regulatory monitoring-station readings. This project stores pollutant concentrations, not official AQI scores. API units are preserved. Correlation does not establish causation; boxplot outliers are statistical flags, not automatically data errors.

## Team split
Kainat: API extraction and raw CSV. Eman: GUI and deployment. Shiza: Pandas cleaning, Pydantic validation, SQLAlchemy/SQLite. Maira: EDA, integration, documentation and GitHub coordination.
