# -*- coding: utf-8 -*-

import datetime

import xlrd
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction

from comum.models import Ano
from djtools import forms
from djtools.testutils import running_tests
from djtools.utils.pdf import check_pdf_with_pypdf, check_pdf_with_gs
from licenca_capacitacao.models import LicCapacitacaoPorDia, PedidoLicCapacitacao, \
    EditalLicCapacitacao, AnexosEdital, AnexosPedidoLicCapacitacaoSubmissao, ServidorComplementar
from rh.models import Servidor


class FiltroQuadroLicencaCapacitacaoForm(forms.FormPlus):

    ano = forms.ModelChoiceField(queryset=Ano.objects, label='Ano', required=False)

    def __init__(self, *args, **kwargs):
        super(FiltroQuadroLicencaCapacitacaoForm, self).__init__(*args, **kwargs)
        id_anos = LicCapacitacaoPorDia.objects.values_list('ano', flat=True).distinct()
        self.fields['ano'].queryset = Ano.objects.filter(id__in=id_anos)
        self.fields['ano'].initial = Ano.objects.get(ano=datetime.date.today().year).id


class CriarProcessamentoForm(forms.FormPlus):

    titulo = forms.CharFieldPlus(label='Título')
    senha = forms.CharFieldPlus(label='Senha', widget=forms.PasswordInput())

    def clean_senha(self):
        senha = self.cleaned_data['senha']
        if senha:
            usuario_autenticado = authenticate(username=self.request.user.username, password=senha)
            if not usuario_autenticado:
                raise forms.ValidationError('Senha inválida.')
        return self.cleaned_data.get('senha')


class EditarOrdemClassificacaoGestaoForm(forms.FormPlus):

    ordem_colocacao = forms.IntegerFieldPlus(label='Ordem colocação')

    def __init__(self, *args, **kwargs):
        self.ordem_colocacao_inicial = kwargs.pop('ordem_colocacao_inicial', None)
        super(EditarOrdemClassificacaoGestaoForm, self).__init__(*args, **kwargs)
        self.fields['ordem_colocacao'].initial = self.ordem_colocacao_inicial


class ImportarResultadoFinalForm(forms.FormPlus):
    planilha = forms.FileFieldPlus(help_text='O arquivo deve ter apenas os pedidos APROVADOS DE FORMA DEFINITIVA, '
                                             'no formato "xlsx", sem cabeçalho, contendo apenas as seguintes '
                                             'colunas: Identificador do Pedido, Matrícula e a Ordem de Classificação.',
                                   required=True)

    def __init__(self, edital, *args, **kwargs):
        super(ImportarResultadoFinalForm, self).__init__(*args, **kwargs)
        self.edital = edital
        self.resultados = []

    def clean(self):
        arquivo = self.cleaned_data.get('planilha')

        if arquivo:
            # Valida se eh XLS
            # -------------------------
            try:
                planilha = arquivo.file
                workbook = xlrd.open_workbook(file_contents=planilha.read())
            except Exception:
                raise forms.ValidationError(
                    'Não foi possível processar a planilha. '
                    'Verfique se o formato do arquivo é .xlsx,'
                )
            sheet = workbook.sheet_by_index(0)

            # Valida se existem 3 colunas
            # -------------------------
            if sheet.ncols < 3:
                raise forms.ValidationError('A planilha não contém as 4 colunas solicitadas.')

            erro = list()

            def get_str(n):
                if not type(n) is str:
                    return str(n).split(".")[0]
                else:
                    return n

            for i in range(0, sheet.nrows):
                dados = sheet.row_values(i)
                la = i + 1

                # Valida se cada uma das colunas tem os dados esperados
                #   Dados solicitados na planilha
                #     - Identificador do Pedido, Matrícula e a Ordem de Classificação

                # Valida Identificador do Pedido
                # ----------------
                pedido = get_str(dados[0])
                if pedido:
                    if PedidoLicCapacitacao.get_pedidos_para_processamento(self.edital).filter(id=int(pedido)).exists():
                        pedido = PedidoLicCapacitacao.objects.get(id=pedido)
                    else:
                        erro.append('Não existe pedido neste edital para o identificador informado na linha {}'.format(la))
                else:
                    erro.append('Identficador inválido na linha {}'.format(la))

                # Valida Matricula
                # ----------------
                matricula = get_str(dados[1])
                if matricula:
                    servidor = Servidor.objects.filter(matricula=matricula)
                    if servidor:
                        if not EditalLicCapacitacao.existe_algum_pedido_submetido_do_servidor_no_edital(self.edital, servidor[0]):
                            erro.append('Neste edital não existe pedido associado ao servidor da matrícula da linha {}'.format(la))
                    else:
                        erro.append('Não existe servidor associado a matrícula da linha {}'.format(la))
                else:
                    erro.append('Matrícula inválida na linha {}'.format(la))

                # Valida ordem
                # ----------------
                ordem = get_str(dados[2])
                try:
                    ordem = int(ordem)
                except forms.ValidationError:
                    erro.append('Ordem inválida "{}" na linha {}'.format(ordem, la))

                # Carrega dados da planilha
                # ----------------
                if not erro:
                    dados_aprovado = {'pedido': pedido,
                                      'ordem': ordem}
                    self.resultados.append(dados_aprovado)

            if erro:
                raise forms.ValidationError('A planilha contém o(s) '
                                            'seguinte(s) erro(s): </br>{}'.
                                            format('</br> '.join(erro)))

        return self.cleaned_data

    @transaction.atomic
    def processar(self):
        for result in self.resultados:
            pedido = result.get('pedido')
            pedido.aprovado_resultado_final = True
            pedido.ordem_classificacao_resultado_final = result.get('ordem')
            pedido.ordem_classificacao_resultado_final_gestao = result.get('ordem')
            pedido.aprovado_em_definitivo = True
            pedido.save()


