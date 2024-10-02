import django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from sentry_sdk import capture_exception

from comum.utils import get_setor
from djtools.utils import send_mail


class ServidorSemSetorMiddleware(MiddlewareMixin):
    def process_request(self, request):
        usuario = request.user
        chave = f'servidor_tem_setor_middleware_{usuario.username}'
        if usuario.is_anonymous:
            return
        if not cache.get(chave, False):
            setor = get_setor(usuario)
            try:
                if usuario.eh_servidor and not (setor and setor.uo):
                    usuario.reset_vinculo()
                    usuario.reset_profile()
                    cache.set(chave, False)
                    logout(request)
                    messages.error(
                        request,
                        '''
                            Você foi deslogado do sistema porque está sem setor SUAP. Favor entrar em contato com a
                            Gestão de Pessoas do seu campus para regularizar sua situação.
                            ''',
                    )
                    return HttpResponseRedirect('/')
                if (usuario.eh_servidor or usuario.eh_prestador or usuario.eh_aluno) and not usuario.get_profile():
                    usuario.reset_vinculo()
                    usuario.reset_profile()
                    cache.set(chave, False)
                    logout(request)
                    obj = None
                    if usuario.eh_aluno:
                        from edu.models import Aluno
                        obj = Aluno.objects.filter(matricula=usuario.username).first()
                    elif usuario.eh_servidor:
                        from rh.models import Servidor
                        obj = Servidor.objects.filter(matricula=usuario.username).first()
                    elif usuario.eh_prestador:
                        from comum.models import PrestadorServico
                        obj = PrestadorServico.objects.filter(matricula=usuario.username).first()

                    if obj and obj.pessoa_fisica and not obj.pessoa_fisica.username:
                        obj.pessoa_fisica.username = usuario.username
                        obj.pessoa_fisica.save()
                        alerta = '''
                        Por favor efetue o login novamente.
                        '''
                    else:
                        titulo = f'Usuário {usuario.username} está sem pessoa física associada.'
                        msg_notificacao = 'Infelizmente, nenhuma matrícula está associada a este username, talvez seja necessário criar uma nova pessoa física.'
                        alerta = '''
                        Você foi deslogado do sistema porque está sem uma pessoa física associada. A equipe de TI já foi notificada,
                        mas você pode entrar em contato com a equipe de TI da reitoria da instituição para regularizar sua situação.
                        '''
                        capture_exception(Exception(f'{titulo} {msg_notificacao}'))
                        send_mail(titulo, f'{titulo} {msg_notificacao}', settings.DEFAULT_FROM_EMAIL, settings.ADMINS)
                    messages.error(
                        request,
                        alerta,
                    )
                    return HttpResponseRedirect('/')
            except Exception:
                cache.set(chave, False)
                messages.error(request, 'Você foi deslogado pois sua sessão expirou. Efetue o login novamente.')
                return HttpResponseRedirect('/')
            if not usuario.is_superuser:
                message = None

                eh_oauth2_govbr_user = "GovbrOAuth2" in request.session.get(django.contrib.auth.BACKEND_SESSION_KEY, [])
                if not usuario.get_vinculo() and not eh_oauth2_govbr_user:
                    message = '''
                        Você foi deslogado pois não existe um vínculo associado a este usuário. Favor entrar em contato com a
                        Coordenação de TI do seu campus para regularizar sua situação.
                    '''
                if not usuario.get_profile() and not eh_oauth2_govbr_user:
                    message = '''
                        Você foi deslogado pois não existe uma pessoa física associada a este usuário. Favor entrar em contato com a
                        Coordenação de TI do seu campus para regularizar sua situação.
                    '''
                if message:
                    cache.set(chave, False)
                    messages.error(request, message)
                    logout(request)
                    return HttpResponseRedirect('/')

        cache.set(chave, True)
