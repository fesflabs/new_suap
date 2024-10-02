from django.contrib.auth.decorators import permission_required
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from comum.models import PessoaEndereco, PessoaTelefone
from .models import ContraCheque, ContraChequeRubrica


@api_view(["GET"])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required("contracheques.pode_ver_contracheques_detalhados")
def contracheques(request):
    # curl -X GET http://localhost:8000/contracheques/api/contracheques/ -H 'Authorization: Token <token>' -d 'ano=2016&mes=1'

    ano = int(request.GET.get("ano", 0))
    mes = int(request.GET.get("mes", 0))

    contracheques_qs = ContraCheque.objects.ativos().fita_espelho().filter(ano__ano=ano, mes=mes, pensionista__isnull=True)

    response = dict(ano=ano, mes=mes)
    contra_cheques = []

    cache_ccr = dict()
    for ccr in (
        ContraChequeRubrica.objects.filter(contra_cheque__ano__ano=ano, contra_cheque__mes=mes)
        .select_related("rubrica", "tipo")
        .values("contra_cheque", "valor", "prazo", "rubrica__codigo", "rubrica__nome", "tipo__codigo", "tipo__nome")
    ):
        cache_ccr.setdefault(ccr["contra_cheque"], []).append(ccr)

    cache_enderecos = dict()
    for pe in PessoaEndereco.objects.filter(pessoa__pessoafisica__funcionario__servidor__isnull=False).values_list(
        "pessoa", "logradouro", "numero", "complemento", "bairro", "cep", "municipio__nome"
    ):
        pessoa_id = pe[0]
        endereco = ", ".join([i for i in pe[1:] if i])
        cache_enderecos[pessoa_id] = endereco

    cache_telefones = dict()
    for pe in PessoaTelefone.objects.filter(pessoa__pessoafisica__funcionario__servidor__isnull=False).values_list("pessoa", "numero"):
        pessoa_id, telefone = pe
        cache_telefones[pessoa_id] = telefone

    for cc in contracheques_qs.values(
        "id",
        "servidor__id",
        "servidor__matricula",
        "servidor__nome",
        "servidor__cpf",
        "servidor__cargo_emprego__nome",
        "servidor__cargo_emprego__grupo_cargo_emprego__categoria",
        "servidor__setor__uo__sigla",
        "servidor__excluido",
        "servidor__situacao__nome_siape",
        "servidor__email",
        "servidor__email_secundario",
        "servidor__pagto_banco__nome",
        "servidor__pagto_agencia",
        "servidor__pagto_ccor",
        "bruto",
    ):

        rubricas = []
        for ccr in cache_ccr.get(cc["id"], []):
            rubricas.append(
                dict(
                    valor=ccr["valor"],
                    prazo=ccr["prazo"],
                    codigo=ccr["rubrica__codigo"],
                    nome=ccr["rubrica__nome"],
                    tipo_codigo=ccr["tipo__codigo"],
                    tipo_nome=ccr["tipo__nome"],
                )
            )

        contra_cheques.append(
            dict(
                matricula=cc["servidor__matricula"],
                nome=cc["servidor__nome"],
                cpf=cc["servidor__cpf"],
                cargo=cc["servidor__cargo_emprego__nome"],
                categoria=cc["servidor__cargo_emprego__grupo_cargo_emprego__categoria"],
                campus=cc["servidor__setor__uo__sigla"],
                ativo=not cc["servidor__excluido"],
                situacao=cc["servidor__situacao__nome_siape"],
                email=cc["servidor__email"] or cc["servidor__email_secundario"],
                endereco=cache_enderecos.get(cc["servidor__id"], ""),
                telefones=cache_telefones.get(cc["servidor__id"], ""),
                # Dados bancários
                banco=cc["servidor__pagto_banco__nome"],
                agencia=cc["servidor__pagto_agencia"],
                conta_corrente=cc["servidor__pagto_ccor"],
                valor_bruto=cc["bruto"] or 0,
                rubricas=rubricas,
            )
        )

    response["contra_cheques"] = contra_cheques
    return Response(response)
