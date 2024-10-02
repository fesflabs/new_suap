from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from djtools.assincrono import task
from djtools.utils import XlsResponse, rhasattr, eval_attr, rgetattr, CsvResponse, send_notification, html_email_template


def tratar_celula_relatorio(valor):
    from djtools.templatetags.filters import format_
    from django.db.models.query import QuerySet

    if isinstance(valor, bool):
        valor = valor and 'Sim' or 'Não'
    elif isinstance(valor, QuerySet):
        valor = ', '.join([str(x) for x in valor.all()])
    elif not isinstance(valor, str) and hasattr(valor, '__iter__'):
        valor = strip_tags(', '.join([format_(e, html=False) for e in valor]))
    else:
        valor = strip_tags(format_(valor, html=False))
    return valor


@task('Exportar para XLS/CSV', method='thread')
def table_export(stype, queryset, columns, task=None):
    task.count(queryset, queryset)
    rows = [[coluna for coluna in columns.keys()]]
    accessors = columns.values()
    for obj in task.iterate(queryset):
        row = []
        for field in accessors:
            if rhasattr(obj, field):
                value = eval_attr(obj, field)
                if callable(value):
                    value = value()
            else:
                value = rgetattr(obj, field)
                if callable(value):
                    if type(value).__name__ == 'ManyRelatedManager':
                        value = ', '.join([str(x) for x in value.all()])
                    else:
                        value = value()
            row.append(tratar_celula_relatorio(value))
        rows.append(row)
    return XlsResponse(rows, processo=task) if stype == 'xls' else CsvResponse(rows, processo=task)


@task('Exportar para XLS/CSV Admin', method='thread')
def admin_export(type, queryset, request, admin, task=None):
    queryset = queryset[0:50000]
    task.count(queryset, queryset)
    metodo = f'to_{type}'
    if callable(getattr(admin, metodo, None)):
        rows = getattr(admin, metodo)(request, queryset, task)
    else:
        rows = []
        header = []
        for field in admin.list_xls_display or admin.list_display:
            if field != 'show_list_display_icons':
                header_name = field.upper().replace('_', ' ')
                if header_name.startswith('GET '):
                    header_name = header_name[4:]
                header.append(header_name)

        rows.append(header)
        for obj in task.iterate(queryset):
            obj.export_to_xls = True
            row = []
            for field in admin.list_xls_display or admin.list_display:
                if field != 'show_list_display_icons':
                    if rhasattr(obj, field):
                        value = eval_attr(obj, field)
                        if callable(value):
                            value = value()
                    else:
                        value = rgetattr(admin, field)
                        if callable(value):
                            value = value(obj)

                    row.append(tratar_celula_relatorio(value))
            rows.append(row)

    return XlsResponse(rows, processo=task) if type == 'xls' else CsvResponse(rows, processo=task)


@task('Notificar os usuários de um grupo')
def notificar_usuarios_grupo(titulo, remetente, texto, grupo, redirect_url, task=None):
    n = 0
    count = 0
    for usuario in task.iterate(grupo.user_set.all()):
        try:
            n += 1
            count += 1
            mensagem = "<h1>{}</h1> {}".format(titulo, "<br />".join(texto.split("\n")))
            send_notification(titulo, mensagem, remetente, [usuario.get_vinculo()], categoria='Mensagem para Grupo')
        except Exception:
            n -= 1
    return task.finalize('%d/%d notificações enviadas com sucesso.' % (n, count), url=redirect_url)


@task('Enviar emails')
def enviar_emails(titulo, mensagem, lista_emails, redirect_url, is_notification=False, bcc=None, attachments=None, files=None, task=None):
    n = 0
    count = 0
    attachments = attachments or []
    files = files or []
    for email in task.iterate(lista_emails):
        html = html_email_template(mensagem, is_notification)
        try:
            n += 1
            count += 1
            msg = EmailMultiAlternatives(
                titulo, html, settings.DEFAULT_FROM_EMAIL, [email])
            msg.attach_alternative(html, "text/html")
            for name, content, mimetype in attachments:
                msg.attach(name, content, mimetype)
            for file_path in files:
                msg.attach_file(file_path)
            if bcc:
                msg.bcc = bcc
            msg.send(False)
        except Exception:
            n -= 1
    return task.finalize('%d/%d emails enviados com sucesso.' % (n, count), url=redirect_url)
