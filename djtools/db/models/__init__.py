# pylint: skip-file
import datetime
import os
import uuid
import base64

from django.conf import settings

from djtools.storages.utils import get_private_storage
from djtools.utils import to_ascii, eval_attr, get_tl
from djtools.utils import get_search_field
from djtools.db.models.manager import *  # NOQA
from django.db.models import *  # NOQA
from django.core import checks

from operator import or_
from django import utils as django_utils
from django.db import models
from djtools.choices import STATE_CHOICES

from djtools.forms import fields as formfields
from djtools.lps import MetaModelPlus
from Crypto.Cipher import DES, AES

from functools import reduce

from djtools.unaccent_field import UnaccentField
assert UnaccentField


###############
# Fields PLUS #
###############


class NotaField(models.PositiveIntegerField):

    def to_python(self, value):
        if settings.NOTA_DECIMAL and settings.CASA_DECIMAL == 1:
            value = int(float(value) * 10)
        elif settings.NOTA_DECIMAL and settings.CASA_DECIMAL == 2:
            value = int(float(value) * 100)
        return super().to_python(value)

    def _get_prep_value(self, value):
        if settings.NOTA_DECIMAL and settings.CASA_DECIMAL == 1:
            return super().get_prep_value(value * 10)
        elif settings.NOTA_DECIMAL and settings.CASA_DECIMAL == 2:
            return super().get_prep_value(value * 100)
        return super().get_prep_value(value)

    def formfield(self, **kwargs):
        if settings.NOTA_DECIMAL:
            kwargs.setdefault('form_class', formfields.NotaField)
        field = super().formfield(**kwargs)
        if settings.NOTA_DECIMAL:
            field.widget = formfields.NotaField.widget()
        return field


class IntegerFieldPlus(models.IntegerField):
    def __init__(self, *args, **kwargs):
        self.extra_attrs = kwargs.pop('extra_attrs', {})
        super().__init__(*args, **kwargs)


class CharFieldPlus(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        self.extra_attrs = kwargs.pop('extra_attrs', {})
        self.widget_attrs = kwargs.pop('widget_attrs', {})
        if 'width' in kwargs:
            self.widget_attrs['style'] = 'width: {}px;'.format(kwargs.pop('width'))
        super().__init__(*args, **kwargs)

    def formfield(self, *args, **kwargs):
        field = super().formfield(*args, **kwargs)
        field.widget.attrs.update(self.widget_attrs)
        return field


class ForeignKeyPlus(models.ForeignKey):
    """
    Deixa o widget padrão o ModelChoiceFieldPlus quando se tem mais de 50 registros.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('on_delete', models.CASCADE)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.ModelChoiceFieldPlus)
        return super(self.__class__, self).formfield(**kwargs)


class OneToOneFieldPlus(models.OneToOneField):
    """
    Deixa o widget padrão o ModelChoiceFieldPlus.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('on_delete', models.CASCADE)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.ModelChoiceFieldPlus)
        return super(self.__class__, self).formfield(**kwargs)


class ManyToManyFieldPlus(models.ManyToManyField):
    """
    Deixa o widget padrão o MultipleModelChoiceFieldPlus.
    """

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.MultipleModelChoiceFieldPlus)
        return super(self.__class__, self).formfield(**kwargs)


class CurrentUserField(models.ForeignKey):
    """
    Utilizado para armazenar o usuário autenticado.
    """

    def __init__(self, *args, **kwargs):
        from comum.models import User

        kwargs.setdefault('on_delete', models.CASCADE)
        kwargs.setdefault('editable', False)
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('to', User)
        kwargs.setdefault('default', get_tl().get_user)
        super().__init__(*args, **kwargs)