class AnexosEditalForm(forms.ModelFormPlus):

    class Meta:
        model = AnexosEdital
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(AnexosEditalForm, self).__init__(*args, **kwargs)
        self.fields['arquivo'].max_file_size = settings.DEFAULT_FILE_UPLOAD_MAX_SIZE

    def clean_arquivo(self):
        content = self.cleaned_data.get('arquivo', None)
        if not content:
            raise forms.ValidationError('Este campo é obrigatório.')
        else:
            if hasattr(content, 'content_type'):
                content_type = content.content_type.split('/')[1]
                if content_type not in settings.CONTENT_TYPES:
                    raise forms.ValidationError('Tipo de arquivo não permitido. Só são permitidos arquivos com extensão: .PDF')
                if not check_pdf_with_pypdf(content) and not check_pdf_with_gs(content) and not running_tests():
                    raise forms.ValidationError('Arquivo corrompido ou mal formado, reimprima o PDF utilizando uma ferramenta de impressão adequada como o CutePDF Writer.')
                return content


class AnexosPedidoLicCapacitacaoSubmissaoForm(forms.ModelFormPlus):

    class Meta:
        model = AnexosPedidoLicCapacitacaoSubmissao
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(AnexosPedidoLicCapacitacaoSubmissaoForm, self).__init__(*args, **kwargs)
        self.fields['arquivo'].max_file_size = settings.DEFAULT_FILE_UPLOAD_MAX_SIZE

    def clean_arquivo(self):
        content = self.cleaned_data.get('arquivo', None)
        if not content:
            raise forms.ValidationError('Este campo é obrigatório.')
        else:
            if hasattr(content, 'content_type'):
                content_type = content.content_type.split('/')[1]
                if content_type not in settings.CONTENT_TYPES:
                    raise forms.ValidationError('Tipo de arquivo não permitido. Só são permitidos arquivos com extensão: .PDF')
                if not check_pdf_with_pypdf(content) and not check_pdf_with_gs(content) and not running_tests():
                    raise forms.ValidationError('Arquivo corrompido ou mal formado, reimprima o PDF utilizando uma ferramenta de impressão adequada como o CutePDF Writer.')
                return content


class SolicitarDesistenciaForm(forms.ModelFormPlus):

    class Meta:
        model = PedidoLicCapacitacao
        fields = ('solicitacao_desistencia',)

    def __init__(self, *args, **kwargs):
        super(SolicitarDesistenciaForm, self).__init__(*args, **kwargs)
        self.fields['solicitacao_desistencia'].required = True

    def save(self, *args, **kwargs):
        self.instance.data_solicitacao_desistencia = datetime.datetime.now()
        return super(SolicitarDesistenciaForm, self).save(*args, **kwargs)


class ServidorComplementarForm(forms.ModelFormPlus):

    class Meta:
        model = ServidorComplementar
        exclude = ()

    def clean(self):
        servidor = self.cleaned_data.get('servidor')
        edital = self.cleaned_data.get('edital')

        existe_como_servidor = EditalLicCapacitacao.get_servidores_efetivo_exercicio().filter(id=servidor.id).exists()
        existe_como_servidor_complementar = ServidorComplementar.objects.filter(servidor=servidor, edital=edital).exists()
        if existe_como_servidor or existe_como_servidor_complementar:
            raise forms.ValidationError('O servidor {} já existe no edital {}')

        return self.cleaned_data
