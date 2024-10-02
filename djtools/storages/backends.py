import os
import uuid
from io import FileIO, BufferedWriter

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.files.temp import NamedTemporaryFile

from .utils import assure_path_exists

__all__ = ['AbstractUploadBackend', 'LocalUploadBackend', 'AWSUploadBackend', 'AWSMultipartUploadBackend']


class AbstractUploadBackend(object):
    BUFFER_SIZE = 64 * 2 ** 10

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def setup(self, filename, *args, **kwargs):
        """Responsible for doing any pre-processing needed before the upload
        starts."""

    def update_filename(self, request, filename, *args, **kwargs):
        """Returns a new name for the file being uploaded."""

    def upload_chunk(self, chunk, *args, **kwargs):
        """Called when a string was read from the client, responsible for
        writing that string to the destination file."""
        raise NotImplementedError

    def upload_complete(self, request, filename, *args, **kwargs):
        """Overriden to performs any actions needed post-upload, and returns
        a dict to be added to the render / json context"""

    def upload_on_stage_area(self, uploaded, content_length, raw_data):
        image_temp = NamedTemporaryFile(delete=True)
        bytes_written = 0

        try:
            if raw_data:
                # File was uploaded via ajax, and is streaming in.
                chunk = uploaded.read(self.BUFFER_SIZE)
                while len(chunk) > 0:
                    bytes_written += len(chunk)
                    image_temp.write(chunk)
                    chunk = uploaded.read(self.BUFFER_SIZE)
            else:
                # File was uploaded via a POST, and is here.
                for chunk in uploaded.chunks():
                    image_temp.write(chunk)
        except Exception as e:
            # things went badly.
            print(("Things went badly: ", str(e)))
            return False
        image_temp.flush()
        if content_length == bytes_written:
            return File(image_temp)
        return None

    def upload(self, uploaded, content_length, raw_data, *args, **kwargs):
        bytes_written = 0
        try:
            if raw_data:
                # File was uploaded via ajax, and is streaming in.
                chunk = uploaded.read(self.BUFFER_SIZE)
                while len(chunk) > 0:
                    bytes_written += len(chunk)
                    self.upload_chunk(chunk, *args, **kwargs)
                    chunk = uploaded.read(self.BUFFER_SIZE)
            else:
                # File was uploaded via a POST, and is here.
                for chunk in uploaded.chunks():
                    self.upload_chunk(chunk, *args, **kwargs)
        except Exception as e:
            # things went badly.
            print(('Arquivo Upload: things went badly: {}.'.format(e)))
            return False
        #
        if content_length == bytes_written:
            return True
        # The upload was canceled by user
        # so delete it
        if hasattr(self, '_filepath'):
            os.remove(self._filepath)
        return False


class LocalUploadBackend(AbstractUploadBackend):
    def setup(self, relative_upload_path, filename, overwriter=False):
        self._absolute_path = os.path.join(settings.MEDIA_ROOT, relative_upload_path)
        assure_path_exists(self._absolute_path)
        if not overwriter:
            filename = self._filepath = self.assure_unique_filename(filename)
        #
        self._filepath = os.path.join(self._absolute_path, filename)
        self._dest = BufferedWriter(FileIO(self._filepath, "w"))

    def upload_chunk(self, chunk, *args, **kwargs):
        self._dest.write(chunk)

    def upload_complete(self, *args, **kwargs):
        self._dest.close()
        # Note: a relative path to the settings.MEDIA_ROOT
        # is returned by this function
        relative_path = os.path.relpath(self._filepath, settings.MEDIA_ROOT)
        return relative_path

    def assure_unique_filename(self, filename):
        """
        Returns a new name for the file being uploaded.
        Ensure file with name doesn't exist, and if it does,
        create a unique filename to avoid overwriting
        """
        extension = os.path.splitext(filename)[1]
        unique_filename = str(uuid.uuid4())
        return unique_filename + (extension or '')


class AWSUploadBackend(AbstractUploadBackend):
    def setup(self, relative_upload_path, filename, overwriter=False):
        self.full_path = f'{relative_upload_path}/{filename}'

    def upload(self, uploaded, content_length, raw_data, *args, **kwargs):
        bytes_written = 0
        import io
        bytes_io = io.BytesIO()
        try:
            if raw_data:
                # File was uploaded via ajax, and is streaming in.
                chunk = uploaded.read(self.BUFFER_SIZE)
                while len(chunk) > 0:
                    bytes_written += len(chunk)
                    bytes_io.write(chunk)
                    chunk = uploaded.read(self.BUFFER_SIZE)
            else:
                # File was uploaded via a POST, and is here.
                for chunk in uploaded.chunks():
                    bytes_io.write(chunk)
        except Exception as e:
            # things went badly.
            print(('Arquivo Upload: things went badly: {}.'.format(e)))
            return False

        if content_length == bytes_written:
            self.final_filename = default_storage.save(self.full_path, bytes_io)
            return True
        return False

    def upload_complete(self, *args, **kwargs):
        return self.final_filename


class AWSMultipartUploadBackend(AbstractUploadBackend):
    def setup(self, relative_upload_path, filename, overwriter=False):
        import boto3
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.client = session.resource(
            's3',
            use_ssl=True,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        ).meta.client
        self.full_path = f'{relative_upload_path}/{self.assure_unique_filename(filename)}'
        self.response_client = self.client.create_multipart_upload(
            Bucket=settings.AWS_MEDIA_BUCKET_NAME,
            Key=self.full_path,
        )
        self.response_chunks = []
        self.part_number = 0

    def upload_chunk(self, chunk, *args, **kwargs):
        self.part_number += 1
        response = self.client.upload_part(
            Body=chunk,
            Bucket=settings.AWS_MEDIA_BUCKET_NAME,
            Key=self.full_path,
            PartNumber=self.part_number,
            UploadId=self.response_client['UploadId'],
        )
        dic = {
            'ETag': response['ETag'],
            'PartNumber': self.part_number
        }
        self.response_chunks.append(dic)

    def upload_complete(self, *args, **kwargs):
        part_info = {
            'Parts': self.response_chunks
        }
        self.client.complete_multipart_upload(
            Bucket=settings.AWS_MEDIA_BUCKET_NAME,
            Key=self.full_path,
            UploadId=self.response_client['UploadId'],
            MultipartUpload=part_info
        )
        return self.full_path

    def assure_unique_filename(self, filename):
        """
        Returns a new name for the file being uploaded.
        Ensure file with name doesn't exist, and if it does,
        create a unique filename to avoid overwriting
        """
        extension = os.path.splitext(filename)[1]
        unique_filename = str(uuid.uuid4())
        return unique_filename + (extension or '')
