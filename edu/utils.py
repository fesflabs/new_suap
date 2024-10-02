from django.contrib.admin.filters import SimpleListFilter
from djtools.utils.response import render_to_string

from comum.models import Ano
from djtools.utils import normalizar_nome_proprio
from edu.models import CursoCampus, Modalidade, Polo
from rh.models import UnidadeOrganizacional


def metadata(objeto):
    lista = []
    box = []
    methods_aux = []
    methods = []
    # Navega pelos atributos do objeto escolhido

    lista_fields_name = []
    for field in objeto._meta.fields:
        lista_fields_name.append(field.name)

    for field in objeto._meta.fields:
        field_name_aux = False
        box_name_aux = 'Dados Gerais'
        if hasattr(objeto, 'fieldsets'):
            dict_fieldsets = dict(objeto.fieldsets)
            for t1, t2 in list(dict_fieldsets.items()):
                for t3 in list(t2.values()):
                    for t4 in t3:
                        if t4 == field.name:
                            field_name_aux = True
                            box_name_aux = t1
                        else:
                            if not t4 in lista_fields_name and not t4 in methods_aux:
                                methods_aux.append(t4)
                                methods.append({t1: t4})

        if not hasattr(objeto, 'fieldsets') or field_name_aux:
            url = ''

            # Recupera o valor do atributo
            if field.choices:
                valor = getattr(objeto, 'get_{}_display'.format(field.name))()
            elif field.__class__.__name__ == 'ImageWithThumbsField':
                imagem = objeto.__getattribute__(field.name)
                try:
                    valor = hasattr(imagem, 'url') and '<img heigth="200" width="150" src="{}" alt="Imagem de {}"/>'.format(imagem.url, objeto) or ''
                except Exception:
                    valor = ''
            else:
                valor = objeto.__getattribute__(field.name)

            # Verifica se o campo é estrangeiro
            if hasattr(field, 'related') and valor:
                url = ''
                # Verifica se o objeto possui o método get_absolute_url
                if hasattr(valor, 'get_absolute_url'):
                    url = str(valor.get_absolute_url())
                # O objeto estrangeiro precisa ser uma classe para gerar a url
                else:
                    app = valor._meta.app_label
                    modelo = valor.__class__.__name__
                    url = '/edu/visualizar/{}/{}/{}/'.format(app, modelo, valor.pk)
            if not box_name_aux in box:
                box.append(box_name_aux)

            lista.append((normalizar_nome_proprio(field.verbose_name), valor, url, box_name_aux))

    for dict_methods in methods:
        for box_name, method_name in list(dict_methods.items()):
            if type(method_name) == str:
                method = getattr(objeto, method_name)
                lista.append((method_name.replace('get_', '').replace('_', ' ').capitalize(), method, '', box_name))
            elif type(method_name) == list or type(method_name) == tuple:
                for m in method_name:
                    method = getattr(objeto, m)
                    lista.append((m.replace('get_', '').replace('_', ' ').capitalize(), method, '', box_name))

            if not box_name in box:
                box.append(box_name)

    lista.append(box)
    return lista


class TabelaBidimensional:
    def __init__(self, descricao, qs, vertical_model=UnidadeOrganizacional, vertical_key='curso_campus__diretoria__setor__uo__id', horizontal_model=None, horizontal_key=None):
        self.descricao = descricao
        colunas = []

        if horizontal_model:
            horizontal_objects = horizontal_model.objects.filter(id__in=qs.values_list(horizontal_key, flat=True))
        else:
            horizontal_objects = vertical_model.objects.none()

        vertical_objects = vertical_model.objects.filter(id__in=qs.values_list(vertical_key, flat=True))
        if vertical_model == CursoCampus:
            vertical_objects = vertical_objects.order_by('diretoria__setor__uo')

        registros = []
        registro_final = dict()
        registro_final[0] = 'TOTAL'

        total_final = 0
        for i in range(1, horizontal_objects.count() + 1):
            registro_final[i] = 0
        for vertical_object in vertical_objects:
            registro = dict()
            total = 0

            if horizontal_objects:
                # tabela bi-dimensional
                if not colunas:
                    colunas.append(vertical_model._meta.verbose_name)
                    for horizontal_object in horizontal_objects:
                        colunas.append(str(horizontal_object))
                    colunas.append('TOTAL')

                registro[0] = str(vertical_object)
                i = 1
                self.align_column = i
                for horizontal_object in horizontal_objects:
                    subtotal = 0
                    lookup = {vertical_key: vertical_object.id, horizontal_key: horizontal_object.id}
                    subtotal += qs.filter(**lookup).values('id').count()

                    registro[i] = subtotal
                    registro_final[i] += subtotal
                    total += subtotal
                    i += 1

            else:
                # tabela unidemensional
                if vertical_model == CursoCampus:
                    if not colunas:
                        colunas.append('Código')
                        colunas.append('Descrição')
                        colunas.append('Câmpus')
                        colunas.append('Modalidade')
                        colunas.append('QTD')
                    registro[0] = vertical_object.codigo
                    registro[1] = vertical_object.descricao
                    registro[2] = vertical_object.diretoria and vertical_object.diretoria.setor.uo or ''
                    registro[3] = vertical_object.modalidade and vertical_object.modalidade.descricao or ''
                    i = 4
                else:
                    if not colunas:
                        colunas.append(vertical_model._meta.verbose_name)
                        colunas.append('Quantidade')
                    registro[0] = str(vertical_object)
                    i = 1
                self.align_column = i
                lookup = {vertical_key: vertical_object.id}
                total = qs.filter(**lookup).count()

            total_final += total
            registro[i] = total

            registros.append(registro)

        if horizontal_objects.count() and vertical_objects.count() > 1:
            registro_final[int(horizontal_objects.count() + 1)] = total_final
            registros.append(registro_final)

        self.colunas = colunas
        self.registros = registros

    def __str__(self):
        return render_to_string('tabela_resumo_alunos.html', dict(tabela=self))


