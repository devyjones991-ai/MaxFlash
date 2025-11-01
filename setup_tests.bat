@echo off
REM Setup script for Windows

echo Installing test dependencies...
pip install pytest pytest-cov pytest-mock

echo Running tests...
python -m pytest tests/ -v

echo Tests completed!
pause
