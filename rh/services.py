# TODO: módulo deprecated, mover serviços para app api

import hashlib
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from comum.models import RegistroEmissaoDocumento
from .models import Servidor


@api_view(['GET'])
@authentication_classes((JWTAuthentication, SessionAuthentication))
@login_required
def emitir_carteira_funcional_digital(request, matricula):
    """
    Cria um novo RegistroEmissaoDocumento e retorna o código de validação e a data de emissão do registro.

    """
    obj = get_object_or_404(Servidor.objects.ativos(), matricula=matricula)
    qs = RegistroEmissaoDocumento.objects.filter(tipo='Carteira Funcional Digital', modelo_pk=obj.pk, data_validade__gte=datetime.today())

    if not qs.exists():
        # Criando o Registro de Emissão da Carteira Funcional Digital
        registro_emissao = RegistroEmissaoDocumento()
        registro_emissao.tipo = 'Carteira Funcional Digital'
        registro_emissao.data_emissao = datetime.today()
        registro_emissao.codigo_verificador = hashlib.sha1(f'{obj.matricula}{registro_emissao.data_emissao}{settings.SECRET_KEY}'.encode()).hexdigest()
        registro_emissao.data_validade = datetime.today() + timedelta(days=1)
        registro_emissao.modelo_pk = obj.pk
        registro_emissao.save()
    else:
        registro_emissao = qs[0]
    return Response(dict(codigo_verificador=registro_emissao.codigo_verificador, data_emissao=registro_emissao.data_emissao, data_validade=registro_emissao.data_validade))