class TabelaResumoAluno(TabelaBidimensional):
    def __init__(self, qs_alunos):
        super().__init__(
            'Total por Campus/Modalidade',
            qs_alunos,
            vertical_model=UnidadeOrganizacional,
            vertical_key='curso_campus__diretoria__setor__uo__id',
            horizontal_model=Modalidade,
            horizontal_key='curso_campus__modalidade__id',
        )


class TabelaResumoMatriculaPeriodo(TabelaBidimensional):
    def __init__(self, qs):
        super().__init__(
            'Total por Câmpus/Modalidade',
            qs,
            vertical_model=UnidadeOrganizacional,
            vertical_key='aluno__curso_campus__diretoria__setor__uo__id',
            horizontal_model=Modalidade,
            horizontal_key='aluno__curso_campus__modalidade__id',
        )


class TabelaResumoMPCurso(TabelaBidimensional):
    def __init__(self, qs_alunos):
        super().__init__(
            'Total por Curso', qs_alunos, vertical_model=CursoCampus, vertical_key='curso_campus__id', horizontal_model=None, horizontal_key=None
        )


class TabelaPoloAnoNivelEnsino(TabelaBidimensional):
    def __init__(self, qs_alunos):
        super().__init__(
            'Total de Alunos no Polo por Ano de Ingresso',
            qs=qs_alunos,
            vertical_model=Ano,
            vertical_key='ano_letivo',
            horizontal_model=Modalidade,
            horizontal_key='curso_campus__modalidade__id',
        )


class TabelaAlunoPoloNivelEnsino(TabelaBidimensional):
    def __init__(self, qs_alunos):
        super().__init__(
            'Total de Alunos por Polo e Nível de Ensino',
            qs=qs_alunos,
            vertical_model=Polo,
            vertical_key='polo',
            horizontal_model=Modalidade,
            horizontal_key='curso_campus__modalidade__id',
        )


class TabelaAlunoCursoCampusPolo(TabelaBidimensional):
    def __init__(self, qs_alunos):
        super().__init__(
            'Total de Alunos por Curso e Polo', qs=qs_alunos, vertical_model=CursoCampus, vertical_key='curso_campus__id', horizontal_model=Polo, horizontal_key='polo'
        )


class TabelaMPPoloNivelEnsino(TabelaBidimensional):
    def __init__(self, qs):
        super().__init__(
            'Total de Alunos por Polo e Nível de Ensino',
            qs=qs,
            vertical_model=Polo,
            vertical_key='polo',
            horizontal_model=Modalidade,
            horizontal_key='curso_campus__modalidade__id',
        )


class SolicitacaoFilter(SimpleListFilter):
    title = 'tipo'
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        return (('relancamento_etapa', 'Solicitações de Relançamento de Etapa'), ('prorrogacao_etapa', 'Solicitações de Prorrogação de Etapa'))

    def queryset(self, request, queryset):
        if self.value() == 'relancamento_etapa':
            return queryset.filter(solicitacaorelancamentoetapa__isnull=False)
        if self.value() == 'prorrogacao_etapa':
            return queryset.filter(solicitacaoprorrogacaoetapa__isnull=False)


def extrair_matriculas_do_diario(diario):
    if diario:
        alunos = diario.get_alunos_ativos()
        return alunos.values_list('matricula_periodo__aluno__matricula', flat=True)
    return []
