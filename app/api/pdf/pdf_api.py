import os
import time
import uuid
from fastapi import APIRouter
from starlette.responses import FileResponse
from app.model import *
from app.const import *

router = APIRouter(
    prefix="/pdf",
    tags=["pdf"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)
