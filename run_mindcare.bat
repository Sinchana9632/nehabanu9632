@echo off
echo Starting MindCare AI Application...
echo.

REM Set environment variables
set DATABASE_URL=sqlite:///mindcare.db
set SESSION_SECRET=mindcare-secret-key-2024
set PYTHONPATH=%CD%

echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting the application...
python main.py

pause