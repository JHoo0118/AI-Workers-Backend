from fastapi import APIRouter
from app.api.pdf import pdfRouter as pdfRouter
from app.api.file import fileRouter as fileRouter
from app.api.ai import aiRouter as aiRouter
from app.api.auth import authRouter as authRouter
from app.api.user import userRouter as userRouter

api = APIRouter()
api.include_router(pdfRouter)
api.include_router(fileRouter)
api.include_router(aiRouter)
api.include_router(authRouter)
api.include_router(userRouter)

__all__ = ["api"]
