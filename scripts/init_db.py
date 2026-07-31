#!/usr/bin/env python3
"""Initialize database tables"""
import sys
sys.path.insert(0, '.')

from database import Database

print("Initializing database...")
db = Database()
print("✅ Database tables created!")
print("📁 Location: trading_bot.db")