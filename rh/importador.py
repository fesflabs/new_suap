import datetime as data
import logging
import os
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.utils.datetime_safe import datetime

from comum import importador
from comum.utils import extrai_matricula, capitaliza_nome
from djtools.testutils import running_tests
from djtools.utils import mask_cpf, cache_queryset, strptime_or_default, strptime_date_or_default, format_telefone

log = logging.getLogger(__name__)

Configuracao = apps.get_model('comum', 'configuracao')
EstadoCivil = apps.get_model('comum', 'estadocivil')
Log = apps.get_model('comum', 'log')
Pais = apps.get_model('comum', 'pais')
Municipio = apps.get_model('comum', 'municipio')
PessoaEndereco = apps.get_model('comum', 'pessoaendereco')
PessoaTelefone = apps.get_model('comum', 'pessoatelefone')
Ano = apps.get_model('comum', 'ano')
Raca = apps.get_model('comum', 'raca')

if 'edu' in settings.INSTALLED_APPS:
    Cidade = apps.get_model('edu', 'cidade')
    Estado = apps.get_model('edu', 'estado')

Atividade = apps.get_model('rh', 'atividade')
Afastamento = apps.get_model('rh', 'afastamentosiape')
Banco = apps.get_model('rh', 'banco')
CargoClasse = apps.get_model('rh', 'cargoclasse')
CargoEmprego = apps.get_model('rh', 'cargoemprego')
DiplomaLegal = apps.get_model('rh', 'diplomalegal')
Funcao = apps.get_model('rh', 'funcao')
GrupoCargoEmprego = apps.get_model('rh', 'grupocargoemprego')
GrupoOcorrencia = apps.get_model('rh', 'grupoocorrencia')
JornadaTrabalho = apps.get_model('rh', 'jornadatrabalho')
NivelEscolaridade = apps.get_model('rh', 'nivelescolaridade')
Ocorrencia = apps.get_model('rh', 'ocorrencia')
PessoaFisica = apps.get_model('rh', 'pessoafisica')
RegimeJuridico = apps.get_model('rh', 'regimejuridico')
Servidor = apps.get_model('rh', 'servidor')
ServidorOcorrencia = apps.get_model('rh', 'servidorocorrencia')
ServidorReativacaoTemporaria = apps.get_model('rh', 'servidorreativacaotemporaria')
ServidorAfastamento = apps.get_model('rh', 'servidorafastamento')
Setor = apps.get_model('rh', 'setor')
Situacao = apps.get_model('rh', 'situacao')
SubgrupoOcorrencia = apps.get_model('rh', 'subgrupoocorrencia')
Titulacao = apps.get_model('rh', 'titulacao')
Deficiencia = apps.get_model('rh', 'deficiencia')
if 'contracheques' in settings.INSTALLED_APPS:
    Rubrica = apps.get_model('contracheques', 'rubrica', None)

if 'ferias' in settings.INSTALLED_APPS:
    Ferias = apps.get_model('ferias', 'ferias')
    InterrupcaoFerias = apps.get_model('ferias', 'interrupcaoferias')

ServidorFuncaoHistorico = apps.get_model('rh', 'servidorfuncaohistorico')
ServidorSetorHistorico = apps.get_model('rh', 'servidorsetorhistorico')

Pessoa = apps.get_model('rh', 'pessoa')
ServidorSetorLotacaoHistorico = apps.get_model('rh', 'servidorsetorlotacaohistorico')

PCA = apps.get_model('rh', 'pca')
PosicionamentoPCA = apps.get_model('rh', 'posicionamentopca')
JornadaTrabalhoPCA = apps.get_model('rh', 'jornadatrabalhopca')
FormaProvimentoVacancia = apps.get_model('rh', 'formaprovimentovacancia')
RegimeJuridicoPCA = apps.get_model('rh', 'regimejuridicopca')


