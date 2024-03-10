import mimetypes
import os
import re

from dotenv import load_dotenv
from fastapi import HTTPException, status
from supabase import create_client, Client

from app.const.const import FILE_BUCKET_NAME
from app.const import file_output_dir
from app.db.prisma import prisma
from app.service.file.file_service import FileService

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")


class SupabaseService(object):
    _initialized = False
    _instance = None
    supabase: Client
    # pattern: str = r"^(\w|\/|!|-|\*|\'|\(|\)| |&|\$|@|=|;|:|\+|,|\?)*$"
    # pattern: str = r"[!@#$%^&*()\/_=:\+,\?\'\"\[\]\{\}\|\`]"

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._initialized = True
            self.supabase = create_client(url, key)

    def check_file_exists_on_supabase(self, file_path: str, filename: str) -> bool:
        try:
            response = self.supabase.storage.from_(FILE_BUCKET_NAME).list(file_path)
            result = list(filter(lambda x: x.get("name") == filename, response))
            if len(result) == 0:
                return False
            return True
        except Exception as e:
            return False

    def file_upload_on_supabase(
        self,
        tmp_file_path: str,
        output_file_path: str,
        filename: str,
        originFilename: str,
    ):
        try:
            with open(tmp_file_path, "rb") as file:
                mime_type = FileService().get_file_mime_type(tmp_file_path)
                response = (
                    SupabaseService()
                    .supabase.storage.from_(FILE_BUCKET_NAME)
                    .upload(
                        file=file,
                        path=output_file_path,
                        file_options={
                            "content-type": mime_type,
                        },
                    )
                )
                file_size = FileService().get_file_size(tmp_file_path)
                FileService().delete_file(tmp_file_path)

                prisma.file.create(
                    data={
                        "filename": filename,
                        "tmpFilePath": tmp_file_path,
                        "originFilename": originFilename,
                        "filePath": output_file_path,
                        "fileSize": file_size,
                        "contentType": mime_type,
                    }
                )
        except Exception as e:
            print(e)

    def file_upload_on_supabase_private(
        self,
        tmp_file_path: str,
        output_file_path: str,
        filename: str,
        originFilename: str,
        email: str,
        jwt: str,
        tmp_usage_file_path: str = None,
    ):
        try:
            with open(tmp_file_path, "rb") as file:
                mime_type = FileService().get_file_mime_type(tmp_file_path)
                response = (
                    SupabaseService()
                    .supabase.storage.from_(FILE_BUCKET_NAME)
                    .upload(
                        file=file,
                        path=output_file_path,
                        file_options={
                            "content-type": mime_type,
                        },
                    )
                )
                file_size = FileService().get_file_size(tmp_file_path)
                FileService().delete_file(tmp_file_path)

                if tmp_usage_file_path is None:
                    tmp_usage_file_path = tmp_file_path

                prisma.file.create(
                    data={
                        "filename": filename,
                        "tmpFilePath": tmp_usage_file_path,
                        "originFilename": originFilename,
                        "filePath": output_file_path,
                        "fileSize": file_size,
                        "contentType": mime_type,
                        "User": {"connect": {"email": email}},
                    }
                )
        except Exception as e:
            print(e)

    def file_donwload_on_supabase(
        self,
        file_path_include_filename: str,
        filename: str,
        ip: str,
        tmp_file_path: str = None,
    ) -> str:
        tmp_dir = file_output_dir["tmp"]
        if tmp_file_path is None:
            tmp_file_path = f"{tmp_dir}/{filename}"
        target_file_path = file_path_include_filename

        no_content_exception = HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="파일이 존재하지 않습니다.",
        )

        try:
            target_file = prisma.file.find_first(where={"filePath": target_file_path})
            if target_file is None:
                raise no_content_exception

            if target_file.tmpFilePath is not None and os.path.exists(
                target_file.tmpFilePath
            ):
                prisma.downloadlog.create(
                    data={
                        "File": {
                            "connect": {
                                "id": target_file.id,
                            }
                        },
                        "userIP": ip,
                    }
                )
                return target_file.tmpFilePath

            with open(tmp_file_path, "wb+") as f:
                res = self.supabase.storage.from_(FILE_BUCKET_NAME).download(
                    target_file_path
                )
                f.write(res)

            prisma.downloadlog.create(
                data={
                    "File": {
                        "connect": {
                            "id": target_file.id,
                        }
                    },
                    "userIP": ip,
                }
            )
            return tmp_file_path
        except Exception as e:
            print(e)
            raise no_content_exception

    def delete_file_on_supabase(self, file_path: str) -> bool:
        try:
            self.supabase.storage.from_(FILE_BUCKET_NAME).remove(file_path)
            target_file = prisma.file.find_first(where={"filePath": file_path})
            if target_file:
                prisma.file.delete(
                    where={
                        "id": target_file.id,
                    },
                )
            return True
        except Exception as e:
            print(e)
            return False

    def delete_all_file_on_supabase(
        self, file_path_list: list[str], id_list: list
    ) -> bool:
        try:
            self.supabase.storage.from_(FILE_BUCKET_NAME).remove(file_path_list)
            prisma.file.delete_many(where={"id": {"in": id_list}})
            return True
        except Exception as e:
            print(e)
            return False

    # def replace_key_for_validation(self, key: str) -> bool:
    #     return re.sub(self.pattern, "", key)
