import os
import mimetypes
import pathlib
import math
import uuid
import time
import shutil

from app.service.crypto.crypto_service import CryptoService


class FileService(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def get_file_extension(self, filename: str) -> str:
        splitted = filename.split(".")
        if len(splitted) == 1:
            return ""
        return splitted[-1]

    def get_file_size(self, file_path: str, suffix: str = "B"):
        file_stats = os.stat(file_path)
        bytes = file_stats.st_size
        magnitude = int(math.floor(math.log(bytes, 1024)))
        val = bytes / math.pow(1024, magnitude)
        if magnitude > 7:
            return "{:.1f}{}{}".format(val, "Y", suffix)
        return "{:3.1f}{}{}".format(
            val, ["", "K", "M", "G", "T", "P", "E", "Z"][magnitude], suffix
        )

    def get_file_mime_type(self, file_path: str) -> str:
        ext = self.get_file_extension(file_path)
        if ext == "docx":
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == "rtf":
            return "application/octet-stream"
        elif ext == "txt":
            return "text/plain"

        return mimetypes.guess_type(file_path)[0]

    def delete_file(self, file_path: str, missing_ok: bool = False) -> bool:
        try:
            pathlib.Path(file_path).unlink(missing_ok=missing_ok)
            return True
        except FileNotFoundError:
            return False

    def get_converted_filename(self, suffix: str, filename: str) -> str:
        u4 = uuid.uuid4()
        curr_ms = round(time.time() * 1000)
        suffix = f"{suffix}-{u4}-{curr_ms}"
        file_extension = self.get_file_extension(filename=filename)
        return f"{suffix}.{file_extension}"

    def delete_dir_with_contents(self, path: str):
        dir_path = pathlib.Path(path)
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)