class ImportadorSIAPE(importador.Importador):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('local_arquivos', 'rh/arquivos_siape')
        kwargs.setdefault('local_refs', os.path.join(settings.BASE_DIR, 'rh/refs'))
        kwargs.setdefault(
            'ordem',
            [
                'atividades',
                'afastamentos',
                'bancos',
                'grupo_cargo_emprego',
                'cargo_emprego',
                'cargo_classe',
                'diploma_legal',
                'funcoes',
                'jornada_trabalho',
                'nivel_escolaridade',
                'pais',
                'regime_juridico',
                'rubrica',
                'estado_civil',
                'grupo_ocorrencia',
                'ocorrencia',
                'situacao_servidor',
                'uo',
                'titulacoes',
                'servidor1',
                'servidor2',
                'servidor3',
                'servidor4',
                'servidor5',
                'servidorafastamentos',
                'historico_ferias',
                'ferias',
                'historico_funcao',
                'historico_setor_siape',
                'servidor_matriculas',
                'pca',
                'posicionamento_pca',
            ],
        )
        super().__init__(*args, **kwargs)

    def _decrescimo_data(self, data, dias):
        if data:
            return data - relativedelta(days=dias)
        return None

    def _get_map_layout_functions(self):
        layouts = dict(
            atividades=self.importar_atividades,
            afastamentos=self.importar_afastamentos,
            bancos=self.importar_bancos,
            grupo_cargo_emprego=self.importar_grupo_cargo_emprego,
            cargo_emprego=self.importar_cargo_emprego,
            cargo_classe=self.importar_cargo_classe,
            diploma_legal=self.importar_diploma_legal,
            funcoes=self.importar_funcoes,
            jornada_trabalho=self.importar_jornada_trabalho,
            pais=self.importar_pais,
            nivel_escolaridade=self.importar_nivel_escolaridade,
            regime_juridico=self.importar_regime_juridico,
            rubrica=self.importar_rubrica,
            situacao_servidor=self.importar_situacao_servidor,
            uo=self.importar_uo,
            estado_civil=self.importar_estado_civil,
            grupo_ocorrencia=self.importar_grupo_ocorrencia,
            ocorrencia=self.importar_ocorrencia,
            titulacoes=self.importar_titulacoes,
            servidor1=self.importar_servidor1,
            servidor2=self.importar_servidor2,
            servidor3=self.importar_servidor3,
            servidor4=self.importar_servidor4,
            servidor5=self.importar_servidor5,
            servidorafastamentos=self.importar_servidor_afastamentos,
            historico_ferias=self.importar_historico_ferias,
            ferias=self.importar_ferias,
            historico_afastamento=self.importar_historico_afastamento,
            historico_funcao=self.importar_historico_funcao,
            historico_setor_siape=self.importar_historico_setor_siape,
            servidor_matriculas=self.importar_servidor_matriculas,
            pca=self.importar_pca,
            posicionamento_pca=self.importar_posicionamento_pca,
        )
        return layouts

    def importar_afastamentos(self, itens):

        for i in itens:
            # foi percebido que alguns tipos de afastamentos estão vindo sem a valor de IT-TP-AFASTAMENTO ou com valores que não são inteiros
            # não é possível cadastrar no suap um afastamento nessas condições
            # TODO estudar o motivo ^^^^^^
            try:
                if i['IT-TP-AFASTAMENTO'] and i['IT-TP-AFASTAMENTO'].isdigit():

                    codigo = i['IT-CO-AFASTAMENTO']

                    kwargs = dict(
                        nome=i['IT-NO-AFASTAMENTO'].strip(),
                        sigla=i['IT-SG-AFASTAMENTO'].strip(),
                        tipo=i['IT-TP-AFASTAMENTO'].strip(),
                        interrompe_pagamento=i['IT-IN-EXCLUI-PAGAMENTO'] == 'S',
                        excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1',
                    )
                    Afastamento.objects.update_or_create(codigo=codigo, defaults=kwargs)
                else:
                    log.info(f'>>> ERRO DE REGISTRO: não foi possível inserir o dicionário {i}, pois o campo IT-TP-AFASTAMENTO não está no padrão aceitável.')
            except Exception as ex:
                log.info(f'>>> ERRO: {ex}')
                continue

    # Esse metodo importa do arquivo Atividades do SIAPE para o SUAP... em algum momento de alguma extracao foi usado a funcao strip no IT-CO-ATIVIDADE
    #    causando duplicacao em registros na tabela.
    #    Essa entidade nao tem sobrescrita no metodo .save()

    def importar_atividades(self, itens):
        for i in itens:
            codigo = i['IT-CO-ATIVIDADE']
            kwargs = dict(nome=i['IT-NO-ATIVIDADE'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            Atividade.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_bancos(self, itens):
        for i in itens:
            codigo = i['IT-CO-BANCO']
            kwargs = dict(nome=i['IT-NO-BANCO'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1', sigla=i['IT-SG-BANCO'].strip())
            Banco.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_grupo_cargo_emprego(self, itens):
        for i in itens:
            codigo = i['IT-CO-GRUPO-CARGO-EMPREGO']
            kwargs = dict(nome=i['IT-NO-GRUPO-CARGO-EMPREGO'].strip(), sigla=i['IT-SG-GRUPO-CARGO-EMPREGO'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            if 'MAG' in i['IT-NO-GRUPO-CARGO-EMPREGO'].strip():
                kwargs['categoria'] = 'docente'

            GrupoCargoEmprego.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_cargo_emprego(self, itens):
        grupo_cargo_emprego_cache = cache_queryset(GrupoCargoEmprego.objects.all(), 'codigo', 'id')
        for i in itens:
            codigo = i['GR-IDEN-CARGO-EMPREGO']
            kwargs = dict(
                grupo_cargo_emprego_id=grupo_cargo_emprego_cache[i['GR-IDEN-CARGO-EMPREGO'][:3]],
                excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1',
                nome=i['IT-NO-CARGO-EMPREGO'].strip(),
                sigla_escolaridade=i['IT-SG-ESCOLARIDADE'].strip(),
            )
            CargoEmprego.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_cargo_classe(self, itens):
        for i in itens:
            codigo = i['IT-CO-CLASSE']
            kwargs = dict(nome=i['IT-NO-CLASSE'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            CargoClasse.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_diploma_legal(self, itens):
        for i in itens:
            codigo = i['IT-CO-DIPLOMA-LEGAL']
            kwargs = dict(nome=i['IT-NO-DIPLOMA-LEGAL'].strip(), sigla=i['IT-SG-DIPLOMA-LEGAL'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            DiplomaLegal.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_funcoes(self, itens):
        for i in itens:
            codigo = i['IT-SG-FUNCAO'].strip()
            kwargs = dict(nome=i['IT-NO-FUNCAO'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            Funcao.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_jornada_trabalho(self, itens):
        for i in itens:
            codigo = i['IT-CO-JORNADA-TRABALHO']
            kwargs = dict(nome=i['IT-NO-JORNADA-TRABALHO'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            JornadaTrabalho.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_nivel_escolaridade(self, itens):
        for i in itens:
            codigo = i['IT-CO-NIVEL-ESCOLARIDADE']
            kwargs = dict(nome=i['IT-NO-NIVEL-ESCOLARIDADE'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            NivelEscolaridade.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_pais(self, itens):
        for i in itens:
            codigo = i['IT-CO-PAIS']
            kwargs = dict(nome=i['IT-NO-PAIS'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1', equiparado=i['IT-IN-PAIS-EQUIPARADO'] == 'S')
            Pais.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_regime_juridico(self, itens):
        for i in itens:
            sigla = i['IT-SG-REGIME-JURIDICO']
            kwargs = dict(nome=i['IT-NO-REGIME-JURIDICO'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            RegimeJuridico.objects.update_or_create(sigla=sigla, defaults=kwargs)

    def importar_rubrica(self, itens):
        if 'contracheques' in settings.INSTALLED_APPS:
            for i in itens:
                codigo = i['IT-CO-RUBRICA']
                kwargs = dict(nome=i['IT-NO-RUBRICA'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
                Rubrica.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_estado_civil(self, itens):
        for i in itens:
            codigo_siape = i['IT-CO-ESTADO-CIVIL']
            kwargs = dict(nome=i['IT-NO-ESTADO-CIVIL'], ativo=i['IT-IN-STATUS-REGISTRO-TABELA'] == '0')
            EstadoCivil.objects.update_or_create(codigo_siape=codigo_siape, defaults=kwargs)

    def importar_grupo_ocorrencia(self, itens):
        for i in itens:
            codigo = i['IT-CO-GRUPO-OCORRENCIA']
            kwargs = dict(nome=i['IT-NO-GRUPO-OCORRENCIA'], excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            GrupoOcorrencia.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_ocorrencia(self, itens):
        grupo_ocorrencia_cache = cache_queryset(GrupoOcorrencia.objects.all(), 'codigo', 'id')
        for i in itens:
            codigo = i['GR-IDEN-OCORRENCIA']
            kwargs = dict(
                nome=i['IT-NO-OCORRENCIA'],
                grupo_ocorrencia=GrupoOcorrencia(pk=grupo_ocorrencia_cache[i['GR-IDEN-OCORRENCIA'][0:2]]),
                excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1',
                interrompe_pagamento=i['IT-IN-OCORRENCIA-EXCL-PGTO'] == 'S',
            )
            Ocorrencia.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_situacao_servidor(self, itens):
        for i in itens:
            codigo = i['IT-CO-SITUACAO-SERVIDOR']
            kwargs = dict(nome=i['IT-NO-SITUACAO-SERVIDOR'].strip(), nome_siape=i['IT-NO-SITUACAO-SERVIDOR'].strip(), excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1')
            Situacao.objects.update_or_create(codigo=codigo, defaults=kwargs)

    def importar_uo(self, itens):

        espelhar_setor = False
        # Se for a primeira vez em que o setor vai ser cria uma arvore de setores SUAP identica a arvore SIAPE.
        # Pressupõe-se que o usuario deseja árvores idênticas apenas para uma primeira importação. A partir dai, ele
        # começa a trabalhar na árvore SUAP editando-a independentemente. Poupa trabalho no cadastro de setores.
        if Configuracao.get_valor_por_chave('comum', 'setores') == 'SUAP' and Setor.suap.all().count() == 0:
            espelhar_setor = True

        # Primeiro salve os setores.
        for i in itens:
            codigo = i['GR-IDENTIFICACAO-UORG'][-9:]
            sigla = i['IT-SG-UNIDADE-ORGANIZACIONAL'].strip()
            kwargs = dict(excluido=i['IT-IN-STATUS-REGISTRO-TABELA'] == '1', nome=i['IT-NO-UNIDADE-ORGANIZACIONAL'].strip())
            kwargs_siape = kwargs
            kwargs_siape['sigla'] = sigla
            Setor.siape.update_or_create(codigo=codigo, defaults=kwargs_siape)
            if espelhar_setor:
                Setor.objects.update_or_create(sigla=sigla, defaults=kwargs)

        # Depois inclua os vinculos separadamente para nao correr os risco de fazer
        # referencia a um setor que ainda nao existe
        for i in itens:
            excluido = i['IT-IN-STATUS-REGISTRO-TABELA'] == '1'
            if not excluido:
                codigo = i['GR-IDENTIFICACAO-UORG'][-9:]
                nome = i['IT-NO-UNIDADE-ORGANIZACIONAL'].strip()
                sigla = i['IT-SG-UNIDADE-ORGANIZACIONAL'].strip()
                setor = Setor.siape.get(codigo=codigo, nome=nome, sigla=sigla)

                if espelhar_setor:
                    setor_espelhado = Setor.suap.get(nome=nome, sigla=sigla)

                vinculo = i['IT-CO-UORG-VINCULACAO'].strip()[-9:]

                # correção da mudança de árvore de setor ocasinado pela migração do eorg (apenas IFRN)
                instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla') or ''
                if instituicao_sigla == 'IFRN':
                    sigla_re = Configuracao.get_valor_por_chave('comum', 'reitoria_sigla')

                    if vinculo == '000000001' and sigla != sigla_re:
                        s = Setor.siape.get(sigla=sigla_re)
                        # ajustando o vinculo de todos os setores, alterando o vinculo de 1 para o vinculo da reitoria
                        vinculo = s.codigo

                if vinculo == '000999999' or int(vinculo) == 0:
                    superior = None
                    if espelhar_setor:
                        superior_espelhado = None
                else:
                    superior = Setor.siape.get(codigo=vinculo)
                    pai_do_superior = superior.superior
                    if espelhar_setor:
                        if pai_do_superior:
                            superior_espelhado = Setor.suap.get(sigla=superior.sigla, superior__sigla=pai_do_superior.sigla)
                        else:
                            superior_espelhado = Setor.suap.get(sigla=superior.sigla)

                setor.superior = superior
                setor.save()
                if espelhar_setor:
                    setor_espelhado.superior = superior_espelhado
                    setor_espelhado.save()

    def calc_caches(self, servidores=True, force_recache=False):

        if force_recache or running_tests():
            force_recache = True

        if force_recache or servidores or not hasattr(self, 'servidores_cache'):
            self.servidores_cache = cache_queryset(Servidor.objects.all(), 'matricula', 'id')

        if force_recache or (not hasattr(self, 'has_cache') or not self.has_cache):
            self.has_cache = True
            self.estado_civil_cache = cache_queryset(EstadoCivil.objects.all(), 'codigo_siape', 'id')
            self.regime_juridico_cache = cache_queryset(RegimeJuridico.objects.all(), 'sigla', 'id')
            self.nivel_escolaridade_cache = cache_queryset(NivelEscolaridade.objects.all(), 'codigo', 'id')
            self.jornada_de_trabalho_cache = cache_queryset(JornadaTrabalho.objects.all(), 'codigo', 'id')
            self.atividades_cache = cache_queryset(Atividade.objects.all(), 'codigo', 'id')
            self.funcoes_cache = cache_queryset(Funcao.objects.all(), 'codigo', 'id')
            self.bancos_cache = cache_queryset(Banco.objects.all(), 'codigo', 'id')
            self.situacoes_cache = cache_queryset(Situacao.objects.all(), 'codigo', 'id')
            self.pais_cache = cache_queryset(Pais.objects.all(), 'codigo', 'id')
            self.setores_cache = cache_queryset(Setor.siape.all(), 'codigo', 'id')
            self.grupo_cargo_emprego_cache = cache_queryset(GrupoCargoEmprego.objects.all(), 'codigo', 'id')
            self.cargo_emprego_cache = cache_queryset(CargoEmprego.objects.all(), 'codigo', 'id')
            self.cargo_classe_cache = cache_queryset(CargoClasse.objects.all(), 'codigo', 'id')
            self.grupo_ocorrencia_cache = cache_queryset(GrupoOcorrencia.objects.all(), 'codigo', 'id')
            self.ocorrencia_cache = cache_queryset(Ocorrencia.objects.all(), 'codigo', 'id')
            self.diploma_legal_cache = cache_queryset(DiplomaLegal.objects.all(), 'codigo', 'id')
            self.titulacao_cache = cache_queryset(Titulacao.objects.all(), 'codigo', 'id')
            self.raca_cache = cache_queryset(Raca.objects.all(), 'codigo_siape', 'id')
            self.deficiencia_cache = cache_queryset(Deficiencia.objects.all(), 'codigo', 'id')
            self.afastamentos_cache = cache_queryset(Afastamento.objects.all(), 'codigo', 'id')

    # INICIAR IMPORTACAO SERVIDOR 1
    def importar_servidor1(self, itens):
        self.calc_caches()
        for i in itens:
            try:
                matricula = extrai_matricula(i['GR-MATRICULA'])
                nome_servidor = capitaliza_nome(i['IT-NO-SERVIDOR'])
                args = dict(
                    matricula=matricula,
                    situacao_id=self.situacoes_cache[i['IT-CO-SITUACAO-SERVIDOR']],
                    sistema_origem='SIAPE',
                    cpf=mask_cpf(i['IT-NU-CPF']),
                    nome=nome_servidor,
                    nome_registro=nome_servidor,
                    nome_mae=capitaliza_nome(i['IT-NO-MAE']),
                    pis_pasep=i['IT-NU-PIS-PASEP'],
                    pagto_agencia=i['IT-CO-AGENCIA-BANCARIA-PGTO-SERV'],
                    pagto_ccor=i['IT-NU-CCOR-PGTO-SERVIDOR'],
                    data_exclusao_instituidor=strptime_or_default(i['IT-DA-EXCLUSAO-INSTITUIDOR'], '%Y%m%d'),
                )

                if int(i['IT-CO-ESTADO-CIVIL']):
                    args['estado_civil_id'] = self.estado_civil_cache.get(i['IT-CO-ESTADO-CIVIL'], None)

                if i['IT-SG-REGIME-JURIDICO'].strip():
                    args['regime_juridico_id'] = self.regime_juridico_cache.get(i['IT-SG-REGIME-JURIDICO'], None)

                if i['IT-CO-BANCO-PGTO-SERVIDOR'] and int(i['IT-CO-BANCO-PGTO-SERVIDOR']):
                    args['pagto_banco_id'] = self.bancos_cache.get(i['IT-CO-BANCO-PGTO-SERVIDOR'], None)

                if i['IT-CO-NACIONALIDADE'] and int(i['IT-CO-NACIONALIDADE']):
                    args['nacionalidade'] = int(i['IT-CO-NACIONALIDADE'])

                # Preenche o país de origem
                if i['IT-CO-PAIS'] and int(i['IT-CO-PAIS']):
                    args['pais_origem_id'] = self.pais_cache.get(i['IT-CO-PAIS'], None)

                # Equivalente ao metodo atualizar lotação
                if int(i['IT-CO-UORG-LOTACAO-SERVIDOR']):
                    args['setor_lotacao_id'] = self.setores_cache.get(i['IT-CO-UORG-LOTACAO-SERVIDOR'], None)
                    args['setor_lotacao_data_ocupacao'] = strptime_or_default(i['IT-DA-LOTACAO'], '%Y%m%d')
                else:
                    args['setor_lotacao'] = None
                    args['setor_lotacao_data_ocupacao'] = None

                # Equivalente ao atualizar cargo emprego
                if int(i['IT-CO-GRUPO-CARGO-EMPREGO']):
                    args['cargo_emprego_id'] = self.cargo_emprego_cache.get(i['IT-CO-GRUPO-CARGO-EMPREGO'] + i['IT-CO-CARGO-EMPREGO'], None)
                    args['cargo_classe_id'] = self.cargo_classe_cache.get(i['IT-CO-CLASSE'], None)
                    args['cargo_emprego_data_ocupacao'] = strptime_or_default(i['IT-DA-OCUPACAO-CARGO-EMPREGO'], '%Y%m%d')
                    args['cargo_emprego_data_saida'] = strptime_or_default(i['IT-DA-SAIDA-CARGO-EMPREGO'], '%Y%m%d')

                if i['IT-CO-PADRAO'].isdigit():
                    args['nivel_padrao'] = i['IT-CO-PADRAO']
                else:
                    args['nivel_padrao'] = i['IT-CO-NIVEL']

                servidor = Servidor.objects.update_or_create(matricula=matricula, defaults=args)[0]
                self._atualizar_ocorrencia_exclusao(servidor, i)
                # self._atualizar_ocorrencia_afastamento(servidor, i)
                self._atualizar_ocorrencia_inatividade(servidor, i)

            except Exception as ex:
                log.error(f'Erro ao processar dados: [{matricula}] {nome_servidor}: \n Error: {ex} \n Array: {i}')

    def _atualizar_ocorrencia_inatividade(self, servidor, item):
        if int(item['IT-CO-GRUPO-OCOR-INATIVIDADE']):
            kwargs = dict(diploma_legal_data=strptime_or_default(item['IT-DA-PUBL-DIPL-INATIVIDADE'], '%Y%m%d'), diploma_legal_num=item['IT-NU-DIPL-INATIVIDADE'])
            if int(item['IT-CO-DIPL-INATIVIDADE']):
                kwargs['diploma_legal_id'] = self.diploma_legal_cache[item['IT-CO-DIPL-INATIVIDADE']]
            else:
                kwargs['diploma_legal_id'] = None

            ocorrencia_id = self.ocorrencia_cache[item['IT-CO-GRUPO-OCOR-INATIVIDADE'] + item['IT-CO-OCOR-INATIVIDADE']]
            data = strptime_or_default(item['IT-DA-OCOR-INATIVIDADE-SERV'], '%Y%m%d')

            ok = False
            try:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data, defaults=kwargs)
                ok = True
            except MultipleObjectsReturned:
                ServidorOcorrencia.objects.filter(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data).delete()
                ok = False
            if not ok:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data, defaults=kwargs)

    def _atualizar_ocorrencia_exclusao(self, servidor, item):
        """ Atualiza a ocorrência de exclusão
            Retorna uma tupla de  (servidorocorrencia, novo) onde novo é um boolean
            especificando se servidorocorrencia foi criado
            Se houver uma ocorrencia de exclusao por falta de recadastramento, mas não vier uma exclusão em item,
            o servidor será reativado. Isso é comum para os casos em que um aposentado volta a fazer o recadastrado.
        """

        def excluir_servidor(servidor, item):
            hoje = datetime.today()
            subgrupo = SubgrupoOcorrencia.objects.get_or_create(descricao='EXCLUSAO')[0]
            kwargs = dict(diploma_legal_data=strptime_or_default(item['IT-DA-PUBL-DIPL-EXCLUSAO'], '%Y%m%d'), diploma_legal_num=item['IT-NU-DIPL-EXCLUSAO'])

            kwargs['diploma_legal_id'] = self.diploma_legal_cache.get(item['IT-CO-DIPL-EXCLUSAO'], None)
            ocorrencia_id = self.ocorrencia_cache[item['IT-CO-GRUPO-OCOR-EXCLUSAO'] + item['IT-CO-OCOR-EXCLUSAO']]
            data = strptime_or_default(item['IT-DA-OCOR-EXCLUSAO-SERV'], '%Y%m%d')

            try:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data, subgrupo=subgrupo, defaults=kwargs)
                ok = True
            except MultipleObjectsReturned:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data, subgrupo=subgrupo).delete()
                ok = False
            if not ok:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data, subgrupo=subgrupo, defaults=kwargs)

            if servidor.servidorreativacaotemporaria_set.filter(data_inicio__lte=hoje, data_fim__gte=hoje).exists():
                Servidor.objects.filter(id=servidor.id).update(excluido=False)
            else:
                Servidor.objects.filter(id=servidor.id).update(excluido=True)

            historico_setores_servidor = ServidorSetorHistorico.objects.filter(servidor=servidor).order_by('-data_inicio_no_setor')
            if historico_setores_servidor.exists():
                setor_mais_atual = historico_setores_servidor[0]
                if not setor_mais_atual.data_fim_no_setor:
                    setor_mais_atual.data_fim_no_setor = data
                    setor_mais_atual.save()

        def reativar_servidor(servidor, item):
            ServidorOcorrencia.objects.filter(servidor=servidor, ocorrencia__nome__unaccent__icontains='falta recadastramento').delete()
            #            Na regra que nos foi passado pelo RH antes um servidor que foi excluido, salvo por falta de recadastramento, nao voltava a ativa com mesma matricula.
            #            Porem foi visto que existem casos de servidores excluidos q voltaram a ativa com mesma matricula
            #            ServidorOcorrencia.objects.filter(servidor=servidor, ocorrencia__grupo_ocorrencia__nome=u'EXCLUSAO').delete()
            Servidor.objects.filter(id=servidor.id).update(excluido=False)

        cod_grupo_ocorrencia_exclusao = int(item['IT-CO-GRUPO-OCOR-EXCLUSAO'])
        # verificando se existe um código de grupo de ocorrência de exclusão e checa se o código não é 0 (zero). Caso o código não seja zero, ou seja
        # existe um código valido de exclusão, chama-se a definição para excluir o servidor no suap.
        if cod_grupo_ocorrencia_exclusao != 0:
            excluir_servidor(servidor, item)

        # verificando se o código de grupo de ocorrência de exclusão é igual a zero e checa se o servidor está como excluído no suap. Caso positivo,
        # reativa o servidor.
        if cod_grupo_ocorrencia_exclusao == 0 and servidor.excluido is True:
            reativar_servidor(servidor, item)

    def _atualizar_ocorrencia_afastamento(self, servidor, item):
        if int(item['IT-CO-GRUPO-OCOR-AFASTAMENTO']):
            kwargs = dict(
                data_termino=strptime_or_default(item['IT-DA-TERMINO-OCOR-AFASTAMENTO'], '%Y%m%d'),
                diploma_legal_data=strptime_or_default(item['IT-DA-PUBL-DIPL-AFASTAMENTO'], '%Y%m%d'),
                diploma_legal_num=item['IT-NU-DIPL-AFASTAMENTO'],
            )
            data_inicio = strptime_or_default(item['IT-DA-INICIO-OCOR-AFASTAMENTO'], '%Y%m%d')
            if data_inicio > datetime.today():
                return
            kwargs['diploma_legal_id'] = self.diploma_legal_cache.get(item['IT-CO-DIPL-AFASTAMENTO'], None)
            ocorrencia_id = self.ocorrencia_cache[item['IT-CO-GRUPO-OCOR-AFASTAMENTO'] + item['IT-CO-OCOR-AFASTAMENTO']]

            ok = False
            try:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data_inicio, defaults=kwargs)
                ok = True
            except MultipleObjectsReturned:
                ServidorOcorrencia.objects.filter(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data_inicio).delete()
                ok = False

            if not ok:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, data=data_inicio, defaults=kwargs)

    def importar_servidor2(self, itens):
        self.calc_caches(servidores=True)
        for i in itens:
            try:
                servidor_id = self.servidores_cache[extrai_matricula(i['GR-MATRICULA'])]
            except Exception:
                continue
            args = dict(
                nascimento_data=strptime_or_default(i['IT-DA-NASCIMENTO'], '%Y%m%d'),
                sexo=i['IT-CO-SEXO'],
                qtde_depend_ir=int(i['IT-QT-DEPENDENTE-IR']),
                ctps_numero=i['IT-NU-CARTEIRA-TRABALHO'],
                ctps_serie=i['IT-NU-SERIE-CARTEIRA-TRABALHO'],
                ctps_uf=i['IT-SG-UF-CTRA-SERVIDOR'].strip(),
                ctps_data_prim_emprego=strptime_or_default(i['IT-DA-PRIMEIRO-EMPREGO'], '%Y%m%d'),
                data_cadastro_siape=strptime_or_default(i['IT-DA-CADASTRAMENTO-SERVIDOR'], '%Y%m%d'),
            )
            if int(i['IT-CO-NIVEL-ESCOLARIDADE']):
                args['nivel_escolaridade_id'] = self.nivel_escolaridade_cache.get(i['IT-CO-NIVEL-ESCOLARIDADE'], None)
            if int(i['IT-CO-JORNADA-TRABALHO']):
                args['jornada_trabalho_id'] = self.jornada_de_trabalho_cache.get(i['IT-CO-JORNADA-TRABALHO'], None)

            # TODO verificar onde adicionar essa informação. ver se pode ser colocada em outros servidores (1,3,4 ou 5)

            # num_processo_aposentadoria = i['IT-NU-PROCESSO-APOSENTADORIA'].strip()
            # if num_processo_aposentadoria.strip('0'):
            #     args['num_processo_aposentadoria'] = num_processo_aposentadoria.lstrip('0')
            # else:
            #     args['num_processo_aposentadoria'] = ''
            # numerador_prop_aposentadoria = int(i['IT-NU-NUMERADOR-PROP'])
            # if numerador_prop_aposentadoria:
            #     args['numerador_prop_aposentadoria'] = numerador_prop_aposentadoria
            # denominador_prop_aposentadoria = i['IT-NU-DENOMINADOR-PROP']
            # if denominador_prop_aposentadoria:
            #     args['denominador_prop_aposentadoria'] = denominador_prop_aposentadoria

            '''
            No extrator do SIAPE, a coluna IT-DA-INGRESSO-NOVA-FUNCAO e IT-DA-INGRESSO-FUNCAO sempre vem preenchindo com a data de inicio na função ou nova função,
            ou com zeros quando o servidor nunca teve uma função.
            '''
            # nova função
            if int(i['IT-DA-INGRESSO-NOVA-FUNCAO']) > int(i['IT-DA-INGRESSO-FUNCAO']):
                funcao_id = self.funcoes_cache[i['IT-SG-NOVA-FUNCAO'].strip()]
                args['funcao_id'] = funcao_id

                args['funcao_codigo'] = nivel = i['IT-CO-NIVEL-NOVA-FUNCAO'].lstrip('0')
                args['funcao_opcao'] = i['IT-IN-OPCAO-FUNCAO'] == 'S'
                args['funcao_data_ocupacao'] = data_inicio_funcao = strptime_or_default(i['IT-DA-INGRESSO-NOVA-FUNCAO'], '%Y%m%d')
                args['funcao_data_saida'] = data_fim_funcao = self._decrescimo_data(strptime_or_default(i['IT-DA-SAIDA-NOVA-FUNCAO'], '%Y%m%d'), 1)

                args['setor_funcao_id'] = None
                if int(i['IT-CO-UORG-NOVA-FUNCAO']):
                    args['setor_funcao_id'] = setor_funcao_id = self.setores_cache[i['IT-CO-UORG-NOVA-FUNCAO']]

                args['funcao_atividade_id'] = None
                if int(i['IT-CO-ATIVIDADE-NOVA-FUNCAO']):
                    args['funcao_atividade_id'] = atividade_funcao_id = self.atividades_cache[i['IT-CO-ATIVIDADE-NOVA-FUNCAO']]

                # salvando
                if funcao_id and data_inicio_funcao and setor_funcao_id:
                    args_historicofuncao = dict(
                        servidor_id=servidor_id,
                        data_inicio_funcao=data_inicio_funcao,
                        nivel=nivel,
                        data_fim_funcao=data_fim_funcao,
                        funcao_id=funcao_id,
                        setor_id=setor_funcao_id,
                        atividade_id=atividade_funcao_id,
                    )
                    ServidorFuncaoHistorico.objects.update_or_create(servidor__pk=servidor_id, data_inicio_funcao=data_inicio_funcao, defaults=args_historicofuncao)

            # função
            elif int(i['IT-DA-INGRESSO-NOVA-FUNCAO']) < int(i['IT-DA-INGRESSO-FUNCAO']):
                if not int(i['IT-DA-SAIDA-FUNCAO']):
                    args['funcao_id'] = funcao_id = self.funcoes_cache[i['IT-SG-FUNCAO'].strip()]
                    args['funcao_codigo'] = nivel = i['IT-CO-NIVEL-FUNCAO'].lstrip('0')
                    args['funcao_opcao'] = i['IT-IN-OPCAO-FUNCAO'] == 'S'
                    args['funcao_data_ocupacao'] = data_inicio_funcao = strptime_or_default(i['IT-DA-INGRESSO-FUNCAO'], '%Y%m%d')
                    args['funcao_data_saida'] = data_fim_funcao = self._decrescimo_data(strptime_or_default(i['IT-DA-SAIDA-FUNCAO'], '%Y%m%d'), 1)

                    args['setor_funcao_id'] = None
                    if int(i['IT-CO-UORG-FUNCAO']):
                        args['setor_funcao_id'] = setor_funcao_id = self.setores_cache[i['IT-CO-UORG-FUNCAO']]
                    args['funcao_atividade_id'] = None
                    if int(i['IT-CO-ATIVIDADE-FUNCAO']):
                        args['funcao_atividade_id'] = atividade_funcao_id = self.atividades_cache[i['IT-CO-ATIVIDADE-FUNCAO']]
                else:
                    args['funcao_id'] = args['funcao_codigo'] = args['funcao_opcao'] = args['funcao_data_ocupacao'] = args['funcao_data_saida'] = args['setor_funcao_id'] = args[
                        'funcao_atividade_id'
                    ] = None

                    funcao_id = self.funcoes_cache[i['IT-SG-FUNCAO'].strip()]
                    nivel = i['IT-CO-NIVEL-FUNCAO'].lstrip('0')
                    data_inicio_funcao = strptime_or_default(i['IT-DA-INGRESSO-FUNCAO'], '%Y%m%d')
                    data_fim_funcao = self._decrescimo_data(strptime_or_default(i['IT-DA-SAIDA-FUNCAO'], '%Y%m%d'), 1)
                    atividade_funcao_id = None
                    if int(i['IT-CO-ATIVIDADE-FUNCAO']):
                        atividade_funcao_id = self.atividades_cache[i['IT-CO-ATIVIDADE-FUNCAO']]
                    setor_funcao_id = None
                    if int(i['IT-CO-UORG-FUNCAO']):
                        setor_funcao_id = self.setores_cache[i['IT-CO-UORG-FUNCAO']]

                # salvando
                if funcao_id and data_inicio_funcao and setor_funcao_id:
                    args_historicofuncao = dict(
                        servidor_id=servidor_id,
                        data_inicio_funcao=data_inicio_funcao,
                        nivel=nivel,
                        data_fim_funcao=data_fim_funcao,
                        funcao_id=funcao_id,
                        setor_id=setor_funcao_id,
                        atividade_id=atividade_funcao_id,
                    )
                    ServidorFuncaoHistorico.objects.update_or_create(servidor__pk=servidor_id, data_inicio_funcao=data_inicio_funcao, defaults=args_historicofuncao)

            Servidor.objects.filter(id=servidor_id).update(**args)
            self._atualizar_ingresso_orgao(servidor_id, i)
            self._atualizar_ingresso_servico_publico(servidor_id, i)

    def _atualizar_ingresso_orgao(self, servidor_id, item):
        if int(item['IT-CO-GRUPO-OCOR-INGR-ORGAO']):
            kwargs = dict(diploma_legal_data=strptime_or_default(item['IT-DA-PUBL-DIPL-INGR-ORGAO'], '%Y%m%d'), diploma_legal_num=item['IT-NU-DIPL-INGR-ORGAO'].strip())
            kwargs['diploma_legal_id'] = self.diploma_legal_cache.get(item['IT-CO-DIPL-INGR-ORGAO'], None)

            ocorrencia_id = self.ocorrencia_cache[item['IT-CO-GRUPO-OCOR-INGR-ORGAO'] + item['IT-CO-OCOR-INGR-ORGAO']]
            subgrupo = SubgrupoOcorrencia.get_or_create(descricao='INCLUSAO NO ORGAO')[0]
            data = strptime_or_default(item['IT-DA-OCOR-INGR-ORGAO-SERV'], '%Y%m%d')

            ok = False
            try:
                ServidorOcorrencia.objects.update_or_create(servidor_id=servidor_id, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data, defaults=kwargs)
                ok = True
            except MultipleObjectsReturned:
                ServidorOcorrencia.objects.filter(servidor_id=servidor_id, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data).delete()
                ok = False

            if not ok:
                ServidorOcorrencia.objects.update_or_create(servidor_id=servidor_id, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data, defaults=kwargs)

    def _atualizar_ingresso_servico_publico(self, servidor_id, item):
        if int(item['IT-CO-GRUPO-OCOR-INGR-SPUB']):
            kwargs = dict(diploma_legal_data=strptime_or_default(item['IT-DA-PUBL-DIPL-INGR-SPUB'], '%Y%m%d'), diploma_legal_num=item['IT-NU-DIPL-INGR-SPUB'].strip())
            kwargs['diploma_legal_id'] = self.diploma_legal_cache.get(item['IT-CO-DIPL-INGR-SPUB'], None)

            ocorrencia_id = self.ocorrencia_cache[item['IT-CO-GRUPO-OCOR-INGR-SPUB'] + item['IT-CO-OCOR-INGR-SPUB']]
            subgrupo = SubgrupoOcorrencia.get_or_create(descricao='INCLUSAO NO SERVICO PUBLICO')[0]
            data = strptime_or_default(item['IT-DA-OCOR-INGR-SPUB-SERV'], '%Y%m%d')

            ok = False
            try:
                ServidorOcorrencia.objects.update_or_create(servidor_id=servidor_id, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data, defaults=kwargs)
                ok = True
            except MultipleObjectsReturned:
                ServidorOcorrencia.objects.filter(servidor_id=servidor_id, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data).delete()
                ok = False

            if not ok:
                ServidorOcorrencia.objects.update_or_create(servidor_id=servidor_id, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data, defaults=kwargs)

    def _atualizar_ingresso_servico_publico_posse(self, servidor, item):
        if int(item['IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE']):
            kwargs = dict(diploma_legal_data=strptime_or_default(item['IT-DA-PUBL-DIPL-INGR-SPUB-POSSE'], '%Y%m%d'), diploma_legal_num=item['IT-NU-DIPL-INGR-SPUB-POSSE'].strip())
            if int(item['IT-CO-DIPL-INGR-SPUB-POSSE']):
                kwargs['diploma_legal'] = self.diploma_legal_cache[item['IT-CO-DIPL-INGR-SPUB-POSSE']]
            else:
                kwargs['diploma_legal'] = None

            ocorrencia_id = self.ocorrencia_cache[item['IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE'] + item['IT-CO-OCOR-INGR-SPUB-POSSE']]
            subgrupo, created = SubgrupoOcorrencia.get_or_create(descricao='POSSE NO SERVICO PUBLICO')
            data = strptime_or_default(item['IT-DA-OCOR-INGR-SPUB-POSSE'], '%Y%m%d')

            ok = False
            try:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data, defaults=kwargs)
                ok = True
            except MultipleObjectsReturned:
                ServidorOcorrencia.objects.filter(servidor=servidor, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data).delete()
                ok = False

            if not ok:
                ServidorOcorrencia.objects.update_or_create(servidor=servidor, ocorrencia_id=ocorrencia_id, subgrupo=subgrupo, data=data, defaults=kwargs)

    def importar_servidor3(self, itens):
        self.calc_caches(servidores=True)
        for i in itens:
            try:
                servidor_id = self.servidores_cache[extrai_matricula(i['GR-MATRICULA'])]
            except Exception:
                continue
            kwargs = dict(
                matricula_anterior=extrai_matricula(i['IT-NU-MATRICULA-ANTERIOR']),
                # Dados do RG
                rg=i['IT-CO-REGISTRO-GERAL'].strip(),
                rg_orgao=i['IT-SG-ORGAO-EXPEDIDOR-IDEN'].strip(),
                rg_data=strptime_or_default(i['IT-DA-EXPEDICAO-IDEN'], '%Y%m%d'),
                rg_uf=i['IT-SG-UF-IDEN'],
                data_obito=strptime_or_default(i['IT-DA-OBITO'], '%Y%m%d'),
                # TODO: O Titulo Eleitoral no arquivo do SIAPE tem 13 caracteres,
                # mas modelamos com 12,
                # como o primeiro do arquivo é sempre ZERO, deixamos assim mesmo.
                titulo_numero=i['IT-NU-TITULO-ELEITOR'][1:],
                opera_raio_x=bool(int(i['IT-IN-OPERADOR-RAIOX'])),
                codigo_vaga=i['IT-CO-VAGA'],
            )

            id_setor_exercicio = i['IT-CO-UORG-EXERCICIO-SERV']

            # corrigindo setor de exercicio (não pode ser o raiz - para IFRN)
            instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla') or ''
            if instituicao_sigla == 'IFRN':
                if id_setor_exercicio == '000000001':
                    sigla_re = Configuracao.get_valor_por_chave('comum', 'reitoria_sigla')
                    setor_exercicio = Setor.siape.get(sigla=sigla_re)
                    id_setor_exercicio = setor_exercicio.codigo

            kwargs['setor_exercicio_id'] = self.setores_cache.get(id_setor_exercicio, None)
            kwargs['titulacao_id'] = self.titulacao_cache.get(i['IT-CO-TITULACAO-FORMACAO-RH'], None)

            Servidor.objects.filter(id=servidor_id).update(**kwargs)

    def _atualizar_endereco(self, servidor_id, item):
        PessoaEndereco.objects.filter(pessoa__id=servidor_id).delete()
        municipio = None
        # TODO: Quando migrar todos os arquivos de CIDADE, ESTADO e PAIS do edu rever esse if
        if 'edu' in settings.INSTALLED_APPS:
            estado = Estado.get_estado_por_sigla(item['IT-SG-UF-SERV-DISPONIVEL'])
            if Cidade.objects.filter(nome=item['IT-NO-MUNICIPIO'], estado=estado).exists():
                municipio = Municipio.get_or_create(item['IT-NO-MUNICIPIO'], item['IT-SG-UF-SERV-DISPONIVEL'])[0]
        else:
            municipio = Municipio.get_or_create(item['IT-NO-MUNICIPIO'], item['IT-SG-UF-SERV-DISPONIVEL'])[0]
        PessoaEndereco.objects.get_or_create(
            pessoa_id=servidor_id,
            logradouro=item['IT-NO-LOGRADOURO'],
            numero=item['IT-NU-ENDERECO'],
            complemento=item['IT-NU-COMPLEMENTO-ENDERECO'],
            bairro=item['IT-NO-BAIRRO'],
            municipio=municipio,
            cep=item['IT-CO-CEP'],
        )

    def _atualizar_telefone(self, servidor_id, item):
        PessoaTelefone.objects.filter(pessoa__id=servidor_id).delete()
        fone_numero = item['IT-NU-TELEFONE'].strip()
        fone_ddd = item['IT-NU-DDD-TELEFONE'].strip()
        fone_ramal = item['IT-NU-RAMAL-TELEFONE'].strip()
        if fone_numero:
            telefone_formatado = format_telefone(fone_ddd, fone_numero)
            telefone = PessoaTelefone(pessoa=Pessoa(id=servidor_id), numero=telefone_formatado, ramal=fone_ramal)
            telefone.save()
        fone_numero_movel = item['IT-NU-TELEFONE-MOVEL'].strip()
        fone_ddd_movel = item['IT-NU-DDD-TELEFONE-MOVEL'].strip()
        if fone_numero_movel:
            telefone_formatado_movel = format_telefone(fone_ddd_movel, fone_numero_movel)
            telefone_movel = PessoaTelefone(pessoa=Pessoa(id=servidor_id), numero=telefone_formatado_movel)
            telefone_movel.save()

    def importar_servidor4(self, itens):
        self.calc_caches(servidores=True)
        for i in itens:
            try:
                servidor_id = self.servidores_cache[extrai_matricula(i['GR-MATRICULA-SERV-DISPONIVEL'])]
                # email_siape = i['IT-ED-CORREIO-ELETRONICO'].strip().lower()
                # try:
                #     validate_email(email_siape)
                # except ValidationError:
                #     email_siape = ''

                kwargs = dict(
                    # email_siape = email_siape,
                    grupo_sanguineo=i['IT-SG-GRUPO-SANGUINEO'].strip(),
                    fator_rh=i['IT-SG-FATOR-RH'].strip(),
                    alterado_em=datetime.now(),
                )

                kwargs['raca_id'] = self.raca_cache.get(str(int(i['IT-CO-COR-ORIGEM-ETNICA'])), None)
                kwargs['deficiencia'] = self.deficiencia_cache.get(i['IT-CO-GRUPO-DEFICIENCIA-FISICA'] + i['IT-CO-DEFICIENCIA-FISICA'], None)

                Servidor.objects.filter(id=servidor_id).update(**kwargs)
                self._atualizar_endereco(servidor_id, i)
                # self._atualizar_telefone(servidor_id, i)
            except Exception as ex:
                log.error(f'Erro ao importar servidor 4 - Error: {ex}\nArray: {i}')

    def importar_servidor5(self, itens):
        #        def _incluir_fax(pessoa_cpf, item):
        #            ddd = item['ED-FAX-RH'][:5].strip('0')
        #            numero = item['ED-FAX-RH'][5:].strip()
        #            if numero:
        #                pessoas=Pessoa.objects.filter(id__in=PessoaFisica.objects.filter(cpf=pessoa_cpf).values_list('id'))
        #                for pessoa in pessoas:
        #                    telefone_formatado = format_telefone(ddd, numero)
        #                    telefone = PessoaTelefone(pessoa=pessoa, numero = telefone_formatado)
        #                    telefone.save()
        for i in itens:
            try:
                pessoa_cpf = mask_cpf(i['NU-CPF-RH'])
            except KeyError:
                continue

            args = dict(
                nome_pai=capitaliza_nome(i['NO-PAI-RH'].strip()),
                nascimento_municipio=Municipio.get_or_create(i['NO-MUNICIPIO-NASCIMENTO-RH'].strip(), i['SG-UF-NASCIMENTO-RH'])[0],
                titulo_uf=i['SG-UF-TITULO-ELEITOR-RH'],
                titulo_zona=i['NU-ZONA-ELEITORAL-RH'].strip(),
                titulo_secao=i['NU-SECAO-ELEITORAL-RH'].strip(),
                titulo_data_emissao=strptime_or_default(i['DA-EMISSAO-TITULO-ELEITOR-RH'], '%Y%m%d'),
                cnh_carteira=i['NU-CART-MOTORISTA-RH'].strip(),
                cnh_registro=i['NU-REGISTRO-CART-MOTORISTA-RH'].strip(),
                cnh_categoria=i['IN-CATEGORIA-CART-MOTORISTA-RH'].strip(),
                cnh_uf=i['SG-UF-CART-MOTORISTA-RH'].strip(),
                cnh_emissao=strptime_or_default(i['DA-EXPEDICAO-CART-MOTORISTA-RH'], '%Y%m%d'),
                cnh_validade=strptime_or_default(i['DA-VALIDADE-CART-MOTORISTA-RH'], '%Y%m%d'),
            )
            PessoaFisica.objects.filter(cpf=pessoa_cpf).update(**args)
            identificacao_unica_siape = i['CO-IDENT-UNICA-SIAPE-RH']
            #            servidor_id=servidores_cache[extrai_matricula(identificacao_unica_siape[:8])]
            Servidor.objects.filter(pessoafisica_ptr__cpf=pessoa_cpf).update(identificacao_unica_siape=identificacao_unica_siape)
            #            _incluir_fax(pessoa_cpf, i)

    def importar_historico_afastamento(self, itens):
        self.calc_caches(True)
        for i in itens:
            servidor_id = self.servidores_cache[extrai_matricula(i['GR-MATRICULA-ANO-MES'])]
            self._atualizar_ocorrencia_afastamento(servidor_id, i)

    def importar_historico_funcao(self, itens):
        self.calc_caches(True)
        for i in itens:
            funcao_id = self.funcoes_cache.get(i['IT-SG-FUNCAO'].strip(), None)
            data_fim = self._decrescimo_data(strptime_or_default(i['IT-DA-SAIDA-FUNCAO'], '%Y%m%d'), 1)
            setor_id = self.setores_cache.get(i['IT-CO-UORG-FUNCAO'][-9:], None)
            if funcao_id and data_fim and setor_id:
                servidor_id = self.servidores_cache[extrai_matricula(i['GR-MATRICULA-ANO-MES'])]
                data_inicio = strptime_or_default(i['IT-DA-INGRESSO-FUNCAO'], '%Y%m%d')
                atividade_id = self.atividades_cache.get(i['IT-CO-ATIVIDADE-FUNCAO'], None)
                kwargs = dict(servidor_id=servidor_id, data_inicio_funcao=data_inicio, nivel=i['IT-CO-NIVEL-FUNCAO'].lstrip('0'), data_fim_funcao=data_fim)
                kwargs['funcao_id'] = funcao_id
                kwargs['setor_id'] = setor_id
                kwargs['atividade_id'] = atividade_id
                check_funcao_historico = ServidorFuncaoHistorico.objects.filter(servidor_id=servidor_id, data_inicio_funcao=data_inicio).first()
                if check_funcao_historico is not None and not check_funcao_historico.atualiza_pelo_extrator:
                    continue
                ServidorFuncaoHistorico.objects.update_or_create(servidor_id=servidor_id, data_inicio_funcao=data_inicio, defaults=kwargs)

    def importar_historico_setor_siape(self, itens):
        if ServidorSetorLotacaoHistorico:
            self.calc_caches(True)
            for i in itens:
                servidor_id = self.servidores_cache.get(extrai_matricula(i['GR-MATRICULA-ANO-MES']))
                setor_lotacao_id = self.setores_cache.get(i['IT-CO-UORG-LOTACAO-SERVIDOR'].strip())
                setor_exercicio_id = self.setores_cache.get(i['IT-CO-UORG-EXERCICIO-SERV'].strip())
                data_inicio_setor_lotacao = strptime_or_default(i['IT-DA-LOTACAO'], '%Y%m%d')
                hora_atualizacao_siape = strptime_or_default(i['IT-DA-TRANSACAO'] + i['IT-HO-TRANSACAO'], '%Y%m%d%H%M%S')
                if servidor_id and setor_lotacao_id and setor_exercicio_id and data_inicio_setor_lotacao and hora_atualizacao_siape:
                    kwargs = dict(
                        servidor_id=servidor_id,
                        data_inicio_setor_lotacao=data_inicio_setor_lotacao,
                        setor_lotacao_id=setor_lotacao_id,
                        setor_exercicio_id=setor_exercicio_id,
                        hora_atualizacao_siape=hora_atualizacao_siape,
                        data_fim_setor_lotacao=None,
                    )
                    servidor_lotacao = ServidorSetorLotacaoHistorico.objects.filter(servidor_id=servidor_id, data_inicio_setor_lotacao=data_inicio_setor_lotacao)
                    if servidor_lotacao.exists():
                        servidor_lotacao.filter(hora_atualizacao_siape__lt=hora_atualizacao_siape).update(**kwargs)
                    else:
                        ServidorSetorLotacaoHistorico.objects.create(**kwargs)

    def importar_historico_ferias(self, itens):
        if Ferias:
            self.calc_caches(True)
            for i in itens:
                # a matricula vem junto com o ano de exercicio da ferias
                matricula = i['GR-MATR-EXERCICIO-FERIAS-HIST'][:12]
                servidor_id = self.servidores_cache[extrai_matricula(matricula)]
                ano = Ano.objects.get_or_create(ano=int(i['GR-MATR-EXERCICIO-FERIAS-HIST'][12:16]))[0]
                quitacao = int(i['IT-IN-QUITACAO-FERIAS'])
                ferias = Ferias.objects.filter(servidor_id=servidor_id, ano=ano).first()
                if ferias:
                    if not ferias.atualiza_pelo_extrator:
                        continue

                    if not ferias.quitacao or ferias.quitacao <= quitacao:
                        ferias.quitacao = quitacao
                        if int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)']):
                            ferias.gratificacao_natalina = 1
                        elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)']):
                            ferias.gratificacao_natalina = 2
                        elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)']):
                            ferias.gratificacao_natalina = 3
                        else:
                            ferias.gratificacao_natalina = 0
                        count = 0
                        indice_setenta_porcento = 0
                        if int(i['IT-IN-ADIANTAMENTO-FERIAS(1)']):
                            indice_setenta_porcento += 1
                            count += 1
                        if int(i['IT-IN-ADIANTAMENTO-FERIAS(2)']):
                            count += 1
                            indice_setenta_porcento += 2
                        if int(i['IT-IN-ADIANTAMENTO-FERIAS(3)']):
                            count += 1
                            indice_setenta_porcento += 3
                        if count > 1:
                            indice_setenta_porcento += 1
                        ferias.setenta_porcento = indice_setenta_porcento

                        ferias.data_inicio_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(1)'], '%Y%m%d')
                        qtd_dias_periodo1 = int(i['IT-QT-DIAS-FERIAS(1)']) - 1
                        ferias.data_inicio_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(2)'], '%Y%m%d')
                        qtd_dias_periodo2 = int(i['IT-QT-DIAS-FERIAS(2)']) - 1
                        ferias.data_inicio_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(3)'], '%Y%m%d')
                        qtd_dias_periodo3 = int(i['IT-QT-DIAS-FERIAS(3)']) - 1

                        data_interrupcao_periodo1 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(1)'], '%Y%m%d')
                        data_interrupcao_periodo2 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(2)'], '%Y%m%d')
                        data_interrupcao_periodo3 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(3)'], '%Y%m%d')
                        data_inicio_continuacao_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(1)'], '%Y%m%d')
                        qtd_dias_continuacao_periodo1 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(1)']) - 1
                        data_inicio_continuacao_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(2)'], '%Y%m%d')
                        qtd_dias_continuacao_periodo2 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(2)']) - 1
                        data_inicio_continuacao_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(3)'], '%Y%m%d')
                        qtd_dias_continuacao_periodo3 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(3)']) - 1
                        if ferias.data_inicio_periodo1:
                            ferias.data_fim_periodo1 = ferias.data_inicio_periodo1 + data.timedelta(days=qtd_dias_periodo1)
                            if data_interrupcao_periodo1:
                                interrupcao = InterrupcaoFerias()
                                interrupcao, created = InterrupcaoFerias.objects.get_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo1)
                                interrupcao.data_fim_continuacao_periodo = data_inicio_continuacao_periodo1 + data.timedelta(days=qtd_dias_continuacao_periodo1)
                                interrupcao.data_inicio_continuacao_periodo = data_inicio_continuacao_periodo1
                                interrupcao.save()
                                if created:
                                    if ferias.data_inicio_periodo1 <= data_interrupcao_periodo1 < ferias.data_fim_periodo1:
                                        ferias.data_fim_periodo1 = data_interrupcao_periodo1 - data.timedelta(days=1)
                                    else:
                                        interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias)
                                        for interr in interrupcoes:
                                            if interr.data_inicio_continuacao_periodo <= data_interrupcao_periodo1 < interr.data_fim_continuacao_periodo:
                                                interr.data_fim_continuacao_periodo = data_interrupcao_periodo1 - data.timedelta(days=1)
                                                interr.save()

                        if ferias.data_inicio_periodo2:
                            ferias.data_fim_periodo2 = ferias.data_inicio_periodo2 + data.timedelta(days=qtd_dias_periodo2)
                            if data_interrupcao_periodo2:
                                interrupcao = InterrupcaoFerias()
                                interrupcao, created = InterrupcaoFerias.objects.get_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo2)
                                interrupcao.data_fim_continuacao_periodo = data_inicio_continuacao_periodo2 + data.timedelta(days=qtd_dias_continuacao_periodo2)
                                interrupcao.data_inicio_continuacao_periodo = data_inicio_continuacao_periodo2
                                interrupcao.save()
                                if created:
                                    if ferias.data_inicio_periodo2 <= data_interrupcao_periodo2 < ferias.data_fim_periodo2:
                                        ferias.data_fim_periodo2 = data_interrupcao_periodo2 - data.timedelta(days=1)
                                    else:
                                        interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias)
                                        for interr in interrupcoes:
                                            if interr.data_inicio_continuacao_periodo <= data_interrupcao_periodo2 < interr.data_fim_continuacao_periodo:
                                                interr.data_fim_continuacao_periodo = data_interrupcao_periodo2 - data.timedelta(days=1)
                                                interr.save()
                        else:
                            ferias.data_fim_periodo2 = None

                        if ferias.data_inicio_periodo3:
                            ferias.data_fim_periodo3 = ferias.data_inicio_periodo3 + data.timedelta(days=qtd_dias_periodo3)
                            if data_interrupcao_periodo3:
                                interrupcao = InterrupcaoFerias()
                                interrupcao, created = InterrupcaoFerias.objects.get_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo3)
                                interrupcao.data_fim_continuacao_periodo = data_inicio_continuacao_periodo3 + data.timedelta(days=qtd_dias_continuacao_periodo3)
                                interrupcao.data_inicio_continuacao_periodo = data_inicio_continuacao_periodo3
                                interrupcao.save()
                                if created:
                                    if ferias.data_inicio_periodo3 <= data_interrupcao_periodo3 < ferias.data_fim_periodo3:
                                        ferias.data_fim_periodo3 = data_interrupcao_periodo3 - data.timedelta(days=1)
                                    else:
                                        interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias)
                                        for interr in interrupcoes:
                                            if interr.data_inicio_continuacao_periodo <= data_interrupcao_periodo3 < interr.data_fim_continuacao_periodo:
                                                interr.data_fim_continuacao_periodo = data_interrupcao_periodo3 - data.timedelta(days=1)
                                                interr.save()
                        else:
                            ferias.data_fim_periodo3 = None

                    ferias.cadastrado = True
                    ferias.save()
                else:
                    ferias = Ferias()
                    ferias.quitacao = quitacao
                    data_inicio_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(1)'], '%Y%m%d')
                    data_inicio_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(2)'], '%Y%m%d')
                    data_inicio_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(3)'], '%Y%m%d')
                    kwargs = dict(data_inicio_periodo1=data_inicio_periodo1, data_inicio_periodo2=data_inicio_periodo2, data_inicio_periodo3=data_inicio_periodo2, cadastrado=True)
                    if int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)']):
                        kwargs['gratificacao_natalina'] = 1
                    elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)']):
                        kwargs['gratificacao_natalina'] = 2
                    elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)']):
                        kwargs['gratificacao_natalina'] = 3
                    else:
                        kwargs['gratificacao_natalina'] = 0
                    count = 0
                    indice_setenta_porcento = 0
                    if int(i['IT-IN-ADIANTAMENTO-FERIAS(1)']):
                        indice_setenta_porcento += 1
                        count += 1
                    if int(i['IT-IN-ADIANTAMENTO-FERIAS(2)']):
                        count += 1
                        indice_setenta_porcento += 2
                    if int(i['IT-IN-ADIANTAMENTO-FERIAS(3)']):
                        count += 1
                        indice_setenta_porcento += 3
                    if count > 1:
                        indice_setenta_porcento += 1

                    kwargs['setenta_porcento'] = indice_setenta_porcento

                    qtd_dias_periodo1 = int(i['IT-QT-DIAS-FERIAS(1)']) - 1
                    qtd_dias_periodo2 = int(i['IT-QT-DIAS-FERIAS(2)']) - 1
                    qtd_dias_periodo3 = int(i['IT-QT-DIAS-FERIAS(3)']) - 1

                    kwargs['data_fim_periodo1'] = data_inicio_periodo1 + data.timedelta(days=qtd_dias_periodo1)
                    data_interrupcao_periodo1 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(1)'], '%Y%m%d')
                    data_interrupcao_periodo2 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(2)'], '%Y%m%d')
                    data_interrupcao_periodo3 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(3)'], '%Y%m%d')
                    data_inicio_continuacao_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(1)'], '%Y%m%d')
                    qtd_dias_continuacao_periodo1 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(1)']) - 1
                    data_inicio_continuacao_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(2)'], '%Y%m%d')
                    qtd_dias_continuacao_periodo2 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(2)']) - 1
                    data_inicio_continuacao_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(3)'], '%Y%m%d')
                    qtd_dias_continuacao_periodo3 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(3)']) - 1
                    if data_inicio_periodo2:
                        kwargs['data_fim_periodo2'] = data_inicio_periodo2 + data.timedelta(days=qtd_dias_periodo2)
                    if data_inicio_periodo3:
                        kwargs['data_fim_periodo3'] = data_inicio_periodo3 + data.timedelta(days=qtd_dias_periodo3)

                    ferias = Ferias.objects.update_or_create(servidor_id=servidor_id, ano=ano, defaults=kwargs)[0]
                    atualizar_dados_ferias = dict()
                    if data_interrupcao_periodo1:
                        kwargs_interrupcao = dict(
                            data_fim_continuacao_periodo=data_inicio_continuacao_periodo1 + data.timedelta(days=qtd_dias_continuacao_periodo1),
                            data_inicio_continuacao_periodo=data_inicio_continuacao_periodo1,
                        )
                        InterrupcaoFerias.objects.update_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo1, defaults=kwargs_interrupcao)
                        if ferias.data_inicio_periodo1 <= data_interrupcao_periodo1 < ferias.data_fim_periodo1:
                            atualizar_dados_ferias['data_fim_periodo1'] = data_interrupcao_periodo1 - data.timedelta(days=1)

                    if data_interrupcao_periodo2:
                        kwargs_interrupcao = dict(
                            data_fim_continuacao_periodo=data_inicio_continuacao_periodo2 + data.timedelta(days=qtd_dias_continuacao_periodo2),
                            data_inicio_continuacao_periodo=data_inicio_continuacao_periodo2,
                        )
                        InterrupcaoFerias.objects.update_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo2, defaults=kwargs_interrupcao)
                        if ferias.data_inicio_periodo2 <= data_interrupcao_periodo2 < ferias.data_fim_periodo2:
                            atualizar_dados_ferias['data_fim_periodo2'] = data_interrupcao_periodo2 - data.timedelta(days=1)

                    if data_interrupcao_periodo3:
                        kwargs_interrupcao = dict(
                            data_fim_continuacao_periodo=data_inicio_continuacao_periodo3 + data.timedelta(days=qtd_dias_continuacao_periodo3),
                            data_inicio_continuacao_periodo=data_inicio_continuacao_periodo3,
                        )
                        InterrupcaoFerias.objects.update_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo3, defaults=kwargs_interrupcao)
                        if ferias.data_inicio_periodo3 <= data_interrupcao_periodo3 < ferias.data_fim_periodo3:
                            atualizar_dados_ferias['data_fim_periodo3'] = data_interrupcao_periodo3 - data.timedelta(days=1)

                    if atualizar_dados_ferias:
                        Ferias.objects.filter(pk=ferias.pk).update(**atualizar_dados_ferias)

    def importar_ferias(self, itens):
        if Ferias:
            for i in itens:
                matricula = i['GR-MATRICULA-EXERCICIO-FERIAS'][:12]  # a matricula vem junto com o ano de exercicio da ferias
                servidor = Servidor.objects.get(matricula=extrai_matricula(matricula))
                ano = Ano.objects.get_or_create(ano=int(i['GR-MATRICULA-EXERCICIO-FERIAS'][12:16]))[0]
                quitacao = int(i['IT-IN-QUITACAO-FERIAS'])
                ferias = Ferias.objects.filter(servidor=servidor, ano=ano).first()
                if ferias:
                    if ferias.atualiza_pelo_extrator and (not ferias.quitacao or ferias.quitacao <= quitacao):
                        ferias.quitacao = quitacao

                        if int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)']):
                            ferias.gratificacao_natalina = 1
                        elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)']):
                            ferias.gratificacao_natalina = 2
                        elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)']):
                            ferias.gratificacao_natalina = 3
                        else:
                            ferias.gratificacao_natalina = 0
                        count = 0
                        indice_setenta_porcento = 0
                        if int(i['IT-IN-ADIANTAMENTO-FERIAS(1)']):
                            indice_setenta_porcento += 1
                            count += 1
                        if int(i['IT-IN-ADIANTAMENTO-FERIAS(2)']):
                            count += 1
                            indice_setenta_porcento += 2
                        if int(i['IT-IN-ADIANTAMENTO-FERIAS(3)']):
                            count += 1
                            indice_setenta_porcento += 3
                        if count > 1:
                            indice_setenta_porcento += 1
                        ferias.setenta_porcento = indice_setenta_porcento

                        ferias.data_inicio_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(1)'], '%Y%m%d')
                        qtd_dias_periodo1 = int(i['IT-QT-DIAS-FERIAS(1)']) - 1
                        ferias.data_inicio_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(2)'], '%Y%m%d')
                        qtd_dias_periodo2 = int(i['IT-QT-DIAS-FERIAS(2)']) - 1
                        ferias.data_inicio_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(3)'], '%Y%m%d')
                        qtd_dias_periodo3 = int(i['IT-QT-DIAS-FERIAS(3)']) - 1

                        data_interrupcao_periodo1 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(1)'], '%Y%m%d')
                        data_interrupcao_periodo2 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(2)'], '%Y%m%d')
                        data_interrupcao_periodo3 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(3)'], '%Y%m%d')
                        data_inicio_continuacao_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(1)'], '%Y%m%d')
                        qtd_dias_continuacao_periodo1 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(1)']) - 1
                        data_inicio_continuacao_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(2)'], '%Y%m%d')
                        qtd_dias_continuacao_periodo2 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(2)']) - 1
                        data_inicio_continuacao_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(3)'], '%Y%m%d')
                        qtd_dias_continuacao_periodo3 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(3)']) - 1
                        if ferias.data_inicio_periodo1:
                            ferias.data_fim_periodo1 = ferias.data_inicio_periodo1 + data.timedelta(days=qtd_dias_periodo1)
                            if data_interrupcao_periodo1:
                                interrupcao = InterrupcaoFerias()
                                interrupcao, created = InterrupcaoFerias.objects.get_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo1)
                                interrupcao.data_fim_continuacao_periodo = data_inicio_continuacao_periodo1 + data.timedelta(days=qtd_dias_continuacao_periodo1)
                                interrupcao.data_inicio_continuacao_periodo = data_inicio_continuacao_periodo1
                                interrupcao.save()
                                if created:
                                    if ferias.data_inicio_periodo1 <= data_interrupcao_periodo1 < ferias.data_fim_periodo1:
                                        ferias.data_fim_periodo1 = data_interrupcao_periodo1 - data.timedelta(days=1)
                                    else:
                                        interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias)
                                        for interr in interrupcoes:
                                            if interr.data_inicio_continuacao_periodo <= data_interrupcao_periodo1 < interr.data_fim_continuacao_periodo:
                                                interr.data_fim_continuacao_periodo = data_interrupcao_periodo1 - data.timedelta(days=1)
                                                interr.save()

                        if ferias.data_inicio_periodo2:
                            ferias.data_fim_periodo2 = ferias.data_inicio_periodo2 + data.timedelta(days=qtd_dias_periodo2)
                            if data_interrupcao_periodo2:
                                interrupcao = InterrupcaoFerias()
                                interrupcao, created = InterrupcaoFerias.objects.get_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo2)
                                interrupcao.data_fim_continuacao_periodo = data_inicio_continuacao_periodo2 + data.timedelta(days=qtd_dias_continuacao_periodo2)
                                interrupcao.data_inicio_continuacao_periodo = data_inicio_continuacao_periodo2
                                interrupcao.save()
                                if created:
                                    if ferias.data_inicio_periodo2 <= data_interrupcao_periodo2 < ferias.data_fim_periodo2:
                                        ferias.data_fim_periodo2 = data_interrupcao_periodo2 - data.timedelta(days=1)
                                    else:
                                        interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias)
                                        for interr in interrupcoes:
                                            if interr.data_inicio_continuacao_periodo <= data_interrupcao_periodo2 < interr.data_fim_continuacao_periodo:
                                                interr.data_fim_continuacao_periodo = data_interrupcao_periodo2 - data.timedelta(days=1)
                                                interr.save()
                        else:
                            ferias.data_fim_periodo2 = None

                        if ferias.data_inicio_periodo3:
                            ferias.data_fim_periodo3 = ferias.data_inicio_periodo3 + data.timedelta(days=qtd_dias_periodo3)
                            if data_interrupcao_periodo3:
                                interrupcao = InterrupcaoFerias()
                                interrupcao, created = InterrupcaoFerias.objects.get_or_create(ferias=ferias, data_interrupcao_periodo=data_interrupcao_periodo3)
                                interrupcao.data_fim_continuacao_periodo = data_inicio_continuacao_periodo3 + data.timedelta(days=qtd_dias_continuacao_periodo3)
                                interrupcao.data_inicio_continuacao_periodo = data_inicio_continuacao_periodo3
                                interrupcao.save()
                                if created:
                                    if ferias.data_inicio_periodo3 <= data_interrupcao_periodo3 < ferias.data_fim_periodo3:
                                        ferias.data_fim_periodo3 = data_interrupcao_periodo3 - data.timedelta(days=1)
                                    else:
                                        interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias)
                                        for interr in interrupcoes:
                                            if interr.data_inicio_continuacao_periodo <= data_interrupcao_periodo3 < interr.data_fim_continuacao_periodo:
                                                interr.data_fim_continuacao_periodo = data_interrupcao_periodo3 - data.timedelta(days=1)
                                                interr.save()
                        else:
                            ferias.data_fim_periodo3 = None

                    ferias.cadastrado = True
                    ferias.save()
                else:
                    ferias = Ferias()
                    ferias.servidor = servidor
                    ferias.ano = ano
                    ferias.quitacao = quitacao
                    if int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)']):
                        ferias.gratificacao_natalina = 1
                    elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)']):
                        ferias.gratificacao_natalina = 2
                    elif int(i['IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)']):
                        ferias.gratificacao_natalina = 3
                    else:
                        ferias.gratificacao_natalina = 0
                    count = 0
                    indice_setenta_porcento = 0
                    if int(i['IT-IN-ADIANTAMENTO-FERIAS(1)']):
                        indice_setenta_porcento += 1
                        count += 1
                    if int(i['IT-IN-ADIANTAMENTO-FERIAS(2)']):
                        count += 1
                        indice_setenta_porcento += 2
                    if int(i['IT-IN-ADIANTAMENTO-FERIAS(3)']):
                        count += 1
                        indice_setenta_porcento += 3
                    if count > 1:
                        indice_setenta_porcento += 1
                    ferias.setenta_porcento = indice_setenta_porcento
                    ferias.data_inicio_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(1)'], '%Y%m%d')
                    qtd_dias_periodo1 = int(i['IT-QT-DIAS-FERIAS(1)']) - 1
                    ferias.data_inicio_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(2)'], '%Y%m%d')
                    qtd_dias_periodo2 = int(i['IT-QT-DIAS-FERIAS(2)']) - 1
                    ferias.data_inicio_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS(3)'], '%Y%m%d')
                    qtd_dias_periodo3 = int(i['IT-QT-DIAS-FERIAS(3)']) - 1
                    ferias.data_fim_periodo1 = ferias.data_inicio_periodo1 + data.timedelta(days=qtd_dias_periodo1)
                    data_interrupcao_periodo1 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(1)'], '%Y%m%d')
                    data_interrupcao_periodo2 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(2)'], '%Y%m%d')
                    data_interrupcao_periodo3 = strptime_date_or_default(i['IT-DA-INTERRUPCAO-FERIAS(3)'], '%Y%m%d')
                    data_inicio_continuacao_periodo1 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(1)'], '%Y%m%d')
                    qtd_dias_continuacao_periodo1 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(1)']) - 1
                    data_inicio_continuacao_periodo2 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(2)'], '%Y%m%d')
                    qtd_dias_continuacao_periodo2 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(2)']) - 1
                    data_inicio_continuacao_periodo3 = strptime_date_or_default(i['IT-DA-INICIO-FERIAS-INTERROMPIDA(3)'], '%Y%m%d')
                    qtd_dias_continuacao_periodo3 = int(i['IT-QT-DIA-FERIAS-INTERROMPIDA(3)']) - 1
                    if ferias.data_inicio_periodo2:
                        ferias.data_fim_periodo2 = ferias.data_inicio_periodo2 + data.timedelta(days=qtd_dias_periodo2)
                    if ferias.data_inicio_periodo3:
                        ferias.data_fim_periodo3 = ferias.data_inicio_periodo3 + data.timedelta(days=qtd_dias_periodo3)
                    ferias.cadastrado = True
                    ferias.save()
                    if data_interrupcao_periodo1:
                        interrupcao = InterrupcaoFerias.objects.create(
                            ferias=ferias,
                            data_interrupcao_periodo=data_interrupcao_periodo1,
                            data_fim_continuacao_periodo=data_inicio_continuacao_periodo1 + data.timedelta(days=qtd_dias_continuacao_periodo1),
                            data_inicio_continuacao_periodo=data_inicio_continuacao_periodo1,
                        )
                        if ferias.data_inicio_periodo1 <= data_interrupcao_periodo1 < ferias.data_fim_periodo1:
                            ferias.data_fim_periodo1 = data_interrupcao_periodo1 - data.timedelta(days=1)
                            ferias.save()

                    if data_interrupcao_periodo2:
                        interrupcao = InterrupcaoFerias.objects.get_or_create(
                            ferias=ferias,
                            data_interrupcao_periodo=data_interrupcao_periodo2,
                            data_fim_continuacao_periodo=data_inicio_continuacao_periodo2 + data.timedelta(days=qtd_dias_continuacao_periodo2),
                            data_inicio_continuacao_periodo=data_inicio_continuacao_periodo2,
                        )
                        if ferias.data_inicio_periodo2 <= data_interrupcao_periodo2 < ferias.data_fim_periodo2:
                            ferias.data_fim_periodo2 = data_interrupcao_periodo2 - data.timedelta(days=1)
                            ferias.save()
                    if data_interrupcao_periodo3:
                        interrupcao = InterrupcaoFerias.objects.get_or_create(
                            ferias=ferias,
                            data_interrupcao_periodo=data_interrupcao_periodo3,
                            data_fim_continuacao_periodo=data_inicio_continuacao_periodo3 + data.timedelta(days=qtd_dias_continuacao_periodo3),
                            data_inicio_continuacao_periodo=data_inicio_continuacao_periodo3,
                        )
                        if ferias.data_inicio_periodo3 <= data_interrupcao_periodo3 < ferias.data_fim_periodo3:
                            ferias.data_fim_periodo3 = data_interrupcao_periodo3 - data.timedelta(days=1)
                            ferias.save()

    def importar_titulacoes(self, itens):
        for i in itens:
            codigo = i['CO-TITULACAO']
            titulacao = Titulacao.objects.get_or_create(codigo=codigo)[0]
            titulacao.nome = i['NO-TITULACAO'].strip()
            titulacao.save()

    def importar_servidor_matriculas(self, itens):
        self.calc_caches(True)
        for i in itens:
            matricula_crh = i['CO-CRH-MATRICULA']
            matricula_sipe = i['NU-MATRICULA-SIPE-RH']
            matricula = extrai_matricula(i['GR-MATRICULA-SIAPE-RH'])
            servidor_id = self.servidores_cache.get(matricula)
            if matricula_crh and matricula_sipe and servidor_id:
                Servidor.objects.filter(id=servidor_id).update(matricula_crh=matricula_crh, matricula_sipe=matricula_sipe)

    def _atualizar_regime_juridico_pca(self, pca, registro, numero_registro):
        regime_juridico = RegimeJuridico.objects.filter(codigo_regime=registro[f'CO-REGIME-JURIDICO-PCA({numero_registro})']).first()
        data_inicio_regime_juridico_pca = strptime_or_default(registro[f'DA-INI-REGIME-JURIDICO-PCA({numero_registro})'], "%Y%m%d")
        data_fim_regime_juridico_pca = strptime_or_default(registro[f'DA-FIM-REGIME-JURIDICO-PCA({numero_registro})'], "%Y%m%d")
        valor_fator_tempo_regime_juridico_pca = Decimal(
            registro[f'VA-FATOR-TEMPO-REGIME-PCA({numero_registro})'][:-4] + '.' + registro[f'VA-FATOR-TEMPO-REGIME-PCA({numero_registro})'][-4:]
        )
        RegimeJuridicoPCA.objects.get_or_create(
            pca=pca,
            regime_juridico=regime_juridico,
            codigo_regime_juridico_pca=registro['CO-REGIME-JURIDICO-PCA(%s)' % numero_registro],
            data_inicio_regime_juridico_pca=data_inicio_regime_juridico_pca,
            data_fim_regime_juridico_pca=data_fim_regime_juridico_pca,
            valor_fator_tempo_regime_juridico_pca=valor_fator_tempo_regime_juridico_pca,
        )

    def _atualizar_jornada_trabalho_pca(self, pca, registro, numero_registro):
        data_inicio_jornada_trabalho_pca = strptime_or_default(registro['DA-INI-JORNADA-TRABALHO-PCA(%s)' % numero_registro], "%Y%m%d")
        data_fim_jornada_trabalho_pca = strptime_or_default(registro['DA-FIM-JORNADA-TRABALHO-PCA(%s)' % numero_registro], "%Y%m%d")
        JornadaTrabalhoPCA.objects.get_or_create(
            pca=pca,
            qtde_jornada_trabalho_pca=registro['QT-JORNADA-TRABALHO-PCA(%s)' % numero_registro],
            data_inicio_jornada_trabalho_pca=data_inicio_jornada_trabalho_pca,
            data_fim_jornada_trabalho_pca=data_fim_jornada_trabalho_pca,
        )

    def importar_pca(self, itens):
        '''
        itens = [
            {CH-PCA: '?', CO-CRH-PCA: '?', ...},
            {CH-PCA: '?', CO-CRH-PCA: '?', ...},
            {CH-PCA: '?', CO-CRH-PCA: '?', ...},
            {CH-PCA: '?', CO-CRH-PCA: '?', ...},
        ]
        '''
        if PCA:
            for registro in itens:
                try:
                    codigo_pca = registro['CH-PCA']
                    servidor_matricula_crh = registro['CO-CRH-PCA']
                    servidor_vaga_pca = registro['CO-VAGA-SIAPE-PCA']
                    cargo_pca = CargoEmprego.objects.get(codigo=registro['CH-CARGO-PCA'])
                    if Servidor.objects.filter(matricula_crh=servidor_matricula_crh, matricula_sipe=codigo_pca[:-3]).exists():
                        servidor = Servidor.objects.filter(matricula_crh=servidor_matricula_crh, matricula_sipe=codigo_pca[:-3]).latest('pk')
                        forma_entrada_pca = None
                        if int(registro['CO-FORMA-ENTRADA-PCA']):
                            forma_entrada_pca = FormaProvimentoVacancia.get_or_create(fill_attr="descricao", codigo=registro['CO-FORMA-ENTRADA-PCA'])[0]

                        forma_vacancia_pca = None
                        if int(registro['CO-FORMA-VACANCIA-PCA']):
                            forma_vacancia_pca = FormaProvimentoVacancia.get_or_create(fill_attr="descricao", codigo=registro['CO-FORMA-VACANCIA-PCA'])[0]

                        kwargs = dict(
                            codigo_pca=codigo_pca,
                            servidor=servidor,
                            servidor_matricula_crh=servidor_matricula_crh,
                            servidor_vaga_pca=servidor_vaga_pca,
                            cargo_pca=cargo_pca,
                            forma_entrada_pca=forma_entrada_pca,
                            data_entrada_pca=strptime_or_default(registro['DA-ENTRADA-PCA'], '%Y%m%d'),
                            texto_entrada_pca=registro['TX-ENTRADA-PCA(1)'].strip(),
                            forma_vacancia_pca=forma_vacancia_pca,
                            data_vacancia_pca=strptime_or_default(registro['DA-VACANCIA-PCA'], '%Y%m%d'),
                            texto_vacancia_pca=registro['TX-VACANCIA-PCA(1)'].strip(),
                        )
                        pca = PCA.objects.update_or_create(codigo_pca=codigo_pca, defaults=kwargs)[0]

                        # regime juridico PCA
                        pca.regimejuridicopca_set.all().delete()
                        if int(registro['CO-REGIME-JURIDICO-PCA(1)']):
                            self._atualizar_regime_juridico_pca(pca, registro, 1)
                        if int(registro['CO-REGIME-JURIDICO-PCA(2)']):
                            self._atualizar_regime_juridico_pca(pca, registro, 2)
                        if int(registro['CO-REGIME-JURIDICO-PCA(3)']):
                            self._atualizar_regime_juridico_pca(pca, registro, 3)
                        if int(registro['CO-REGIME-JURIDICO-PCA(4)']):
                            self._atualizar_regime_juridico_pca(pca, registro, 4)
                        if int(registro['CO-REGIME-JURIDICO-PCA(5)']):
                            self._atualizar_regime_juridico_pca(pca, registro, 5)
                        if int(registro['CO-REGIME-JURIDICO-PCA(6)']):
                            self._atualizar_regime_juridico_pca(pca, registro, 6)

                        # jornada de trabalho PCA
                        pca.jornadatrabalhopca_set.all().delete()
                        if int(registro['QT-JORNADA-TRABALHO-PCA(1)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 1)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(2)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 2)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(3)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 3)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(4)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 4)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(5)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 5)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(6)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 6)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(7)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 7)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(8)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 8)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(9)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 9)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(10)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 10)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(11)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 11)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(12)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 12)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(13)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 13)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(14)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 14)
                        if int(registro['QT-JORNADA-TRABALHO-PCA(15)']):
                            self._atualizar_jornada_trabalho_pca(pca, registro, 15)

                except Exception as ex:
                    log.info(f'>>> ERRO: {ex} \n>>> LINHA: {registro}')
                    continue

    def importar_posicionamento_pca(self, itens):
        '''
        pca = models.ForeignKeyPlus('rh.PCA', null=False)
        codigo_pca_posicionamento = models.CharField(max_length=11) # CH-PCA-POSICIONAMENTO - é o mesmo dado de rh.PCA.codigo_pca
        codigo_posicionamento_pca = models.CharField(max_length=9, unique=True, null=False) # CH-POSICIONAMENTO-PCA

        forma_entrada = models.ForeignKeyPlus('rh.FormaProvimentoVacancia') # CO-FORMA-ENTRADA-POS-PCA
        data_inicio_posicionamento_pca = models.DateFieldPlus() # DA-INI-POSICIONAMENTO-PCA
        data_fim_posicionamento_pca = models.DateFieldPlus() # DA-FIM-POSICIONAMENTO-PCA
        '''
        if PosicionamentoPCA:
            for registro in itens:
                codigo_pca = registro['CH-PCA-POSICIONAMENTO']
                codigo_posicionamento = registro['CH-POSICIONAMENTO-PCA']
                forma_entrada = FormaProvimentoVacancia.get_or_create(fill_attr="descricao", codigo=registro['CO-FORMA-ENTRADA-POS-PCA'])[0]
                data_inicio_posicionamento_pca = strptime_or_default(registro['DA-INI-POSICIONAMENTO-PCA'], '%Y%m%d')
                kwargs = dict(
                    codigo_pca_posicionamento=codigo_pca,
                    codigo_posicionamento_pca=codigo_posicionamento,
                    forma_entrada=forma_entrada,
                    data_inicio_posicionamento_pca=data_inicio_posicionamento_pca,
                    data_fim_posicionamento_pca=strptime_or_default(registro['DA-FIM-POSICIONAMENTO-PCA'], '%Y%m%d'),
                )
                pca = PCA.objects.filter(codigo_pca=codigo_pca).first()
                if pca:
                    kwargs['pca'] = pca
                    PosicionamentoPCA.objects.update_or_create(
                        codigo_posicionamento_pca=codigo_posicionamento,
                        codigo_pca_posicionamento=codigo_pca,
                        forma_entrada=forma_entrada,
                        data_inicio_posicionamento_pca=data_inicio_posicionamento_pca,
                        defaults=kwargs,
                    )

    def importar_servidor_afastamentos(self, itens):
        self.calc_caches()
        for i in itens:
            servidor_id = self.servidores_cache.get(extrai_matricula(i['GR-MATRICULA']))
            afastamento_id = self.afastamentos_cache.get(i['IT-CO-AFASTAMENTO-SERV'])

            if not afastamento_id or not servidor_id:
                continue
            cancelado = int(i['IT-CO-MOTIVO-CANCELA-AFAST']) > 0 or strptime_or_default(i['IT-DA-CANCELA-AFASTAMENTO'], '%Y%m%d') is not None
            tem_efeito_financeiro = i['IT-IN-EFEITO-FINANCEIRO-SERV'] == 'S'
            data_inicio = strptime_or_default(i['IT-DA-INICIO-AFASTAMENTO-SERV'], '%Y%m%d')
            kwargs = dict(data_termino=strptime_or_default(i['IT-DA-TERMINO-AFASTAMENTO-SERV'], '%Y%m%d'), tem_efeito_financeiro=tem_efeito_financeiro, cancelado=cancelado)
            ServidorAfastamento.objects.update_or_create(servidor_id=servidor_id, afastamento_id=afastamento_id, data_inicio=data_inicio, defaults=kwargs)
