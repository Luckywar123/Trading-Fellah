from fastapi import APIRouter, Depends

from backend.auth.siwe import create_nonce, verify_signature_and_login, get_current_user
from backend.models.schemas import NonceRequest, VerifyRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/nonce")
async def request_nonce(body: NonceRequest):
    """Langkah 1: minta nonce buat ditandatangani wallet."""
    return create_nonce(body.wallet)


@router.post("/verify")
async def verify(body: VerifyRequest):
    """Langkah 2: kirim signature, dapet JWT session kalau valid."""
    return verify_signature_and_login(body.wallet, body.signature)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
