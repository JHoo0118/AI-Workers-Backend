import os
import time
import uuid
import aiofiles
import pathlib
import re

from typing import List
from fastapi import UploadFile
from pdf2docx import parse
import prisma
from app.const import *
from app.service.file.file_service import FileService
from app.const.const import FILE_BUCKET_NAME
from app.db.supabase import SupabaseService
from app.db.prisma import prisma
from pdf2docx import Converter
from docx import Document


def replace_text_in_docx(docx_path):
    doc = Document(docx_path)

    for paragraph in doc.paragraphs:
        if "\u0000" in paragraph.text:
            paragraph.text = paragraph.text.replace("\u0000", "")

    doc.save(docx_path)


async def get_pdf_to_word_result(files: List[UploadFile]) -> List[str]:
    try:
        u4 = uuid.uuid4()
        result_list = []
        output_dir = file_output_dir["anon_docx"]
        tmp_dir = file_output_dir["tmp"]

        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        for file in files:
            curr_ms = round(time.time() * 1000)

            input_file_tmp_path = f"{tmp_dir}/{file.filename}"

            async with aiofiles.open(input_file_tmp_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

            output_filename_except_dir = f"converted-{u4}-{curr_ms}.docx"
            tmp_output_file_path = f"{tmp_dir}/{output_filename_except_dir}"
            supabase_output_file_path = f"{output_dir}/{output_filename_except_dir}"

            cv = Converter(input_file_tmp_path)
            cv.convert(tmp_output_file_path)
            cv.close()
            result_list.append(output_filename_except_dir)

            replace_text_in_docx(tmp_output_file_path)

            SupabaseService().file_upload_on_supabase(
                tmp_file_path=tmp_output_file_path,
                output_file_path=supabase_output_file_path,
                filename=output_filename_except_dir,
                originFilename=output_filename_except_dir,
            )

            FileService().delete_file(input_file_tmp_path, missing_ok=True)
            FileService().delete_file(tmp_output_file_path, missing_ok=True)

        print(result_list)
        return result_list

    except FileNotFoundError:
        raise ("해당 파일을 찾을 수 없습니다.")
    except KeyError:
        raise ("올바른 파일인지 확인해 주세요.")
    except UnicodeDecodeError as e:
        raise e
    except Exception:
        pathlib.Path(input_file_tmp_path).unlink(missing_ok=True)
