@echo off
echo Starting MindCare AI Application in Production Mode...
echo.

REM Set environment variables
set DATABASE_URL=sqlite:///mindcare.db
set SESSION_SECRET=mindcare-secret-key-2024-production
set PYTHONPATH=%CD%
set FLASK_ENV=production

echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting the application...
python run.py

pause