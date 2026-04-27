#!/usr/bin/env python3
"""
run.py — Main entry point for research_bot

Usage:
  python run.py                    # Interactive mode (prompts for requirement)
  python run.py "requirement"      # Direct mode (pass requirement as argument)

This script sets up the correct paths and runs the research bot.
"""

import os
import sys

# Ensure we're in the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

# Add core and database to path
sys.path.insert(0, PROJECT_ROOT)

# Import and run research_bot
from core import research_bot

if __name__ == "__main__":
    research_bot.main()
