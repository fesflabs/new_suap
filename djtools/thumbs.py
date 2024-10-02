# -*- encoding: utf-8 -*-

"""
Inspirado em http://code.google.com/p/django-thumbs/
Melhorias:
- redimensionamento da imagem
- guarda os thumbs em pastas separadas para cada tamanho
- opção use_id_for_name
"""
import io
import tempfile

from PIL import Image, ImageOps
from django.core.signing import Signer
from django.db.models import ImageField
from django.db.models.fields.files import ImageFieldFile
import os


EXIF_ORIENTATION = 0x0112


class ImageWithThumbsFieldFile(ImageFieldFile):
    """
    See ImageWithThumbsField for usage example
    """

    def __init__(self, *args, **kwargs):
        super(ImageWithThumbsFieldFile, self).__init__(*args, **kwargs)

        if self.field.sizes:
            for size in self.field.sizes:
                setattr(self, 'url_%sx%s' % size, self.get_thumb_url(size))

    @property
    def url(self):
        if not self:
            return ''
        return self.storage.url(self.name)

    def get_thumb_url(self, size):
        if not self:
            return ''
        splited = list(os.path.split(self.name))
        splited.insert(-1, '%dx%d' % size)
        relative_path = os.path.join(*splited)
        return self.field.storage.url(relative_path)

    def save(self, name, content, save=True):
        extension = name.split('.')[-1]
        if self.field.use_id_for_name:
            string_randomica = Signer(salt='extra-salt').sign(self.instance.id).split(':')[1][:12]
            name = '%s.%s.%s' % (self.instance.id, string_randomica, extension)
        super().save(name, content, save)
        if self.field.sizes:
            for size in self.field.sizes:
                thumb_dir = os.path.join(self.field.upload_to, '%dx%d' % size)
                file_name = os.path.join(self.field.upload_to, name)

                with self.field.storage.open(file_name) as f:
                    content = io.BytesIO(f.read())

                imin = Image.open(content)
                code = imin.getexif().get(EXIF_ORIENTATION, 1)

                if code and code != 1:
                    imin = ImageOps.exif_transpose(imin)

                width, height = imin.size
                nwidth = (height / 4) * 3
                x = (width - nwidth) / 2
                if x > 0:
                    imout = imin.crop((x, 0, width - x, height))
                else:
                    imout = imin.crop((0, 0, width, height))
                imout = imout.resize(size)
                thumb_file = os.path.join(thumb_dir, name)
                imout = imout.convert("RGB")
                tmp = tempfile.NamedTemporaryFile(suffix=f'.{extension}')
                imout.save(tmp)
                tmp.seek(0)
                self.field.storage.save(thumb_file, tmp)
                tmp.close()

    def delete(self, save=True):
        name = self.name
        super().delete(save)
        if self.field.sizes:
            for size in self.field.sizes:
                splited = list(os.path.split(name))
                splited.insert(-1, '%dx%d' % size)
                thumb_name = os.path.join(*splited)
                try:
                    self.storage.delete(thumb_name)
                except Exception:
                    pass


class ImageWithThumbsField(ImageField):

    attr_class = ImageWithThumbsFieldFile

    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, sizes=None, **kwargs):
        self.verbose_name = verbose_name
        self.name = name
        self.width_field = width_field
        self.height_field = height_field
        self.sizes = sizes
        self.use_id_for_name = kwargs.pop('use_id_for_name', True)
        super().__init__(**kwargs)
