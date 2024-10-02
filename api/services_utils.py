# -*- coding: utf-8 -*-


from urllib.parse import urlparse

from django.shortcuts import redirect
from rest_framework import serializers, fields
from rest_framework.response import Response


# --------------------------------------------------------------------------------------------------------------------
from comum.models import User
from rest_framework import status


class ResponseSerializer(serializers.Serializer):
    def is_valid(self, raise_exception=False):
        self._validated_data = self.initial_data
        self._data = self.initial_data
        self._errors = {}
        return True

    def _update_initial_data(self):
        #
        # atualiza initial_data a partir dos valores dos fields tratando a situaçao
        # na qual os fields são atualizados depois da instanciação da classe 'Serializer'
        if not hasattr(self, 'initial_data'):
            self.initial_data = {}
        for attr_name in list(self.get_fields().keys()):
            if not hasattr(self, attr_name):  # fixme: as vezes isso dá verdadeiro (muito estranho)
                setattr(self, attr_name, self.get_fields().get(attr_name).default)
            if getattr(self, attr_name) is not fields.empty:
                self.initial_data[attr_name] = getattr(self, attr_name)

    @property
    def data(self):
        self._update_initial_data()
        self.is_valid()
        return super(ResponseSerializer, self).data


class ErroResponseSerializer(ResponseSerializer):
    message = serializers.CharField(required=False, allow_blank=True, default="")

    def __init__(self, instance=None, data=serializers.empty, **kwargs):
        message = kwargs.pop('message', None)
        super(ErroResponseSerializer, self).__init__(instance, data=data, **kwargs)
        self.message = message
        if not self.message:
            self.message = 'Ocorreu um erro.'


class ServiceDocParameter:
    TYPE_STRING = 'string'
    PARAM_TYPE_FORM = 'form'  # envio de um parâmetro POST
    PARAM_TYPE_HEADER = 'header'  # envio com adição de header na requisição
    PARAM_TYPE_QUERY = 'query'  # envio de um parâmetro GET

    parameter = dict()

    def __init__(self, name, description, required=True, type=TYPE_STRING, paramType=PARAM_TYPE_QUERY):
        """
        :param name: nome do parâmetro (identificador)
        :param description: descrição do parâmetro (NÃO USE ':')
        :param required: obrigatoriedade ou não
        :param type: tipo de dados
        :param paramType: tipo do parâmetro
        :return:
        """
        if required:
            required = 'true'
        else:
            required = 'false'
        #
        self.parameter = dict(name=name, description=description, required=required, type=type, paramType=paramType)

    @property
    def doc(self):
        """
        https://github.com/OAI/OpenAPI-Specification/blob/master/versions/1.2.md#524-parameter-object

        :return: string no padrão YAML docstring referente a definição de um parâmetro

            '''
            - name: <nome do parâmetro>
              description: <descrição do parâmetro>
              required: <obrigatoriedade do parâmetro>
              type: <tipo de dados do parâmetro>
              paramType: <tipo do parâmetro>
            '''
        """
        return '''
        - name: {}
          description: {}
          required: {}
          type: {}
          paramType: {}
'''.format(
            self.parameter['name'], self.parameter['description'], self.parameter['required'], self.parameter['type'], self.parameter['paramType']
        )


def service_doc(descricao, token_authorization=True, response_serializer="", parameters=[]):
    """
        Decorator que insere uma documentação no padrão YAML docstring no serviço.
        http://django-rest-swagger.readthedocs.io/en/latest/yaml.html

        :param descricao: descrição do serviço
        :param token_authorization: adiciona ou não o parâmetro header authorization (default True)
        :param response_serializer: string com o caminho completo da classe que serializa a resposta
        :param parameters: uma lista de parâmetros que serão solicitados na requisição do serviço

        Estrutura do docstring:

        '''
            <descrição>
            ---
            parameters:
                <parameter token authorization automático>
                <parameter>
                <parameter>
                <parameter>
                ...

            response_serializer: <string com o caminho completo da classe>
        '''
    """

    def decorator(func):
        doc = '''
    {}
    ---
    # YAML docstring (o separador '---' é obrigatório)
'''.format(
            descricao
        )
        #
        if token_authorization:
            doc += '''
    parameters:
        - name: Authorization
          description: Token do usuário requisitante (informe "Token [token]")
          required: true
          type: string
          paramType: header
'''
        #
        if parameters:
            if not token_authorization:
                doc += '''
    parameters:
'''
            for parameter in parameters:  # instâncias de ServiceDocParameter
                if isinstance(parameter, ServiceDocParameter):
                    doc += '''
{}
'''.format(
                        parameter.doc
                    )
        #
        if response_serializer:
            doc += '''
    response_serializer: {}
'''.format(
                response_serializer
            )
        #
        doc_anterior = func.__doc__
        if doc_anterior:
            func.__doc__ = doc_anterior + doc
        else:
            func.__doc__ = doc
        #
        return func

    return decorator


# --------------------------------------------------------------------------------------------------------------------


def request_url_base(request, barra_final=True):
    #
    # esquema://dominio[:porta][/]
    request_url = urlparse(request.META.get('HTTP_REFERER', '/'))
    request_porta = request_url.port and ':{}'.format(request_url.port) or ''
    request_barra_final = (barra_final and '/') or ''
    #
    return '{}://{}{}{}'.format(request_url.scheme, request_url.hostname, request_porta, request_barra_final)


def hora_min_seg_to_str(int_horas, int_minutos, int_segundos):
    horas = int_horas
    minutos = int_minutos
    segundos = int_segundos
    #
    if horas < 10:
        horas = '0{}'.format(horas)
    if minutos < 10:
        minutos = '0{}'.format(minutos)
    if segundos < 10:
        segundos = '0{}'.format(segundos)
    #
    return horas, minutos, segundos


# --------------------------------------------------------------------------------------------------------------------


def permission_denied_handler(request):
    # return redirect('/api/auth/login/?next=/docs/')
    return redirect('/accounts/login/?next=/api/docs/')


# --------------------------------------------------------------------------------------------------------------------


def exigir_captcha(username):
    if User.objects.filter(username=username, login_attempts__gt=3).exists():
        return True
    return False


def response_captcha():
    return Response({'detail': 'Tentativas excessivas de logins. Por favor efetue o login na página inicial do suap.'}, status=status.HTTP_403_FORBIDDEN)
