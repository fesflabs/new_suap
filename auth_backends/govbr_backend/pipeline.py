import six
from django.db import transaction, IntegrityError
from social_core.exceptions import SocialAuthBaseException
from social_django.models import UserSocialAuth

from catalogo_provedor_servico.utils import get_cpf_formatado
from comum.models import PessoaEndereco, Municipio, User


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    final_username = details['username']
    return {'username': final_username}


def create_social_auth(user, uid, provider):
    if not isinstance(uid, six.string_types):
        uid = str(uid)
    if uid != user.username:
        raise SocialAuthBaseException('Erro ao tentar autenticar. Por favor, efetue login novamente.')
    with transaction.atomic():
        social_auth = UserSocialAuth.objects.create(user=user, uid=uid, provider=provider)
    return social_auth


UserSocialAuth.create_social_auth = create_social_auth


def get_confiabilidades(strategy, details, backend, user=None, *args, **kwargs):
    if user and hasattr(user, 'social_auth'):
        user.social_auth.first().set_extra_data({"confiabilidade_govbr": details['confiabilidade_govbr']})
        user.save()


def get_vinculos_ativos_ids(strategy, details, backend, user=None, *args, **kwargs):
    if user and hasattr(user, 'social_auth'):
        user.social_auth.first().set_extra_data({"vinculos_ativos_ids": details['vinculos_ativos_ids']})
        user.save()


def atualiza_dados_cidadao(strategy, details, backend, user=None, *args, **kwargs):
    try:
        if user:
            from djtools.services import consulta_cidadao
            sucesso, dados_cidadao = consulta_cidadao([details['username']])
            sexo = {1: 'M', 2: 'F', 3: None}
            if sucesso:
                dados_cidadao = dados_cidadao[0]
                user.pessoafisica.sexo = sexo.get(dados_cidadao.get("Sexo"), None)
                user.pessoafisica.nome = dados_cidadao.get("Nome", None)
                user.pessoafisica.nome_mae = dados_cidadao.get("NomeMae", None)
                user.pessoafisica.nome_pai = dados_cidadao.get("NomePai", None)
                user.save()
                municipio = Municipio.objects.filter(uf=dados_cidadao.get("UF", None), nome__icontains=dados_cidadao.get("Municipio", None)).first()
                pessoa_endereco = PessoaEndereco()
                pessoa_endereco.pessoa = user.pessoafisica
                pessoa_endereco.logradouro = dados_cidadao.get("Logradouro", None)
                pessoa_endereco.numero = dados_cidadao.get("NumeroLogradouro", None)
                pessoa_endereco.bairro = dados_cidadao.get("Bairro", None)
                pessoa_endereco.cep = dados_cidadao.get("Cep", None)
                if municipio:
                    pessoa_endereco.municipio = municipio
                pessoa_endereco.save()
    except Exception:
        pass


USER_FIELDS = ['username', 'email']


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    # If existe usuário do SUAP (User) mas não existe Usuário Social Auth
    cpf = get_cpf_formatado(details['username'])
    if User.objects.filter(pessoafisica__cpf=cpf, is_active=True).exists() and not UserSocialAuth.objects.filter(uid=details['username']).exists():
        fields = {name: kwargs.get(name, details.get(name))
                  for name in backend.setting('USER_FIELDS', USER_FIELDS)}
        if not fields:
            return

        try:
            return {
                'is_new': True,
                'user': strategy.create_user(**fields)
            }
        except IntegrityError:
            user = User.objects.filter(pessoafisica__cpf=cpf, is_active=True).first()
            UserSocialAuth.objects.create(user=user, uid=details['username'], provider="govbr")
