import datetime
import json
import logging
import socket
import sys

from django.conf import settings
from django.db import models

from djtools.templatetags.filters import format_money, format_datetime
from djtools.utils import get_tl, get_client_ip, get_qualified_model_name, encrypt

from .constants import STATUS_VIEWED

log = logging.getLogger("history")


def get_now_formatted():
    return str(datetime.datetime.utcnow().isoformat())


def format_(value):
    if value in (None, ''):
        return '-'
    elif isinstance(value, bool):
        return value and 'Sim' or 'Não'
    elif value.__class__.__name__ == 'Decimal':
        return format_money(value)
    elif hasattr(value, 'strftime'):
        return format_datetime(value)
    return str(value)


def process_field(field, instance):
    pks = '-'
    value = '-'
    if isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField):
        pks = str(getattr(instance, field.attname, ''))
        try:
            value = str(getattr(instance, field.name, '') or '-')
        except Exception:
            value = '-'
    elif isinstance(field, models.ManyToManyField):
        try:
            qs = getattr(instance, field.name).all()
        except Exception:
            qs = []
        objs = []
        for obj in qs:
            try:
                objs.append(str(obj))
            except Exception:
                objs.append('-')
        objs_ids = [str(obj.id) for obj in qs]
        value = str(','.join(objs) or '-')
        pks = str(','.join(objs_ids))
    elif getattr(field, 'choices', None):
        try:
            value = str(getattr(instance, f'get_{field.attname}_display', lambda: '')() or '-')
        except Exception:
            value = '-'
        pks = str(getattr(instance, field.attname, ''))
    else:
        try:
            value = format_(getattr(instance, field.attname, ''))
        except Exception:
            value = '-'
    return str(value), str(pks)


def get_fields_attrs(new_instance, old_instance, blank_fields, encrypted_fields, ignored_fields):
    fields = []

    if old_instance:
        for field in new_instance._meta.concrete_fields:
            value1, pks1 = process_field(field, new_instance)
            value2, pks2 = process_field(field, old_instance)
            if value1 == value2 and pks1 == pks2:
                ignored_fields.append(field.name)

    for field in [field for field in new_instance._meta.concrete_fields if field.name not in ignored_fields]:
        attrs = {}
        new_value, new_pks = process_field(field, new_instance)
        if old_instance:
            old_value, old_pks = process_field(field, old_instance)
        else:
            old_value, old_pks = '-', '-'

        attrs["field"] = str(field.name)

        if field.name in encrypted_fields:
            new_value = encrypt(new_value)
            old_value = encrypt(old_value)
        if field.name in blank_fields:
            new_value = 'Este campo teve seu valor alterado.'
            old_value = 'Valor antigo.'

        attrs["new_value"] = new_value
        attrs['old_value'] = old_value
        if new_pks != '-':
            attrs["new_pks"] = new_pks
        if old_pks != '-':
            attrs["old_pks"] = old_pks
        fields.append(attrs)
    return fields


def get_request_data(request=None):
    if not request:
        request = get_tl().get_request()

    host_name = getattr(settings, 'SERVER_ALIAS', None) or socket.gethostname()

    if request:
        user = getattr(request, 'user', None)
        return dict(
            last_update=get_now_formatted(),
            author=dict(
                user_id=str(getattr(user, 'id', '-')),
                username=str(getattr(user, 'username', '-'))
            ),
            user_agent=str(request.META.get('HTTP_USER_AGENT', '-')),
            ip_address=str(get_client_ip(request)),
            url=str(request.build_absolute_uri()),
            server=str(host_name),
        )
    return dict(
        last_update=get_now_formatted(),
        author=dict(
            user_id='-',
            username='-'
        ),
        user_agent=' '.join(sys.argv),
        ip_address='-',
        url='-',
        server=str(host_name),
    )


def process_data(new_instance, old_instance, status):
    history = getattr(new_instance, 'History', None)

    disabled = getattr(history, 'disabled', False)
    if disabled:
        return

    blank_fields = getattr(history, 'blank_fields', [])
    encrypt_fields = getattr(history, 'encrypt_fields', [])
    ignore_fields = list(getattr(history, 'ignore_fields', []))
    diff = []
    if status != STATUS_VIEWED:
        diff = get_fields_attrs(new_instance, old_instance, blank_fields, encrypt_fields, ignore_fields)
        if not diff:
            return

    record = {
        'model': get_qualified_model_name(new_instance),
        'pk': getattr(new_instance, 'pk', None),
        'status': status,
        'diff': diff,
        'request': get_request_data()
    }

    log.info(json.dumps(record))