class SearchField(models.TextField):
    """
    Campo utilizado para buscas, recebendo uma lista de atributos da instância
    (``attrs``) e os convertendo para valores de forma (``prepare_string``) a
    tornar as buscas mais eficientes.
    """

    @staticmethod
    def prepare_string(v):
        return str(to_ascii(v).upper().strip())

    def pre_save(self, model_instance, add):
        search_text = []
        if not hasattr(self, 'search_attrs'):
            return model_instance.__getattribute__(self.name)

        for attr_name in self.search_attrs:
            val = eval_attr(model_instance, attr_name)
            if val:  # Evitar string `NONE`
                val = self.prepare_string(val)
                search_text.append(val)
        return ' '.join(search_text)

    def __init__(self, *args, **kwargs):
        if 'attrs' in kwargs:
            self.search_attrs = kwargs.pop('attrs')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('default', '')
        kwargs.setdefault('editable', False)
        super().__init__(*args, **kwargs)


class BrSexoField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 1)
        kwargs.setdefault('choices', (('M', 'Masculino'), ('F', 'Feminino')))
        super(self.__class__, self).__init__(*args, **kwargs)


class BrDiaDaSemanaField(models.CharField):
    def __init__(self, *args, **kwargs):
        choices = [(str(django_utils.dates.WEEKDAYS[i]), str(django_utils.dates.WEEKDAYS[i])) for i in range(7)]
        kwargs.setdefault('max_length', 50)
        kwargs.setdefault('choices', choices)
        super().__init__(*args, **kwargs)


class DecimalFieldPlus(models.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('max_digits', 12)
        super(self.__class__, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.DecimalFieldPlus)
        return super(self.__class__, self).formfield(**kwargs)


class BrCpfField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 14)
        kwargs.setdefault('verbose_name', 'CPF')
        super(self.__class__, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.BrCpfField)
        return super(self.__class__, self).formfield(**kwargs)


class BrCnpjField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 18)
        kwargs.setdefault('verbose_name', 'CNPJ')
        super(self.__class__, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.BrCnpjField)
        return super(self.__class__, self).formfield(**kwargs)


class BrCepField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 9)
        super(self.__class__, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.BrCepField)
        return super(self.__class__, self).formfield(**kwargs)


class BrTelefoneField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 14)
        super(self.__class__, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.BrTelefoneField)
        return super(self.__class__, self).formfield(**kwargs)


class DateFieldPlus(models.DateField):
    def formfield(self, *args, **kwargs):
        kwargs.setdefault('form_class', formfields.DateFieldPlus)
        field = super().formfield(**kwargs)
        return field


class TimeFieldPlus(models.TimeField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.TimeFieldPlus)
        return super().formfield(**kwargs)


class DateTimeFieldPlus(models.DateTimeField):
    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.DateTimeFieldPlus)
        return super(self.__class__, self).formfield(**kwargs)


class FieldFilePlus(models.fields.files.FieldFile):
    @property
    def url(self):
        if not self:
            return ''
        return self.storage.url(self.name)


class FileFieldPlus(models.FileField):
    attr_class = FieldFilePlus

    def __init__(self, *args, **kwargs):
        self.filetype = kwargs.pop('filetypes', None)
        self.check_mimetype = kwargs.pop('check_mimetype', True)
        self.max_file_size = kwargs.pop('max_file_size', None)
        self.create_date_subdirectories = kwargs.pop('create_date_subdirectories', False)
        self.force_filename = kwargs.pop('force_filename', None)
        super().__init__(*args, **kwargs)

    def _check_upload_to(self):
        if not self.upload_to:
            return [
                checks.Error(
                    f"O 'upload_to' de {self.__class__.__name__} é um campo obrigatório.",
                    obj=self,
                    id='fields.E202',
                    hint='Adicione o atributo no FileFieldPlus.',
                )
            ]
        return super()._check_upload_to()

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.FileFieldPlus)
        kwargs.setdefault('filetypes', self.filetype)
        kwargs.setdefault('check_mimetype', self.check_mimetype)
        kwargs.setdefault('max_file_size', self.max_file_size)
        return super().formfield(**kwargs)

    def generate_filename(self, instance, filename):
        filename = super().generate_filename(instance, filename)
        if self.create_date_subdirectories:
            directory = os.path.dirname(filename)
            name = os.path.basename(filename)
            today = datetime.datetime.today().strftime('%Y/%m/%d')
            directory = f'{directory}/{today}'
            filename = f'{directory}/{name}'
        ext = '.{}'.format(filename.split('.')[-1])
        filename = filename.replace(ext, f'-{uuid.uuid4().hex}{ext}')
        return filename


