from comum.models import User
from djtools import tasks as djtools_tasks
from djtools.db import models
from edu.models.logs import LogModel


class Mensagem(LogModel):
    remetente = models.ForeignKeyPlus('comum.User', verbose_name='Remetente', related_name='remetente_set')
    destinatarios = models.ManyToManyFieldPlus(User, verbose_name='Destinatários', related_name='destinatarios_set')
    assunto = models.CharFieldPlus('Assunto')
    conteudo = models.TextField('Conteúdo')
    anexo = models.FileFieldPlus(upload_to='edu/mensagem/', null=True, blank=True, verbose_name='Anexo')
    data_envio = models.DateTimeField(auto_now=True)
    via_suap = models.BooleanField('Via SUAP', default=True)
    via_email = models.BooleanField('Via E-mail', default=False)

    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ('-data_envio',)

    def existe_registro_leitura(self, user):
        return RegistroLeitura.objects.filter(destinatario__pk=user.pk, mensagem=self).exists()

    def get_absolute_url(self):
        return f'/edu/mensagem/{self.pk}/'

    def enviar_emails(self, qs_alunos, anexo=None, coordenadores=None, diretores=None, copia_para_remetente=True):
        if coordenadores is None:
            coordenadores = []
        if diretores is None:
            diretores = []
        emails = list(qs_alunos.exclude(pessoa_fisica__email="").values_list("pessoa_fisica__email", flat=True))
        emails_secundarios = list(qs_alunos.exclude(pessoa_fisica__email_secundario="").values_list("pessoa_fisica__email_secundario", flat=True))
        if copia_para_remetente:
            if self.remetente.get_profile().email:
                emails.append(self.remetente.get_profile().email)
            if self.remetente.get_profile().email_secundario:
                emails.append(self.remetente.get_profile().email_secundario)
        for coordenador in coordenadores:
            if coordenador.get_profile().email:
                emails.append(coordenador.get_profile().email)
        for diretor in diretores:
            if diretor.get_profile().email:
                emails.append(diretor.get_profile().email)
        files = []
        if anexo:
            files.append(anexo)
        return djtools_tasks.enviar_emails(self.assunto, self.conteudo, list(set(emails + emails_secundarios)), '/edu/enviar_mensagem/', files=files)


class RegistroLeitura(models.ModelPlus):
    mensagem = models.ForeignKeyPlus('edu.Mensagem', verbose_name='Mensagem')
    destinatario = models.ForeignKeyPlus('comum.User', verbose_name='Destinatário')
    data_leitura = models.DateTimeField(auto_now=True)

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Registro de Leitura'
        verbose_name_plural = 'Registros de Leituras'


class RegistroExclusao(models.ModelPlus):
    mensagem = models.ForeignKeyPlus('edu.Mensagem', verbose_name='Mensagem')
    destinatario = models.ForeignKeyPlus('comum.User', verbose_name='Destinatário')
    data_exclusao = models.DateTimeField(auto_now=True)

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Registro de Exclusão'
        verbose_name_plural = 'Registros de Exclusões'


class MensagemEntrada(Mensagem):
    class Meta:
        proxy = True
        verbose_name = 'Mensagem Recebida'
        verbose_name_plural = 'Mensagens Recebidas'


class MensagemSaida(Mensagem):
    def get_quantidade_destinatarios(self):
        return self.destinatarios.count()

    get_quantidade_destinatarios.short_description = 'Quantidade de Destinatários'

    def get_quantidade_leitura(self):
        return RegistroLeitura.objects.filter(mensagem=self).count()

    get_quantidade_leitura.short_description = 'Quantidade de Leitura'

    class Meta:
        proxy = True
        verbose_name = 'Mensagem Enviada'
        verbose_name_plural = 'Mensagens Enviadas'
