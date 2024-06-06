import logging

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api
from app.db.prisma import prisma
from app.middleware import RouterLoggingMiddleware

from app.db.supabase import SupabaseService

from app.middleware.ai_middleware import AIMiddleware
from app.service.scheduler.scheduler_service import SchedulerService


load_dotenv()

SupabaseService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        prisma.connect()
        SchedulerService().start()
        yield
    finally:
        prisma.disconnect()


app = FastAPI(lifespan=lifespan)
# app.add_middleware(
#     RouterLoggingMiddleware,
#     logger=logging.getLogger(__name__),
# )
allow_origins = [
    "http://localhost:3000",
    "https://smartaiworkers.com",
    "https://www.smartaiworkers.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AIMiddleware)


@app.get("/")
def read_root():
    return {"version": "1.0.0"}


app.include_router(api, prefix="/api")
