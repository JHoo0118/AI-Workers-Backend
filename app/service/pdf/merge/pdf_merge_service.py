import os
import time
import uuid

from typing import List
from fastapi import UploadFile
from pypdf import PdfWriter
from app.const import *
from app.db.supabase import SupabaseService
from app.const.const import FILE_BUCKET_NAME
from app.db.prisma import prisma

from app.service.file.file_service import FileService


def get_pdf_merge_result(files: List[UploadFile]) -> str:
    merger = PdfWriter()
    tmp_dir = file_output_dir["tmp"]
    output_dir = file_output_dir["anon_pdf"]

    for pdf in files:
        merger.append(pdf.file)

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    curr_ms = round(time.time() * 1000)
    u4 = uuid.uuid4()

    filename = f"merged-{u4}-{curr_ms}.pdf"
    try:
        tmp_file_path = f"{tmp_dir}/{filename}"
        output_file_path = f"{output_dir}/{filename}"
        merger.write(tmp_file_path)
        merger.close()

        SupabaseService().file_upload_on_supabase(
            tmp_file_path=tmp_file_path,
            output_file_path=output_file_path,
            filename=filename,
            originFilename=filename,
        )
        return filename
    except:
        FileService().delete_file(tmp_file_path)
