from django.conf import settings

from djtools.utils import get_uo_setor_listfilter
from rh.forms import EmpregadoFesfForm
from rh.lps.demo_lps.forms import CargoEmpregoForm

'''
O ServidorAdmin abaixo sobrescreve a propriedade list_filter permanecendo com as demais propriedades do admin original. 
'''


class ServidorAdmin():
    form = EmpregadoFesfForm
    list_filter = get_uo_setor_listfilter() + ('excluido',)
    dados_endereco = (('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),)
    dados_funcionais = (("Dados Funcionais", {"fields": ('cargo_emprego', "setor", "setores_adicionais")}),)
    dados_documentacao_rg = (("RG", {"fields": ('rg', 'rg_uf', 'rg_orgao', 'rg_data')}),)
    dados_documentacao_titulo = (("Título de Eleitor", {"fields": ('titulo_numero', 'titulo_zona', 'titulo_secao', 'titulo_data_emissao', 'titulo_uf')}),)
    dados_bancarios= (('Dados Bancários', {'fields': ('pagto_banco', 'pagto_agencia', 'pagto_ccor',)}),)
    dados_docs = (('Documentos', {'fields': ('ctps_numero', 'ctps_uf', 'ctps_serie', 'pis_pasep', 'numero_registro')}),)

    dados_sistemicos = ()
    fieldsets = (
        ("Dados Pessoais", {"fields": ("nome_social", 'nome_registro', "nome_pai", 'nome_mae', 'sexo', "nascimento_municipio",'nacionalidade','nivel_escolaridade', 'estado_civil', "foto")}),
    ) + dados_funcionais + dados_endereco

    extra_fieldsets = (
                          ('Dados para Contato', {'fields': ('email', 'telefone_celular', )}),
                      ) + dados_documentacao_rg + dados_documentacao_titulo + dados_bancarios + dados_docs

    super_extra_fieldsets = ()


    def get_fieldsets(self, request, obj=None):
        meus_fieldsets = self.fieldsets
        if request.user.has_perm("rh.add_servidor"):
            print('Add user')
            meus_fieldsets = ( self.fieldsets +
                self.extra_fieldsets + self.dados_sistemicos + (("Para Gestão de Pessoas", {"fields": ("cpf", "matricula", "situacao")}),)
            )
        elif request.user.has_perm("rh.eh_rh_sistemico"):
            meus_fieldsets = self.extra_fieldsets + self.dados_sistemicos
        if request.user.is_superuser:
            meus_fieldsets += self.super_extra_fieldsets

        return meus_fieldsets


'''
O CargoEmpregoAdmin abaixo retira a propriedade readonly_fields do admin original e adiciona um novo formulário para o
admin de cargo emprego.
'''


class CargoEmpregoAdmin():
    readonly_fields = []
    form = CargoEmpregoForm
