"""
Database Handler - SQLite (dev) or PostgreSQL (prod)
"""
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create tables if not exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trade History
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL,
                exit_price REAL,
                pnl REAL,
                exit_reason TEXT,
                confidence REAL,
                trailing_active BOOLEAN DEFAULT 0,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP
            )
        ''')
        
        # Equity Curve
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equity_curve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                equity REAL NOT NULL,
                daily_pnl REAL,
                cumulative_pnl REAL
            )
        ''')
        
        # AI Predictions Log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                prediction_type TEXT,
                confidence REAL,
                result TEXT
            )
        ''')
        
        # System Logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def save_trade(self, trade: Dict):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades 
            (order_id, symbol, direction, size, entry_price, stop_loss, 
             take_profit, exit_price, pnl, exit_reason, confidence,
             trailing_active, opened_at, closed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.get('order_id'),
            trade.get('symbol'),
            trade.get('direction'),
            trade.get('size'),
            trade.get('entry_price'),
            trade.get('stop_loss'),
            trade.get('take_profit'),
            trade.get('exit_price'),
            trade.get('pnl'),
            trade.get('exit_reason'),
            trade.get('confidence'),
            1 if trade.get('trailing_active') else 0,
            trade.get('opened_at'),
            trade.get('closed_at') or datetime.now(timezone.utc).isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_trades(self, limit: int = 100, symbol: Optional[str] = None):
        """Get trade history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?"
        params = [limit]
        
        if symbol:
            query = "SELECT * FROM trades WHERE symbol = ? ORDER BY opened_at DESC LIMIT ?"
            params = [symbol, limit]
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0], 'order_id': r[1], 'symbol': r[2],
            'direction': r[3], 'size': r[4], 'entry_price': r[5],
            'stop_loss': r[6], 'take_profit': r[7], 'exit_price': r[8],
            'pnl': r[9], 'exit_reason': r[10], 'confidence': r[11],
            'trailing_active': bool(r[12]), 'opened_at': r[13], 'closed_at': r[14]
        } for r in rows]
    
    def log_system(self, level: str, message: str, details: str = None):
        """Log system event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_logs (level, message, details)
            VALUES (?, ?, ?)
        ''', (level, message, details))
        
        conn.commit()
        conn.close()
    
    def log_ai_prediction(self, symbol: str, prediction_type: str, 
                          confidence: float, result: str):
        """Log AI prediction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_predictions (symbol, prediction_type, confidence, result)
            VALUES (?, ?, ?, ?)
        ''', (symbol, prediction_type, confidence, result))
        
        conn.commit()
        conn.close()

# Singleton instance
db = Database()