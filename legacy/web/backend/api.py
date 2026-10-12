"""FastAPI Backend"""
from fastapi import FastAPI
import asyncio
from datetime import datetime, timezone

app = FastAPI(title="Aggressive Sniper Bot v3.0 API", version="3.0.0")

trading_engine = None

@app.get("/api/health")
async def health_check():
    return {"status": "online", "version": "3.0.0"}

@app.get("/api/dashboard/overview")
async def get_overview():
    if not trading_engine:
        return {
            "equity": 100.0, "daily_pnl": 0.0, "win_rate": 0.0,
            "active_positions": [], "trade_count_today": 0,
            "system_status": "INITIALIZING", "mode": "PAPER"
        }
    return {
        "equity": trading_engine.equity,
        "daily_pnl": trading_engine.daily_pnl,
        "win_rate": trading_engine.calculate_win_rate(),
        "active_positions": trading_engine.active_positions,
        "system_status": "RUNNING" if trading_engine.is_running else "STOPPED",
        "mode": trading_engine.mode,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ... existing code ...

@app.post("/api/trades/open")
async def open_trade(order: OrderRequest):
    """Manually open a trade from web"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=503, detail="Trading engine not ready")
    
    try:
        # Calculate SL/TP if not provided
        entry_price = order.entry_price
        if not order.stop_loss:
            # Auto-calculate SL based on 10 pips
            pip_value = 0.0001 if "JPY" not in order.symbol else 0.00001
            if order.direction == "LONG":
                order.stop_loss = entry_price - (10 * pip_value)
            else:
                order.stop_loss = entry_price + (10 * pip_value)
        
        # Execute via engine
        order_dict = order.dict()
        result = await trading_engine.execute_manual_order(order_dict)
        
        # Log to database
        if db:
            db.save_trade(result)
        
        return {"success": True, "order": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/trades/close/{position_id}")
async def close_trade(position_id: str, reason: str = "MANUAL"):
    """Close position from web"""
    global trading_engine
    
    if not trading_engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
    
    position = next((p for p in trading_engine.active_positions 
                     if p.get("order_id") == position_id), None)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Get current price (would need live feed)
    current_price = position.get("entry_price", 0)
    result = await trading_engine.close_position(position, current_price, reason)
    
    return {"success": True, "result": result}

@app.get("/api/database/trades")
async def get_trades_db(limit: int = 100, symbol: str = None):
    """Get trades from database"""
    if not db:
        return []
    return db.get_trades(limit, symbol)

# ... rest of API ...