import base64
import hashlib


def encode_base64(input: bytes, charset: str = "utf-8") -> str:
    file_bytes = base64.encodebytes(input)
    return str(file_bytes, charset)


def calculate_md5(input: bytes) -> str:
    return hashlib.md5(input).hexdigest()