class ImageFieldPlus(models.ImageField):
    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, **kwargs):
        self.filetype = kwargs.pop('filetypes', None)
        self.check_mimetype = kwargs.pop('check_mimetype', True)
        self.max_file_size = kwargs.pop('max_file_size', None)
        self.width_field, self.height_field = width_field, height_field
        super().__init__(verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.ImageFieldPlus)
        kwargs.setdefault('max_file_size', self.max_file_size)
        return super().formfield(**kwargs)

    def generate_filename(self, instance, filename):
        filename = super().generate_filename(instance, filename)
        ext = '.{}'.format(filename.split('.')[-1])
        filename = filename.replace(ext, f'-{uuid.uuid4().hex}{ext}')
        return filename


class PrivateFileField(FileFieldPlus):
    def __init__(self, *args, **kwargs):
        kwargs.update(storage=get_private_storage())
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', formfields.PrivateFileField)
        return super().formfield(**kwargs)


class BrEstadoBrasileiroField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 2)
        kwargs.setdefault('choices', STATE_CHOICES)
        super().__init__(*args, **kwargs)


class LookupDateTimeToDate(models.Transform):
    """
    Uma implementação do SQL lookup quando usar '__date' com datetimes.
    Permite comparar DateTimeField com DateField.
    Exemplo de uso:
        Arquivo.objects.filter(data_geracao__date='2011-08-18')
        ou
        Arquivo.objects.filter(data_geracao__date=datetime.date(2011, 08, 18))
    """

    lookup_name = 'date'

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return f'DATE({lhs})', params

    @property
    def output_field(self):
        return models.DateField()


models.DateTimeField.register_lookup(LookupDateTimeToDate)


class PositiveIntegerFieldPlus(models.PositiveIntegerField):
    """ permite informar um valor mínimo diferente de zero através do
        parâmetro 'min_value'
    """

    def __init__(self, *args, **kwargs):
        self.min_value = kwargs.pop('min_value', 0)
        if self.min_value < 0:
            self.min_value = 0
        #
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value}
        defaults.update(kwargs)
        return super().formfield(**defaults)


def _search(cls, q, fields=None, max_fields=5):
    """
    Busca genérica para models.

    q         : string a ser buscada
    fields    : define os campos que se quer filtrar
    max_fields: usado quando não é passado o fields e define os N primeiros campos
                charfield do modelo que serão incluídos na busca
    """

    def _get_str_fields(cls):
        """Retorna lista de campos (string) cujo tipo é CharField ou TextField"""
        fields = []
        for f in cls._meta.fields:
            if f.get_internal_type() in ['CharField', 'TextField']:
                fields.append(f.name)
        if not fields:
            raise Exception(f'Class {cls.__name__} don\'t have CharField or TextField.')
        return fields

    search_field = get_search_field(cls)

    if search_field and not fields:
        use_fields = False
        use_search_field = True
    else:
        use_fields = True
        use_search_field = False

    qs = cls.objects.all()

    if use_fields:
        fields = fields or _get_str_fields(cls)[:max_fields]
        for word in q.split(' '):
            or_queries = [models.Q(**{f'{field_name}__icontains': word}) for field_name in fields]
            qs = qs.filter(reduce(or_, or_queries))
    elif use_search_field:
        q = SearchField.prepare_string(q)
        for word in q.split(' '):
            or_queries = [models.Q(**{f'{search_field.name}__contains': word})]
            qs = qs.filter(reduce(or_, or_queries))

    return qs

##########
# Models #
##########


class SUAPMetaModel(MetaModelPlus):
    def __new__(cls, name, *args, **kwargs):
        my_meta = super().__new__(cls, name, *args, **kwargs)
        my_meta._meta.default_permissions = ('add', 'change', 'delete', 'view')
        # view_permission_tuple = (('view_' + my_meta._meta.model_name, u'Pode visualizar {}'.format(my_meta._meta.verbose_name)),)
        # if my_meta._meta.permissions:
        #     if not view_permission_tuple[0] in [x for x, y in my_meta._meta.permissions]:
        #         my_meta._meta.permissions += view_permission_tuple
        # else:
        #     my_meta._meta.permissions = view_permission_tuple
        return my_meta


