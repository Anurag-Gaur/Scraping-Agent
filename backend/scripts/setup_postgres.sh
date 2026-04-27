#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════
# PostgreSQL Setup Script for Linux/Mac
# ═════════════════════════════════════════════════════════════════════════
#
# This script automates the setup of PostgreSQL migration:
#   1. Installs psycopg2-binary dependency
#   2. Creates the database table
#   3. Migrates existing agent data
#
# Usage:
#   chmod +x setup_postgres.sh
#   ./setup_postgres.sh
#
# ═════════════════════════════════════════════════════════════════════════

set -e

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  PostgreSQL Migration Setup"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python first."
    exit 1
fi

echo "[1/3] Installing psycopg2-binary..."
pip install 'psycopg2-binary>=2.9.0'
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install psycopg2-binary"
    exit 1
fi
echo "[✓] psycopg2-binary installed"

echo ""
echo "[2/3] Creating PostgreSQL table schema..."
python3 pg_store.py create
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create table. Check your database connection."
    exit 1
fi
echo "[✓] Table created"

echo ""
echo "[3/3] Migrating existing agent data..."
python3 seed_postgres.py
if [ $? -ne 0 ]; then
    echo "[WARN] Migration completed with some errors. Check the output above."
fi
echo "[✓] Migration complete"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  • Verify setup: python3 pg_store.py list"
echo "  • Run research bot: python3 research_bot.py 'your requirement'"
echo "  • Check stored agents: python3 pg_store.py stats"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
