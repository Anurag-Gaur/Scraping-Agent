@echo off
REM ═════════════════════════════════════════════════════════════════════════
REM PostgreSQL Setup Script for Windows PowerShell
REM ═════════════════════════════════════════════════════════════════════════
REM
REM This script automates the setup of PostgreSQL migration:
REM   1. Installs psycopg2-binary dependency
REM   2. Creates the database table
REM   3. Migrates existing agent data
REM
REM Usage:
REM   .\setup_postgres.bat
REM
REM ═════════════════════════════════════════════════════════════════════════

echo.
echo ════════════════════════════════════════════════════════════════
echo   PostgreSQL Migration Setup
echo ════════════════════════════════════════════════════════════════
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python first.
    exit /b 1
)

echo [1/3] Installing psycopg2-binary...
pip install psycopg2-binary>=2.9.0
if errorlevel 1 (
    echo [ERROR] Failed to install psycopg2-binary
    exit /b 1
)
echo [✓] psycopg2-binary installed

echo.
echo [2/3] Creating PostgreSQL table schema...
python pg_store.py create
if errorlevel 1 (
    echo [ERROR] Failed to create table. Check your database connection.
    exit /b 1
)
echo [✓] Table created

echo.
echo [3/3] Migrating existing agent data...
python seed_postgres.py
if errorlevel 1 (
    echo [WARN] Migration completed with some errors. Check the output above.
)
echo [✓] Migration complete

echo.
echo ════════════════════════════════════════════════════════════════
echo   Setup Complete!
echo ════════════════════════════════════════════════════════════════
echo.
echo Next steps:
echo   • Verify setup: python pg_store.py list
echo   • Run research bot: python research_bot.py "your requirement"
echo   • Check stored agents: python pg_store.py stats
echo.
echo ════════════════════════════════════════════════════════════════
echo.
pause