class ModelPlus(models.Model, metaclass=SUAPMetaModel):
    """ A models.Model with facilities """

    class Meta:
        abstract = True

    def __repr__(self):
        return f'{self.__class__.__module__}.{self.__class__.__name__} #{self.pk} - "{self.__str__()}"'

    def __str__(self):
        for f in self.__class__._meta.fields:
            if f.get_internal_type() in ['CharField', 'TextField']:
                value = getattr(self, f.name)
                if value:
                    return value
        return f'{self.__class__._meta.verbose_name} {self.pk}'

    @classmethod
    def search(cls, q, fields=None, max_fields=5):
        return _search(cls, q, fields=fields, max_fields=max_fields)

    @classmethod
    def get_or_create(cls, fill_attr=None, **kwargs):
        """ A short to objects.get_or_create
        By pass the kwargs arguments to objects.get_or_create class method,
        if its has created the object, this get_or_create will filled the fill_attr attribute, if is not None,
        with a message to update the objects.
        If fill_attr is None it will fill the first null char (or text) field.
        """

        def get_first_null_char_field(self, force_attr=None):

            if force_attr:
                return self._meta.get_field(force_attr)

            for f in self._meta.fields:
                if f.get_internal_type() in ['CharField', 'TextField'] and not getattr(self, f.name):
                    return f

            return None

        o, created = cls.objects.get_or_create(**kwargs)
        if created:
            f = get_first_null_char_field(o, fill_attr)
            if f:
                c = f'Atualize o cadastro de {cls._meta.verbose_name_plural}'
                c = c[: f.max_length]
                setattr(o, f.name, c)
                o.save()

        return o, created

    # @classmethod
    # def _case_ordering_relevance(cls, list_relevance):
    #     whens = []
    #     for cont, order_ in enumerate(list_relevance):
    #         whens.append(When(Q(order_), then=Value(cont)))
    #     case = Case(*whens, output_field=IntegerField(), default=cont+1)
    #     return case

    def _get_search_fields_optimized_content_to_save(self):
        """
        Esse método retorna o conteúdo que deverá ser armazenado no atributo search_fields_optimized. As classes filhas
        deverão sobreescrever esse método para personalizar essa informação.
        :return: texto
        """
        raise NotImplementedError('Método _get_search_fields_optimized_content_to_save não implementado.')

    def save(self, *args, **kwargs):
        # Ajustando as informações reduntantes que serão usadas para uma busca mais eficiente na entidade.
        if hasattr(self, 'search_fields_optimized'):
            self.search_fields_optimized = self._get_search_fields_optimized_content_to_save()
        return super().save(*args, **kwargs)


class EncryptedPKModel(ModelPlus):
    """Adds encrypted_pk property to children which returns the encrypted value of the primary key."""

    encryption_obj = DES.new(settings.SECRET_KEY[:8].encode(), mode=DES.MODE_ECB)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setattr(self.__class__, f"encrypted_{self._meta.pk.name}", property(self.__class__._encrypted_pk))

    def _encrypted_pk(self):
        pk = self.pk
        return encrypt_val(pk)

    encrypted_pk = property(_encrypted_pk)

    class Meta:
        abstract = True


def encrypt_val(clear_text):
    enc_secret = AES.new(settings.SECRET_KEY[:32].encode(), mode=AES.MODE_ECB)
    tag_string = str(clear_text) + (AES.block_size - len(str(clear_text)) % AES.block_size) * "\0"
    cipher_text = base64.b64encode(enc_secret.encrypt(tag_string.encode())).hex()
    return cipher_text


def decrypt_val(cipher_text):
    dec_secret = AES.new(settings.SECRET_KEY[:32].encode(), mode=AES.MODE_ECB)
    unhex = bytearray.fromhex(cipher_text).decode()
    raw_decrypted = dec_secret.decrypt(base64.b64decode(unhex))
    clear_val = raw_decrypted.decode().rstrip("\0")
    return clear_val
