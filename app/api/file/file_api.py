import os
import pathlib
from typing import Optional

from fastapi import APIRouter, Header, Request
from fastapi.responses import FileResponse
from app.model.file import *
from app.const import file_output_dir
from app.service.file.file_service import FileService
from app.db.supabase import SupabaseService

router = APIRouter(
    prefix="/file",
    tags=["file"],
    dependencies=[],
    responses={404: {"description": "찾을 수 없습니다."}},
)


@router.get(
    "/exist",
    response_model=IsExistFileOutputs,
    summary="존재하는 파일인지 확인",
    description="파일명과 파일 확장자를 입력 받아서 존재하는 파일인지 확인합니다.",
    response_description="isExist가 true면 존재하고, false이면 존재하지 않는 파일입니다.",
)
async def is_exist_file(filename: str, email: str = None) -> IsExistFileOutputs:
    fileType = FileService().get_file_extension(filename)
    if email is None:
        fileType = "anon_" + fileType

    isExist = SupabaseService().check_file_exists_on_supabase(
        file_path=file_output_dir[fileType], filename=filename
    )

    return IsExistFileOutputs(isExist=isExist)


@router.get("/download/{filename}")
async def file_download(
    request: Request, filename: str, email: str = None
) -> FileResponse:
    fileType = FileService().get_file_extension(filename)
    if email is None:
        fileType = "anon_" + fileType
    tmp_file_path = SupabaseService().file_donwload_on_supabase(
        file_path_include_filename=f"{file_output_dir[fileType]}/{filename}",
        filename=filename,
        ip=request.client.host,
    )
    mime_type = FileService().get_file_mime_type(tmp_file_path)

    return FileResponse(
        tmp_file_path,
        media_type=mime_type,
        filename=filename,
    )


@router.delete("/public/delete/{filename}")
async def file_delete(filename: str, email: str = None) -> bool:
    fileType = FileService().get_file_extension(filename)
    if email is None:
        fileType = "anon_" + fileType
    tmp_file_path = f'{file_output_dir["tmp"]}/{filename}'
    FileService().delete_file(file_path=tmp_file_path)
    return SupabaseService().delete_file_on_supabase(
        f"{file_output_dir[fileType]}/{filename}",
    )
