import os
import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv

load_dotenv()

aes_key = base64.b64decode(os.getenv("AES_KEY"))
aes_iv = base64.b64decode(os.getenv("AES_IV"))


class CryptoService(object):
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)

        return class_._instance

    def encrypt_data(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")

        cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        padded_data = pad(data, AES.block_size)
        encrypted_bytes = cipher.encrypt(padded_data)

        return base64.b64encode(encrypted_bytes).decode("utf-8")

    def decrypt_data(self, encrypted_data):
        encrypted_bytes = base64.b64decode(encrypted_data)

        cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
        padded_data = cipher.decrypt(encrypted_bytes)
        decrypted_data = unpad(padded_data, AES.block_size)

        return decrypted_data.decode("utf-8")
