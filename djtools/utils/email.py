"""
Django, our web development framework of choice provides many useful functions,
send_mail() being one of them which we frequently use.

Though convenient, send_mail() in Django is a synchronous operation – meaning
Django will wait for the mail sending process to finish before continuing other tasks.
This is not usually that big of a deal if the mail server Django is configured to use is
located in the same site (and has low latency), but in cases where the mail server is not
located in the same cloud, this could give the impression that your website is slow,
especially in sites with relatively slow internet connectivity (like Indonesia).

Consider a really common scenario where an application automatically sends an email
verification message to a newly registered user. If configured to use a third party SMTP
server like Gmail, the email sending process takes close to half a second if our app is
located in Jakarta. This means that we are adding close a half a second of latency before
rendering a response to the user, making our app look sluggish (in reality the user
creation process itself takes less than 50ms).

So one of our engineers Gilang wrote a simple wrapper around Django’s send_mail() to
perform the task asynchronously using Python’s threading.

http://ui.co.id/blog/asynchronous-send_mail-in-django
"""
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail as django_send_mail

__all__ = ['EmailThread', 'send_notification', 'send_mail', 'html_email_template']


class EmailThread(threading.Thread):
    """
    Classe que faz o envio de e-mail de forma assincrona. Ela foi baseada em:
    http://ui.co.id/blog/asynchronous-send_mail-in-django
    """

    def __init__(self, subject, body, from_email, recipient_list, fail_silently, html, attachments=[], files=[], bcc=[]):
        """
        Construtor.

        Args:
            subject (string): assunto do e-mail;
            body (string): corpo d0 e-mail;
            from_email (string): e-mail do remetente;
            recipient_list (list): lista com os destinatários;
            fail_silently (bool): indica se é para silenciar erros;
            html (bool): indica que o e-mail é um **HTML**.
            attachments (list of tuples(name, content, mimetype)): lista de anexos
            files: (list of strings): paths of files to be attached
            bcc: (list of string): e-mail para destinatários com cópia de carbono
        """
        self.subject = subject
        self.body = body
        self.recipient_list = recipient_list
        self.from_email = from_email
        self.fail_silently = fail_silently
        self.html = html
        self.attachments = attachments
        self.files = files
        self.bcc = bcc
        threading.Thread.__init__(self)

    def run(self):
        """
        Método de execução por parte do Thread.
        """
        to = self.recipient_list
        if isinstance(to, str):
            to = to,
        msg = EmailMultiAlternatives(
            self.subject, self.body, self.from_email, to)
        if self.html:
            msg.attach_alternative(self.body, "text/html")
        for name, content, mimetype in self.attachments:
            msg.attach(name, content, mimetype)
        for file_path in self.files:
            msg.attach_file(file_path)
        if self.bcc:
            msg.bcc = self.bcc
        try:
            msg.send(self.fail_silently)
        except Exception as e:
            if not self.fail_silently:
                raise e


def send_notification(assunto, mensagem, de, vinculos, fail_silently=True, html=None, categoria=None, salvar_no_banco=True, data_permite_marcar_lida=None, data_permite_excluir=None, so_notificar=False, objeto=None):
    """
    Envia uma mensagem para o sistema de notificação.

    Args:
        assunto (string): assunto da notificação;
        mensagem (string): corpo da mensagem da notificação;
        de (string): e-mail do remetente;
        vinculos (list): lista contendo os vínculos dos usuários que receberam a notificação;
        fail_silently (bool): indica que os erros devem ser silenciados;
        html (string): corpo do e-mail no formato *HTML*.
        categoria (string): categoria vinculada a notificação.
        salvar_no_banco (bool): indica se o texto da mensagem será salvo no banco de dados do SUAP

    Note:
        Caso o usuário indique que tem preferência pelo recebimento das notificações por e-mail, um e-mail será enviado.
    """
    from comum.models import CategoriaNotificacao, NotificacaoSistema, RegistroNotificacao, PreferenciaNotificacao

    if categoria:
        categoria = categoria
    else:
        if assunto.startswith("[SUAP] "):
            categoria = assunto[7:]
        else:
            categoria = assunto

    # Verifica se a categoria existe
    categoria_notificacao = CategoriaNotificacao.objects.filter(
        assunto=categoria)
    if categoria_notificacao.exists():
        categoria_notificacao = categoria_notificacao.first()
        categoria_notificacao.ativa = True
        categoria_notificacao.save()
    else:
        categoria_notificacao = CategoriaNotificacao.objects.create(
            assunto=categoria)

    if salvar_no_banco:
        # Salva a notificacao
        if objeto:
            str_obj = f"{objeto._meta.verbose_name} #{objeto.pk}" if hasattr(objeto, '._meta') else str(objeto)
            notificacao = NotificacaoSistema.objects.create(
                categoria=categoria_notificacao, mensagem=mensagem, objeto_relacionado=str_obj)
        else:
            notificacao = NotificacaoSistema.objects.create(
                categoria=categoria_notificacao, mensagem=mensagem)

    for vinculo in vinculos:
        # Verifica a preferencia do Usuario
        if not vinculo:
            continue
        preferencia = PreferenciaNotificacao.objects.filter(
            vinculo=vinculo, categoria=categoria_notificacao)
        if preferencia.exists():
            preferencia = preferencia.first()
        else:
            if vinculo.user:
                from comum.models import Preferencia

                preferencia_usuario = Preferencia.objects.get_or_create(usuario=vinculo.user)[
                    0]
                preferencia = PreferenciaNotificacao.objects.create(
                    vinculo=vinculo, categoria=categoria_notificacao, via_suap=preferencia_usuario.via_suap,
                    via_email=preferencia_usuario.via_email
                )
        if preferencia:
            if preferencia.via_suap:
                if salvar_no_banco:
                    # Registra a notificacao no SUAP
                    rn = RegistroNotificacao.objects.create(
                        notificacao=notificacao, vinculo=vinculo)
                    if data_permite_marcar_lida:
                        rn.data_permite_marcar_lida = data_permite_marcar_lida
                    if data_permite_excluir:
                        rn.data_permite_excluir = data_permite_excluir
                    rn.save()

            if preferencia.via_email:
                # Envia a notificacao por e-mail
                email = vinculo.get_email()
                if email and not so_notificar:
                    send_mail(assunto, mensagem, de, [
                              email], fail_silently, html, True)
        else:
            # caso de vínculo que não tem user
            email = vinculo.get_email()
            if email and not so_notificar:
                send_mail(assunto, mensagem, de, [email], fail_silently, html)


