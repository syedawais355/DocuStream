from fastapi import Depends, HTTPException, Header
from config import get_settings


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key
