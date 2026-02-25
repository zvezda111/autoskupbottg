import asyncio
import os
import signal
import tempfile
import uuid

from datetime import datetime, timedelta
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
import random
from app.api.config import API_KEY
from app.bot.main import handle_archive_logic
from app.db.database import AsyncSessionLocal
from app.services.db_services import get_stats, get_or_create_user, request_withdrawal
import uvicorn
app = FastAPI()


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db



@app.get("/api/wd/{telegram_id}")
async def wd(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):

    user = await get_or_create_user(db, telegram_id, "")
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(
            db,
            telegram_id,
            user.username or ""
        )
        amount = user.balance
        if amount <= 0:
            return {
                "text": f"У вас нет средств для вывода.",
            }
        w = await request_withdrawal(db, user, amount)

        return {
            "text": f"Запрос на вывод {amount}₽ создан (ID {w.id}).",
        }
@app.get("/api/profile/{telegram_id}")
async def profile(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    user = await get_or_create_user(db, telegram_id, "")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now     = datetime.utcnow()
    periods = [
        ("сегодня",   now - timedelta(days=1)),
        ("неделю",     now - timedelta(weeks=1)),
        ("30 дней",    now - timedelta(days=30)),
        ("всё время",  datetime(2000,1,1)),
    ]
    stats = []
    for label, since in periods:
        count, breakdown = await get_stats(db, user.id, since)
        stats.append({
            "period":    label,
            "count":     count,
            "breakdown": breakdown
        })

    return {
        "telegram_id": user.telegram_id,
        "username":    user.username,
        "balance":     float(user.balance),
        "stats":       stats
    }

@app.post("/api/upload")
async def upload(
    telegram_id: int,
    username:    str,
    number:         str, #number
    user_id:        str, #future_token
    sb:             bool,
    twoFA:          str,
    file:        UploadFile = File(None),
    db:          AsyncSession = Depends(get_db)
):
    user = await get_or_create_user(db, telegram_id, username)
    print(number)
    print(number)
    print(user_id)
    try:
        token_bytes = bytes.fromhex(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid HEX token format")
    if file:
        
        try:
            
            temp_dir = tempfile.mkdtemp()
            archive_path = os.path.join(temp_dir, file.filename)

            with open(archive_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            batch_id = str(str(random.randint(10000, 99999)) + '-' + str(random.randint(10000, 99999)))
            result = await handle_archive_logic(archive_path=archive_path, user_data=user, batch_id=batch_id, type_u='API', token=token_bytes, twoFA= twoFA,number= number,spamblock=sb)
            return result
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {e}")
            
        finally:
            if os.path.exists(archive_path):
                os.remove(archive_path)

            os.rmdir(temp_dir)
    elif not file:

        batch_id = str(str(random.randint(10000, 99999)) + '-' + str(random.randint(10000, 99999)))
        result = await handle_archive_logic(None, user, batch_id, 'API', number, twoFA, user_id,sb)
        return result
        
     
            


from app.bot.src.session_cloner import *

async def main():
    os.makedirs("logs_api", exist_ok=True)
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)

    asyncio.create_task(queue_worker())
    await server.serve()

if __name__ == '__main__':
    asyncio.run(main())