def send_mail(assunto, mensagem, de, para, fail_silently=True, html=None, is_notification=False, attachments=[], files=[], bcc=[]):
    """
    Envia um email para um conjunto de e-mails.

    Args:
        assunto (string): assunto do e-mail;
        mensagem (string): mensagem a enviar pelo e-mail;
        de (string): e-mail do remetente;
        para (list): lista de e-mails para quem será enviado o e-mail;
        fail_silently (bool): indica que os erros devem ser silenciados;
        html (string): corpo do e-mail no formato *HTML*.
        attachments (list of tuples(name, content, mimetype)): lista de anexos
        files: (list of strings): paths of files to be attached
    """
    from djtools.testutils import running_tests

    if running_tests():
        django_send_mail(assunto, mensagem, de, para, fail_silently)
    else:
        html = html_email_template(mensagem, is_notification)
        if fail_silently:
            try:
                EmailThread(assunto, html, de, para, fail_silently, bool(html), attachments=attachments, files=files, bcc=bcc).start()
            except Exception:
                pass
        else:
            if isinstance(para, str):
                para = para,
            msg = EmailMultiAlternatives(
                assunto, html, de, para)
            msg.attach_alternative(html, "text/html")
            for name, content, mimetype in attachments:
                msg.attach(name, content, mimetype)
            for file_path in files:
                msg.attach_file(file_path)
            if bcc:
                msg.bcc = bcc
            msg.send(fail_silently)


def html_email_template(mensagem, is_notification=False):
    """
    Obtem o **HTML** padrão para mensagens via e-mail.

    Args:
        mensagem (string): texo da mensagem.

    Returns:
         String contendo o **HTML** da mensagem.
    """
    body = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <meta name="format-detection" content="telephone=no" />
        <title>Notificação do SUAP</title>
        <style>
            dd {{ margin: 0; padding: 0 0 15px; }}
            dt {{ font-weight: bold; }}
            h1 {{ color: #666; font-size: 12pt; font-weight: 300; margin-bottom: 0; }}
            h2 {{ color: #444; font-size: 14pt; margin-top: 5px; }}
            h2 ~ p {{ color: #444; }}
            h3 {{ border-bottom: 2px solid #666; color: #444; font-size: 12pt; padding-bottom: 5px; padding-top: 20px; }}
        </style>
        </head>
        <body style="background: #dddddd;">
            <div style="background: #dddddd; display: inline-block; overflow: hidden; padding: 20px 0; width: 100%;">
                <table width="100%" style="background: #ffffff; border-collapse: collapse; clear:both; font-family: Arial; font-size: 14px; margin: 0 auto; max-width: 800px;">
                    <tr style="background: #dddddd;">
                        <td valign="top" width="100%" style="padding: 15px 0;"></td>
                    </tr>
                    <tr>
                        <td valign="top" width="100%" style="background-color: #292929; overflow: hidden;">
                            <img src="https://suap.ifrn.edu.br/static/comum/img/email-newsletter.png" style="border: 0; margin-left: -50px;" />
                        </td>
                    </tr>
                    <tr>
                        <td valign="top" width="100%" style="background: #ffffff; border-left: 1px solid #dddddd; border-right: 1px solid #dddddd; line-height: 20px; padding: 30px 50px;">
                            {0}
                        </td>
                    </tr>
                     <tr>
                        <td valign="top" width="100%" style="background: #ffffff; border-bottom: 1px solid #dddddd; border-left: 1px solid #dddddd; border-right: 1px solid #dddddd; line-height: 14px; padding: 0 50px 60px; text-align: right;">
                            <p>Atenciosamente,</p>
                            <p><a href="{1}" style="color: #75ad0a; padding: 5px 0 0; text-align: right; text-decoration: none;">{2}</a></p>
                        </td>
                    </tr>
                    <tr style="background: #dddddd;">
                        <td valign="top" width="100%">
                            <p style="color: #666666; font-size: 9pt; line-height: 18px; margin: 0; padding: 20px 50px;">Dúvidas? Entre em contato com o Setor responsável por esta notificação.</p>'''.format(mensagem, settings.SITE_URL, settings.SITE_URL.split("//", 1)[1])

    if is_notification:
        body += '''<p style="color: #666666; font-size: 9pt; line-height: 18px; margin: 0; padding: 0 50px;">Caso você não deseje mais receber esse tipo de notificação por e-mail, <a href="{}/admin/comum/preferencianotificacao/">gerencie as suas Preferências de Notificações</a>.</p>
        <p style="color: #666666; font-size: 9pt; line-height: 18px; margin: 0; padding: 5px 50px 20px;">As preferências também podem ser acessadas pelo menu "Tec. da Informação :: Usuários :: Notificações" no SUAP.</p>'''.format(settings.SITE_URL)

    footer = '''</td>
                </tr>
            </table>
        </div>
    </body>
    </html>'''

    return f'{body}{footer}'
