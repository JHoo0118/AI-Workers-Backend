from io import BytesIO
import os
import time
import uuid

from typing import List
from fastapi import UploadFile
from pypdf import PdfWriter, PdfReader
from app.const import *
from app.db.supabase import SupabaseService
from app.const.const import FILE_BUCKET_NAME
from app.db.prisma import prisma

from app.service.file.file_service import FileService


def get_pdf_split_result(
    start_page_number: str, end_page_number: str, files: List[UploadFile]
) -> str:
    start_page = int(start_page_number) - 1
    end_page = int(end_page_number) - 1
    tmp_dir = file_output_dir["tmp"]
    output_dir = file_output_dir["anon_pdf"]

    # for file in files:
    file = files[0]

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    curr_ms = round(time.time() * 1000)
    u4 = uuid.uuid4()

    filename = f"splitted-{u4}-{curr_ms}.pdf"
    try:
        tmp_file_path = f"{tmp_dir}/{filename}"
        output_file_path = f"{output_dir}/{filename}"
        reader = PdfReader(file.file)
        writer = PdfWriter()
        if start_page == end_page:
            writer.add_page(reader.pages[start_page])
        else:
            for page_num in range(start_page, end_page + 1):
                writer.add_page(reader.pages[page_num])
        writer.write(tmp_file_path)
        writer.close()

        SupabaseService().file_upload_on_supabase(
            tmp_file_path=tmp_file_path,
            output_file_path=output_file_path,
            filename=filename,
            originFilename=filename,
        )
        return filename
    except:
        FileService().delete_file(tmp_file_path)
