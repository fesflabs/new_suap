import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string

from .s3 import TemporaryS3Storage, MediaS3Storage, PrivateS3Storage, upload_temporary_s3, download_temporary_content_s3
from .storage import TemporaryFileSystemStorage, FileSystemStoragePlus, PrivateFileSystemStorage

__all__ = [
    "is_remote_storage",
    "assure_path_exists",
    "get_private_storage",
    "get_temp_storage",
    "get_overwrite_storage",
    "cache_file",
    "download_media_content",
    "upload_temporary_file",
    "download_temporary_content",
    "copy_file",
    "move_file",
]


def is_remote_storage():
    return settings.DEFAULT_FILE_STORAGE == "djtools.storages.s3.MediaS3Storage"


def assure_path_exists(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def get_private_storage():
    if is_remote_storage():
        return PrivateS3Storage()
    return PrivateFileSystemStorage()


def get_temp_storage():
    if is_remote_storage():
        return TemporaryS3Storage()
    return TemporaryFileSystemStorage()


def get_overwrite_storage():
    if is_remote_storage():
        storage = MediaS3Storage()
    else:
        storage = FileSystemStoragePlus()
    storage.file_overwrite = True
    return storage


def cache_file(remote_filename, local_filename=None, force=False, random_local_filename=False):
    if not local_filename:
        local_filename = remote_filename
        if random_local_filename:
            ext = remote_filename.split(".")[-1]
            local_filename = f"tmp{get_random_string()}.{ext}"
    full_local_filename = os.path.join(settings.TEMP_DIR, local_filename)
    if remote_filename and default_storage.exists(remote_filename):
        storage = TemporaryFileSystemStorage()
        storage.file_overwrite = True
        if not storage.exists(local_filename) or force:
            with default_storage.open(remote_filename, "rb") as remote_file:
                cleaned_name = storage.save(local_filename, remote_file)
                full_local_filename = os.path.join(settings.TEMP_DIR, cleaned_name)
    return full_local_filename


def download_media_content(relative_remote_path):
    try:
        with default_storage.open(relative_remote_path, "rb") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return None


def upload_temporary_file(file_path):
    if is_remote_storage():
        return upload_temporary_s3(file_path)
    return file_path


def download_temporary_content(file_path):
    if is_remote_storage():
        return download_temporary_content_s3(file_path)
    with open(file_path, "rb") as f:
        content = f.read()
    return content


def copy_file(original_relative_path, new_relative_path):
    default_storage.save(new_relative_path, default_storage.open(original_relative_path))


def move_file(original_relative_path, new_relative_path):
    copy_file(original_relative_path, new_relative_path)
    default_storage.delete(original_relative_path)
