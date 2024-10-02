"""
__author__ = "Fernando Lopes"
__institute__ = "IFRN"
__version__ = "0.0.1"
"""
import re
import ssl

from datetime import datetime, date
from django.apps.registry import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from suds import WebFault
from suds.client import Client

from comum.utils import capitaliza_nome, extrai_matricula
from djtools.utils import mask_cpf, format_telefone

import logging

logging.getLogger("suds.client").setLevel(logging.CRITICAL)

Ferias = apps.get_model("ferias", "Ferias") if "ferias" in settings.INSTALLED_APPS else None
ParcelaFerias = apps.get_model("ferias", "ParcelaFerias") if "ferias" in settings.INSTALLED_APPS else None
Situacao = apps.get_model("rh", "Situacao")
RegimeJuridico = apps.get_model("rh", "RegimeJuridico")
Banco = apps.get_model("rh", "Banco")
Servidor = apps.get_model("rh", "Servidor")
Atividade = apps.get_model("rh", "Atividade")
CargoClasse = apps.get_model("rh", "CargoClasse")
Funcao = apps.get_model("rh", "Funcao")
Deficiencia = apps.get_model("rh", "Deficiencia")
Setor = apps.get_model("rh", "Setor")
JornadaTrabalho = apps.get_model("rh", "JornadaTrabalho")
Ocorrencia = apps.get_model("rh", "Ocorrencia")
SubgrupoOcorrencia = apps.get_model("rh", "SubgrupoOcorrencia")
ServidorOcorrencia = apps.get_model("rh", "ServidorOcorrencia")
CargoEmprego = apps.get_model("rh", "CargoEmprego")
NivelEscolaridade = apps.get_model("rh", "NivelEscolaridade")
Titulacao = apps.get_model("rh", "Titulacao")
ServidorFuncaoHistorico = apps.get_model("rh", "ServidorFuncaoHistorico")
AfastamentoSiape = apps.get_model("rh", "AfastamentoSiape")
ServidorAfastamento = apps.get_model("rh", "ServidorAfastamento")
ServidorSetorHistorico = apps.get_model("rh", "ServidorSetorHistorico")
EstadoCivil = apps.get_model("comum", "EstadoCivil")
Municipio = apps.get_model("comum", "Municipio")
Raca = apps.get_model("comum", "Raca")
Pais = apps.get_model("comum", "Pais")
Ano = apps.get_model("comum", "Ano")
PessoaEndereco = apps.get_model("comum", "PessoaEndereco")
PessoaTelefone = apps.get_model("comum", "PessoaTelefone")
ExcecaoDadoWS = apps.get_model("rh", "ExcecaoDadoWS")

"""
De modo geral, toda operação é composta pelos seguintes parâmetros de entrada:

    siglaSistema: É a sigla do sistema informada durante seu cadastramento. (estático)
    nomeSistema: É o nome do sistema informado durante seu cadastramento. (estático)
    senha: É a senha de acesso gerada após o cadastramento e enviada ao endereço eletrônico (e-mail) do responsável pelo sistema. (estático)
    cpf: O conteúdo deste parâmetro refere-se ao CPF do qual deseja-se obter as informações da consulta codOrgao: Este parâmetro é opcional. Recebe o código do órgão referente ao vínculo de onde deseja-se consultar as informações, para o CPF informado
    parmExistPag: Recebe os valores “a” ou “b”, conforme permissões. concedidas durante o cadastramento.
        a – Somente os vínculos ativos para pagamento na data atual (sem ocorrência de exclusão);
        b – Todos os vínculos existentes no sistema para o CPF, independentes de estarem recebendo pagamento (com ou sem ocorrência de exclusão)

    ParmTipoVinculo: Recebe os valores “a”, “b” ou “c”, conforme permissões concedidas durante o cadastramento.
        a – Somente os vínculos de servidores em exercício (servidores com PCA-exercício interno ou PFU vigentes ou com vínculos sem cargo e sem função). Não entram nestes casos aposentados, pensionistas, cedidos ou em exercício externo ao órgão de lotação.
        b – Somente os vínculos que se referem diretamente ao servidor (todos os vínculos do item a + aposentadorias + cedidos ou em exercício externo ao órgão de lotação)
        c – Todos os vínculos de recebimento do servidor (todos os vínculos do item b + pensões recebidas).
"""

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


class ImportadorWs:
    lista_uorgs = None
    client = None

    def __init__(self):
        #####################################################################################
        # Configuração necessária para que o suds não verifique certificados auto assinados
        #####################################################################################
        Configuracao = apps.get_model("comum", "configuracao")
        config = Configuracao.get_valor_por_chave(app="rh", chave="urlProducaoWS")
        if config:
            cliente = Client(config)
            cliente.options.location = config.split("?")[0]
            self.client = cliente
        else:
            raise ValidationError("Não foi encontrado uma url do WSDL cadastrada no SUAP.")

    """ Definição auxiliar para formatar datas no formado do webservice."""

    def _str_to_date(self, string_date):
        try:
            if string_date:
                return datetime.strptime(string_date, "%d%m%Y").date()
            return None
        except Exception:
            return None

    """ Definição auxiliar que monta, separados por vírgula, os parâmetros de um serviço."""

    def __get_params_service(self, method):
        params = ", ".join("%s" % part.name for part in method.soap.input.body.parts)
        return params

    """ Consulta todos os serviços disponíveis no webservice."""

    def _get_services_siape(self):
        list_options = []
        for k, v in list(self._get_service_and_params().items()):
            list_options.append(["%s" % k, f"{k}({v})"])
        return list_options

    """ Monta um dicionário onde a chave é o nome do serviço e o valor todos os seus parâmetros."""

    def _get_service_and_params(self):
        dict = {}
        if self.client:
            for method in list(self.client.wsdl.services[0].ports[0].methods.values()):
                params = self.__get_params_service(method)
                dict[method.name] = params
        return dict

    """ Definição que chama um serviço do webservice."""

    def _call_service_siape(self, params):
        Configuracao = apps.get_model("comum", "configuracao")
        metodo = params.pop("consulta")
        params["siglaSistema"] = Configuracao.get_valor_por_chave("rh", "siglaSistemaWS")
        params["nomeSistema"] = Configuracao.get_valor_por_chave("rh", "nomeSistemaWS")
        params["codOrgao"] = Configuracao.get_valor_por_chave("rh", "codOrgaoWS")
        params["senha"] = Configuracao.get_valor_por_chave("rh", "senhaWS")
        nome_parametros = self._get_service_and_params().get(metodo).replace(" ", "").split(",")
        try:
            result = getattr(self.client.service, metodo)(*[params[parametro] for parametro in nome_parametros])
        except Exception:
            result = ("", {})
        return result

    """ Consulta as uorgs do instituto e seta atributo para manter os valores."""

    def get_lista_uorgs(self, cod_uorg=1):
        #
        # não entendi pq essa consulta precisa de cpf :/
        params = {"consulta": "listaUorgs", "codUorg": cod_uorg, "cpf": 11111111111}
        self.lista_uorgs = self._call_service_siape(params)

    """ Consulta servidores de uma uorg. Se a uorg não for passada, consulta de todas as uorgs do instituto."""

    def get_lista_servidores(self, uo=None):
        s = dict()
        uorgs = None
        if uo:
            uorgs = [uo]
        else:
            uorgs = self.lista_uorgs[0]

        for uorg in uorgs:
            try:
                s[uorg.codigo] = {"codigo": uorg.codigo, "nome": "%s" % uorg.nome}
                #
                # não entendi pq essa consulta precisa de cpf :/
                params = {"consulta": "listaServidores", "cpf": 11111111111, "codUorg": uorg.codigo}
                s[uorg.codigo]["servidores"] = self._call_service_siape(params)
            except Exception:
                continue
        return s

    """
    Consulta dados funcionais de um servidor
        :param cpf - apenas números
        :param todos_os_vinculos - Se True, mostra vínculos com ocorrência de exclusão, caso existam.
    """

    def get_dados_funcionais(self, cpf, todos_os_vinculos=False, ver_apenas_servidores_em_exercicio=False):
        tipo_vinculo = "a" if ver_apenas_servidores_em_exercicio else "b"
        params = {
            "consulta": "consultaDadosFuncionais",
            "cpf": cpf,
            "parmExistPag": "a",
            "parmTipoVinculo": tipo_vinculo,
        }
        if todos_os_vinculos:
            params.update({"parmExistPag": "b", "parmTipoVinculo": "c"})

        dados_servidor = self._call_service_siape(params)

        return dados_servidor.dadosFuncionais.DadosFuncionais

    """
    Consulta dados pessoais de um servidor
        :param cpf - apenas números
    """

    def get_dados_pessoais(self, cpf):
        params = {"consulta": "consultaDadosPessoais", "cpf": cpf, "parmExistPag": "b", "parmTipoVinculo": "c"}
        dados_pessoais = self._call_service_siape(params)
        return dados_pessoais

    """
    Consulta afastamentos no momento.
        :param cpf - apenas números
    """

    def get_afastamento(self, cpf):
        try:
            params = {"consulta": "consultaDadosAfastamento", "cpf": cpf, "parmExistPag": "a", "parmTipoVinculo": "b"}
            afastamentos = self._call_service_siape(params)

            ocorrencias = None
            ferias = None

            # verificando afastamentos por matrícula
            if hasattr(ocorrencias, "ArrayDadosAfastamento"):
                ferias_por_matr = dict()
                ocorrencia_por_matr = dict()

                afastamentos_matricula = afastamentos.dadosAfastamentoPorMatricula.DadosAfastamentoPorMatricula
                for a in afastamentos_matricula:
                    if a.ferias:
                        ferias_por_matr["dataIni"] = a.ferias.DadosFerias[0].dataIni
                        ferias_por_matr["dataFim"] = a.ferias.DadosFerias[0].dataFim

                        f = dict()
                        f["ferias"] = ferias_por_matr
                        ferias = f

                    if a.ocorrencias:
                        ocorrencia_por_matr["codOcorrencia"] = a.ocorrencias.DadosOcorrencias[0].codOcorrencia
                        ocorrencia_por_matr["descOcorrencia"] = a.ocorrencias.DadosOcorrencias[0].descOcorrencia
                        ocorrencia_por_matr["dataIni"] = a.ocorrencias.DadosOcorrencias[0].dataIni
                        ocorrencia_por_matr["dataFim"] = a.ocorrencias.DadosOcorrencias[0].dataFim

                        o = dict()
                        o["ocorrencia"] = ocorrencia_por_matr
                        ocorrencias = o

            return ferias, ocorrencias
        except WebFault as e:
            return e

    def get_afastamento_historico(self, cpf, mes_inicio=1, ano_inicio=date.today().year, mes_fim=12, ano_fim=date.today().year + 1):
        cpf = cpf.replace(".", "").replace("-", "")
        param_1 = "a"
        # Servidores que tem 2 vinculos ativos ao mesmo tempo
        if Servidor.objects.ativos().filter(pessoa_fisica__cpf=cpf).count() >= 2:
            param_1 = "b"
        params = {
            "consulta": "consultaDadosAfastamentoHistorico",
            "cpf": cpf,
            "mesInicial": mes_inicio,
            "anoInicial": ano_inicio,
            "mesFinal": mes_fim,
            "anoFinal": ano_fim,
            "parmExistPag": param_1,
            "parmTipoVinculo": "c",
        }
        ocorrencias = self._call_service_siape(params)
        afastamentos_servidor = []
        ferias_servidor = []
        if hasattr(ocorrencias, "ArrayDadosAfastamento"):
            for ocorrencia in ocorrencias.ArrayDadosAfastamento:
                dados_por_matricula = ocorrencia.dadosAfastamentoPorMatricula.DadosAfastamentoPorMatricula
                for dado in dados_por_matricula:
                    matricula = extrai_matricula(dado.grMatricula)
                    servidor = Servidor.objects.filter(matricula=matricula).first()
                    if servidor and dado.ferias and Ferias:
                        anos_parcelas = []
                        for dados_ferias in dado.ferias.DadosFerias:
                            ano_exercicio = Ano.objects.get_or_create(ano=int(dados_ferias.anoExercicio))[0]
                            ferias = Ferias(ano=ano_exercicio, servidor=servidor)
                            numero_parcela = dados_ferias.numeroDaParcela
                            ano_parcela = f"{ano_exercicio.ano}{numero_parcela}"
                            if ano_parcela not in anos_parcelas:
                                kwargs = {
                                    "ferias": ferias,
                                    "numero_parcela": numero_parcela,
                                    "continuacao_interrupcao": dados_ferias.parcelaContinuacaoInterrupcao == "S",
                                    "parcela_interrompida": dados_ferias.parcelaInterrompida == "S",
                                    "data_inicio": self._str_to_date(dados_ferias.dataIni),
                                    "data_fim": self._str_to_date(dados_ferias.dataFim),
                                    "adiantamento_gratificacao_natalina": dados_ferias.gratificacaoNatalina == "S",
                                    "setenta_porcento": dados_ferias.adiantamentoSalarioFerias == "S",
                                }
                                ferias_servidor.append(kwargs)
                                anos_parcelas.append(ano_parcela)

                    if servidor and dado.ocorrencias:
                        for dados_afastamento in dado.ocorrencias.DadosOcorrencias:
                            afastamento = AfastamentoSiape.objects.filter(codigo=dados_afastamento.codOcorrencia).first()
                            if afastamento:
                                kwargs = {
                                    "afastamento": afastamento,
                                    "servidor": servidor,
                                    "data_inicio": self._str_to_date(dados_afastamento.dataIni),
                                    "data_termino": self._str_to_date(dados_afastamento.dataFim),
                                }
                                afastamentos_servidor.append(kwargs)

        return {"ferias": ferias_servidor, "afastamentos": afastamentos_servidor}

    """
    Consulta dados bancários de um servidor
        :param cpf - apenas números
    """

    def get_dados_bancarios(self, cpf):
        try:
            params = {"consulta": "consultaDadosBancarios", "cpf": cpf, "parmExistPag": "b", "parmTipoVinculo": "c"}
            dados_bancarios = self._call_service_siape(params)
            return dados_bancarios.dadosBancarios.DadosBancarios
        except WebFault as e:
            return e

    """
    Consulta dependentes
        :param cpf - apenas números
    """

    def get_dependentes(self, cpf):
        try:
            params = {"consulta": "consultaDadosDependentes", "cpf": cpf, "parmExistPag": "a", "parmTipoVinculo": "b"}
            dependentes = self._call_service_siape(params)
            return dependentes
        except WebFault as e:
            return e

    """
    Consulta dados de documentação
        :param cpf - apenas números
    """

    def get_dados_documentacao(self, cpf):
        try:
            params = {"consulta": "consultaDadosDocumentacao", "cpf": cpf, "parmExistPag": "b", "parmTipoVinculo": "c"}
            documentacao = self._call_service_siape(params)
            return documentacao
        except WebFault as e:
            return e

    """
    Consulta dados de endereço residencial
        :param cpf - apenas números
    """

    def get_dados_endereco_residencial(self, cpf):
        try:
            params = {
                "consulta": "consultaDadosEnderecoResidencial",
                "cpf": cpf,
                "parmExistPag": "b",
                "parmTipoVinculo": "c",
            }
            endereco = self._call_service_siape(params)
            return endereco
        except WebFault as e:
            return e

    """
    Consulta dados escolares (inclui as titulações)
        :param cpf - apenas números
    """

    def get_dados_escolares(self, cpf):
        try:
            params = {"consulta": "consultaDadosEscolares", "cpf": cpf, "parmExistPag": "b", "parmTipoVinculo": "c"}
            dados_escolares = self._call_service_siape(params)

            d_titutlacao = None
            d_escolar = None
            if dados_escolares:
                d_escolar = [
                    {
                        "codEscolaridade": dados_escolares.codEscolaridade,
                        "nomeEscolaridade": dados_escolares.nomeEscolaridade,
                    }
                ]

                if dados_escolares.arrayTitulacao:
                    d_titutlacao = dados_escolares.arrayTitulacao.DadosTitulacao

            return {"escolar": d_escolar, "titulacoes": d_titutlacao}
        except WebFault as e:
            return e

    """
    Consulta dados ficanceiros
        :param cpf - apenas números
    """

    def get_dados_financeiros(self, cpf):
        try:
            params = {"consulta": "consultaDadosFinanceiros", "cpf": cpf, "parmExistPag": "a", "parmTipoVinculo": "b"}
            dados_financeiros = self._call_service_siape(params)

            return dados_financeiros.dadosFinanceiros.DadosFinanceiros
        except WebFault as e:
            return e

    """
    Consulta dados uorg de um servidor
        :param cpf - apenas números
    """

    def get_dados_uorg(self, cpf):
        try:
            params = {"consulta": "consultaDadosUorg", "cpf": cpf, "parmExistPag": "a", "parmTipoVinculo": "b"}
            dados_uorg = self._call_service_siape(params)
            return dados_uorg
        except WebFault as e:
            return e

    """
    Consulta dados do contracheques
        :param cpf - apenas números
        :param anoInicial - apenas números
        :param anoFinal - apenas números
    """

    def get_dados_contracheques(self, cpf, ano_inicial=None, ano_fim=None, ultimo_cc_apenas=False):
        try:
            ano_atual = date.today().year
            params = {
                "consulta": "consultaDadosFinanceirosHistorico",
                "cpf": cpf,
                "parmExistPag": "b",
                "parmTipoVinculo": "c",
                "anoInicial": ano_atual,
                "anoFinal": ano_atual,
            }
            if ano_inicial:
                params = params.update({"anoInicial": ano_inicial})
            if ano_fim:
                params = params.update({"anoFinal": ano_fim})

            dados = self._call_service_siape(params)
            if ultimo_cc_apenas and hasattr(dados, "ArrayDadosFinanceiros"):
                ultimo_ano_mes_cc = dados.ArrayDadosFinanceiros[-1].mesAnoPagamento
                cc_ultimo_mes_list = []
                for x in dados.ArrayDadosFinanceiros:
                    if x.mesAnoPagamento == ultimo_ano_mes_cc:
                        cc_ultimo_mes_list.append(x)
                dados.ArrayDadosFinanceiros = cc_ultimo_mes_list
            return dados
        except WebFault as e:
            return e

    #########################
    # IMPORTAÇÕES           #
    #########################
    def _get_servidor_completo(self, cpf, ver_apenas_servidores_em_exercicio=False):
        servidores = []
        cpf = cpf.replace(".", "").replace("-", "")
        """
        tratando dados funcionais
        """
        count = 1
        interar = True
        dados_funcionais = None
        while interar:
            try:
                dados_funcionais = self.get_dados_funcionais(cpf, True, ver_apenas_servidores_em_exercicio)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_funcionais:
            raise Exception("Não foi possível recuperar dados funcionais do servidor.")
        else:
            for dados in dados_funcionais:
                servidor = {}
                for dado_funcional in dados:
                    servidor[dado_funcional[0]] = dado_funcional[1]
                servidores.append(servidor)

        """
        tratando dados de documentações
        """
        count = 1
        interar = True
        dados_documentacao = None
        pessoa = {}
        while interar:
            try:
                dados_documentacao = self.get_dados_documentacao(cpf)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_documentacao:
            raise Exception("Não foi possível recuperar dados de documentação do servidor.")
        else:
            for d in dados_documentacao:
                pessoa[d[0]] = d[1]

        """
        tratando dados pessoais
        """
        count = 1
        interar = True
        dados_pessoais = None
        while interar:
            try:
                dados_pessoais = self.get_dados_pessoais(cpf)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_pessoais:
            raise Exception("Não foi possível recuperar dados pessoais do servidor.")
        else:
            for d in dados_pessoais:
                pessoa[d[0]] = d[1]

        """
        tratando dados endereço residencial
        """
        count = 1
        interar = True
        dados_endereco_residencial = None
        while interar:
            try:
                dados_endereco_residencial = self.get_dados_endereco_residencial(cpf)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_endereco_residencial:
            raise Exception("Não foi possível recuperar dados endereco residencial.")
        else:
            for d in dados_endereco_residencial:
                pessoa[d[0]] = d[1]

        """
        tratando dados bancarios
        """
        count = 1
        interar = True
        dados_bancarios = None
        while interar:
            try:
                dados_bancarios = self.get_dados_bancarios(cpf)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_bancarios:
            raise Exception("Não foi possível recuperar dados bancários do servidor.")
        else:
            for d in dados_bancarios[0]:
                pessoa[d[0]] = d[1]

        """
        tratando dados escolares (titulações)
        """
        count = 1
        interar = True
        dados_escolares = None
        while interar:
            try:
                dados_escolares = self.get_dados_escolares(cpf)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_escolares:
            raise Exception("Não foi possível recuperar dados escolares do servidor.")
        else:
            for d in dados_escolares:
                if dados_escolares.get(d):
                    if d == "titulacoes":
                        pessoa[d] = dados_escolares.get(d)
                    else:
                        pessoa[d] = dados_escolares.get(d)[0]

        """
        tratando dados de contracheques
        """
        count = 1
        interar = True
        dados_contracheques = None
        while interar:
            try:
                dados_contracheques = self.get_dados_contracheques(cpf, ultimo_cc_apenas=True)
                interar = False
            except Exception:
                if count < 3:
                    count += 1
                else:
                    interar = False

        if not dados_bancarios:
            raise Exception("Não foi possível recuperar dados de contracheques do servidor.")
        else:
            pessoa["dados_contracheques"] = {}
            for d in dados_contracheques[0]:
                if pessoa["dados_contracheques"].get(d["matricula"]):
                    pessoa["dados_contracheques"].get(d["matricula"]).update({d["mesAnoPagamento"]: d["dadosFinanceiros"]})
                else:
                    pessoa["dados_contracheques"].update({d["matricula"]: {d["mesAnoPagamento"]: d["dadosFinanceiros"]}})

        return servidores, pessoa

    """
    Processamento de importação de um servidor
        :param cpf - apenas números
        :param ver_apenas_servidores_em_exercicio - Se True, segue a regra do parametro ParmTipoVinculo (opção 'a') definida na documentação ConsultaSiape.
    """

    def importacao_servidor(self, cpf, ver_dados_apenas=False, ver_apenas_servidores_em_exercicio=False):
        try:
            ###############################
            # Consultando cpf no webservice
            ###############################
            servidores, pessoa = self._get_servidor_completo(cpf, ver_apenas_servidores_em_exercicio)

            ############################
            # DADOS FUNCIONAIS         #
            ############################

            # TODO: verificar quando setar o campo "data_obito"
            # TODO: é para setar o username com a matrícula do servidor/estagiário?

            #
            # Não foi possível recuperar:
            # 1. CargoEmprego, pois não é possível recuperar o grupo cargo emprego via webservice
            # 2. Não foi encontrado a data do primeiro emprego via webservice (ctps_data_prim_emprego)
            # 3. Não foi possível encontrar o código do país via webservice
            # 4. Não foi possível encontrar o grupo de deficiência via webservice

            #
            # Carregando informações sobre exceções de atualização de dados
            # - carrega campos de servidores que não terão essas informações atualizadas (os campos cadastrados como exceção de atualização)
            excecoes_atualizacao = dict()
            for i in ExcecaoDadoWS.objects.all():
                if i.servidor.matricula not in excecoes_atualizacao:
                    excecoes_atualizacao[i.servidor.matricula] = [i for i in i.campos.values_list("campo", flat=True)]

            dados_atualizar = []
            for servidor in servidores:
                matricula = extrai_matricula(servidor.get("matriculaSiape"))
                # Verificando se existe um email siape cadastrado. Caso negativo, não permite o cadastro do servidor
                email_siape = servidor.get("emailServidor")
                if not email_siape or email_siape == "":
                    raise ValidationError(
                        "Não existe um e-mail cadastrado no SIAPE para o servidor. Por favor, cadastre um e-mail e repita esta operação."
                    )

                args = dict(
                    matricula=matricula,
                    situacao=Situacao.objects.get_or_create(codigo=servidor.get("codSitFuncional"))[0],
                    cpf=mask_cpf(pessoa.get("numCPF")),
                    nome=capitaliza_nome(pessoa.get("nome")),
                    nome_registro=capitaliza_nome(pessoa.get("nome")),
                    nome_mae=capitaliza_nome(pessoa.get("nomeMae")),
                    nome_pai=capitaliza_nome(pessoa.get("nomePai")),
                    sexo=pessoa.get("codSexo"),
                    nascimento_data=self._str_to_date(pessoa.get("dataNascimento")),
                    raca=Raca.objects.get_or_create(codigo_siape=pessoa.get("codCor"), defaults={"descricao": pessoa.get("nomeCor")})[0],
                    estado_civil=EstadoCivil.get_or_create(codigo_siape=pessoa.get("codEstadoCivil"))[0],
                    regime_juridico=RegimeJuridico.get_or_create(sigla=servidor.get("siglaRegimeJuridico"))[0],
                    nacionalidade=pessoa.get("codNacionalidade"),
                    email_siape=email_siape.lower(),
                    identificacao_unica_siape=servidor.get("identUnica"),
                    titulo_numero=pessoa.get("numeroTituloEleitor"),
                    titulo_zona=pessoa.get("zonaTituloEleitor"),
                    titulo_secao=pessoa.get("secaoTituloEleitor"),
                    titulo_uf=pessoa.get("ufTituloEleitor"),
                    titulo_data_emissao=self._str_to_date(pessoa.get("dataTituloEleitor")),
                    rg=pessoa.get("numeroCarteiraIdentidade"),
                    rg_orgao=pessoa.get("orgaoCarteiraIdentidade"),
                    rg_data=self._str_to_date(pessoa.get("dataCarteiraIdentidade")),
                    rg_uf=pessoa.get("ufCarteiraIdentidade"),
                    cnh_carteira=pessoa.get("numeroCarteiraMotorista"),
                    cnh_registro=pessoa.get("registroCarteiraMotorista"),
                    cnh_categoria=pessoa.get("categoriaCarteiraMotorista"),
                    cnh_emissao=self._str_to_date(pessoa.get("dataExpedicaoCarteiraMotorista")),
                    cnh_uf=pessoa.get("ufCarteiraMotorista"),
                    cnh_validade=self._str_to_date(pessoa.get("dataValidadeCarteiraMotorista")),
                    ctps_numero=pessoa.get("numeroCarteiraTrabalho"),
                    ctps_uf=pessoa.get("ufCarteiraTrabalho"),
                    ctps_serie=pessoa.get("serieCarteiraTrabalho"),
                    pis_pasep=pessoa.get("numPisPasep"),
                    pagto_banco=Banco.get_or_create(codigo=pessoa.get("banco"))[0],
                    pagto_agencia=pessoa.get("agencia"),
                    pagto_ccor=pessoa.get("contaCorrente"),
                    data_inicio_exercicio_na_instituicao=self._str_to_date(servidor.get("dataExercicioNoOrgao")),
                    nivel_padrao=servidor.get("codPadrao"),
                )

                if ver_dados_apenas:
                    args.update({"nome_apresentacao": capitaliza_nome(pessoa.get("nome"))})

                #
                # Verificando email secundario
                email_secundario = pessoa.get("email_secundario")
                if email_secundario:
                    Configuracao = apps.get_model("comum", "configuracao")
                    if not Configuracao.get_valor_por_chave(
                        "comum", "permite_email_institucional_email_secundario"
                    ) and not Configuracao.eh_email_institucional(email_secundario):
                        args.update({"email_secundario": email_secundario})

                #
                # tratando deficiência
                deficiencia = pessoa.get("codDefFisica")
                if deficiencia:
                    try:
                        deficiencia = Deficiencia.objects.get(codigo=pessoa.get("codDefFisica"))
                        args.update({"deficiencia": deficiencia})
                    except Exception:
                        pass

                #
                # tratando país de origem
                pais_origem = pessoa.get("pais_origem")
                if pais_origem:
                    try:
                        pais_origem = Pais.objects.get(nome=pessoa.get("pais_origem"))
                        args.update({"pais_origem": pais_origem})
                    except Exception:
                        pass
                #
                # tratando nome do município de nascimento
                municipio_nascimento = pessoa.get("nomeMunicipNasc")
                uf_nascimento = pessoa.get("ufNascimento")
                if municipio_nascimento and uf_nascimento:
                    identificacao = Municipio.get_identificacao(municipio_nascimento, uf_nascimento)
                    municipio_nascimento = Municipio.objects.get_or_create(
                        identificacao=identificacao, defaults={"uf": uf_nascimento, "nome": municipio_nascimento}
                    )[0]
                    args.update({"nascimento_municipio": municipio_nascimento})

                #
                # tratando grupo sanguíneo
                gs = pessoa.get("grupoSanguineo")
                if gs:
                    grupo_sanguineo = re.findall("[a-zA-Z]+", gs)
                    fator_rh = re.findall("[-+]+", gs)
                    if grupo_sanguineo and fator_rh:
                        args.update({"grupo_sanguineo": grupo_sanguineo[0], "fator_rh": fator_rh[0]})

                #
                # tratando cargo emprego
                cargo_emprego = servidor.get("codCargo")
                if cargo_emprego:
                    cargo_emprego = CargoEmprego.objects.get_or_create(codigo=cargo_emprego, defaults={"nome": servidor.get("nomeCargo")})[
                        0
                    ]
                    args.update({"cargo_emprego": cargo_emprego})

                #
                # tratando cargo classe
                cargo_classe = servidor.get("codClasse")
                if cargo_classe:
                    cargo_classe = CargoClasse.objects.get_or_create(codigo=cargo_classe, defaults={"nome": servidor.get("nomeClasse")})[0]
                    args.update({"cargo_classe": cargo_classe})

                #
                # tratando atividade da função
                funcao_atividade = servidor.get("codAtivFun")
                if funcao_atividade:
                    funcao_atividade = Atividade.objects.get_or_create(
                        codigo=servidor.get("codAtivFun"), defaults={"nome": servidor.get("nomeAtivFun")}
                    )[0]
                    args.update({"funcao_atividade": funcao_atividade})
                funcao = servidor.get("codFuncao")
                data_ini_funcao = servidor.get("dataIngressoFuncao")
                nova_funcao = servidor.get("codNovaFuncao")
                data_ini_nova_funcao = servidor.get("dataIngressoNovaFuncao")
                if nova_funcao and (not data_ini_funcao or (data_ini_funcao and data_ini_nova_funcao > data_ini_funcao)):
                    nova_funcao = Funcao.objects.get_or_create(
                        codigo=nova_funcao[:3].strip(), defaults={"nome": servidor.get("nomeNovaFuncao")}
                    )[0]
                    args.update({"funcao": nova_funcao})
                elif funcao:
                    funcao = Funcao.objects.get_or_create(codigo=funcao[:3].strip(), defaults={"nome": servidor.get("nomeFuncao")})[0]
                    args.update({"funcao": funcao})

                jornada_trabalho = servidor.get("codJornada")
                if jornada_trabalho:
                    jornada_trabalho = JornadaTrabalho.objects.get(codigo=jornada_trabalho)
                    args.update({"jornada_trabalho": jornada_trabalho})

                #
                # tratando o setor de lotação do servidor
                setor_lotacao = servidor.get("codUorgLotacao")
                if setor_lotacao and setor_lotacao != "":
                    setor_lotacao, created = Setor.siape.get_or_create(codigo=servidor.get("codUorgLotacao"))
                    args.update({"setor_lotacao": setor_lotacao})

                #
                # tratando o setor e setor exercício do servidor
                setor_exercicio = servidor.get("codUorgExercicio")
                setor = None
                if setor_exercicio:
                    Configuracao = apps.get_model("comum", "configuracao")
                    setor_exercicio, created = Setor.siape.get_or_create(codigo=servidor.get("codUorgExercicio"))

                    # o setor de exercício NÃO pode ser o setor raiz (no ifrn)
                    if setor_exercicio.sigla == "IFRN":
                        # verificando o setor exercício do usuário para corrigir o problema do setor raiz errado (apenas IFRN)
                        sigla_re = Configuracao.get_valor_por_chave("comum", "reitoria_sigla")
                        # pegando o setor siape correto para setar no setor_exercicio
                        novo_setor_exercicio = Setor.siape.get(sigla=sigla_re)
                        setor_exercicio = novo_setor_exercicio

                    args.update({"setor_exercicio": setor_exercicio})
                    configuracao_setor = Configuracao.get_valor_por_chave(app="comum", chave="setores")
                    if configuracao_setor == "SIAPE":
                        setor = setor_exercicio
                    else:
                        try:
                            setor_exercicio_split = setor_exercicio.sigla.split("/")
                            sigla_setor = setor_exercicio_split[0]
                            sigla_uo = setor_exercicio_split[1]
                            setor = (
                                Setor.suap.filter(sigla=sigla_setor, uo__sigla=sigla_uo, excluido=False).first()
                                or Setor.suap.filter(sigla=setor_exercicio, uo__sigla=sigla_uo, excluido=False).first()
                            )

                        except Exception:
                            pass
                    if setor:
                        args.update({"setor": setor})

                #
                # tratando dados escolares e titulações
                dados_escolares = pessoa.get("escolar")
                if dados_escolares:
                    nivel_escolar, created = NivelEscolaridade.objects.get_or_create(
                        codigo=dados_escolares.get("codEscolaridade"),
                        defaults={"nome": dados_escolares.get("nomeEscolaridade")},
                    )
                    args.update({"nivel_escolaridade": nivel_escolar})

                dados_titulacoes = pessoa.get("titulacoes")
                if dados_titulacoes:

                    #
                    # procurando a maior titulação
                    if "contracheques" in settings.INSTALLED_APPS:
                        from contracheques import layout

                        d_posicao = {}
                        for k, v in list(layout.classificacao_titulacoes.items()):
                            for t in dados_titulacoes:
                                if t.nomeTitulacao in v:
                                    d_posicao[k] = [t.codTitulacao, t.nomeTitulacao]
                        if d_posicao:
                            dados = d_posicao[max(d_posicao)]
                            titulacao, created = Titulacao.objects.get_or_create(codigo=dados[0], defaults={"nome": dados[1]})
                            args.update({"titulacao": titulacao})

                # tratando a entrada de dados de contracheque via webservices
                dados_contracheques = pessoa.get("dados_contracheques")
                if dados_contracheques.get(int(matricula)):
                    cc_dados = {}
                    for k, v in dados_contracheques.get(int(matricula)).items():
                        lista_rubricas = []
                        for rubrica in v[0]:
                            lista_rubricas.append(
                                {
                                    "valorRubrica": rubrica["valorRubrica"],
                                    "nomeRubrica": rubrica["nomeRubrica"],
                                    "indicadorRD": rubrica["indicadorRD"],
                                    "numeroSeq": rubrica["numeroSeq"],
                                    "pzRubrica": rubrica["pzRubrica"],
                                    "codRubrica": rubrica["codRubrica"],
                                }
                            )
                        if cc_dados.get(matricula):
                            cc_dados.get(matricula).update({k: lista_rubricas})
                        else:
                            cc_dados.update({matricula: {k: lista_rubricas}})
                    args.update({"dados_contracheques": cc_dados})

                # excluindo do args, informações que serão ignoradas na atualização do servidor
                if matricula in excecoes_atualizacao:
                    for campo in excecoes_atualizacao[matricula]:
                        if ver_dados_apenas:
                            args.update(
                                {
                                    campo: "{} <br /><strong>(Não será atualizado)</strong>".format(
                                        args.get(campo),
                                    )
                                }
                            )
                        else:
                            del args[campo]

                # se o parâmetro "ver_dados_apenas" for verdadeiro, iremos retornar o dicionário com as informações
                if ver_dados_apenas:
                    dados_atualizar.append(args)
                else:
                    dados_atualizar.append(self.__efetiva_dados_sevidor(matricula, servidor, pessoa, args))

            return dados_atualizar

        except WebFault:
            raise
        except IndexError:
            raise

    def __efetiva_dados_sevidor(self, matricula, servidor, pessoa, args):
        hoje = date.today()
        Configuracao = apps.get_model("comum", "configuracao")
        configuracao_setor = Configuracao.get_valor_por_chave(app="comum", chave="setores")
        setor_suap = None
        if args.get("setor") and configuracao_setor == "SUAP":
            setor_suap = args.pop("setor")

        # se tiver contracheque, recupera o dado e joga para cc, se não, seta cc igual a none
        # é necessário remover o indice "dados_contracheques" de args para não dar problema no update_or_create de servidor
        cc = None
        if args.get("dados_contracheques"):
            cc = args.pop("dados_contracheques")

        #
        args["data_ultima_atualizacao_webservice"] = hoje
        servidor_atualizado, criado = Servidor.objects.update_or_create(matricula=matricula, defaults=args)
        atualizar_setor = False
        if criado and setor_suap:
            atualizar_setor = True
        elif not criado and setor_suap:
            if not servidor_atualizado.setor in setor_suap.descendentes:
                atualizar_setor = True

        if atualizar_setor:
            servidor_atualizado.setor = setor_suap
            servidor_atualizado.save()

        if servidor.get("dataOcorrIngressoOrgao"):
            ocorrencia = Ocorrencia.objects.get(codigo=servidor.get("codOcorrIngressoOrgao"))
            subgrupo = SubgrupoOcorrencia.objects.get_or_create(descricao="INCLUSAO NO ORGAO")[0]
            ServidorOcorrencia.objects.update_or_create(
                servidor=servidor_atualizado,
                ocorrencia=ocorrencia,
                subgrupo=subgrupo,
                data=self._str_to_date(servidor.get("dataOcorrIngressoOrgao")),
            )

        if servidor.get("dataOcorrIngressoServPublico"):
            ocorrencia = Ocorrencia.objects.get(codigo=servidor.get("codOcorrIngressoServPublico"))
            subgrupo = SubgrupoOcorrencia.objects.get_or_create(descricao="INCLUSAO NO SERVICO PUBLICO")[0]
            ServidorOcorrencia.objects.update_or_create(
                servidor=servidor_atualizado,
                ocorrencia=ocorrencia,
                subgrupo=subgrupo,
                data=self._str_to_date(servidor.get("dataOcorrIngressoServPublico")),
            )

        if servidor.get("codOcorrExclusao"):
            subgrupo = SubgrupoOcorrencia.objects.get_or_create(descricao="EXCLUSAO")[0]
            ocorrencia_exclusao = Ocorrencia.objects.get(codigo=servidor.get("codOcorrExclusao"))
            data_ocorrencia_exclusao = self._str_to_date(servidor.get("dataOcorrExclusao"))
            ServidorOcorrencia.objects.get_or_create(
                servidor=servidor_atualizado,
                ocorrencia=ocorrencia_exclusao,
                data=data_ocorrencia_exclusao,
                subgrupo=subgrupo,
            )

            if servidor_atualizado.servidorreativacaotemporaria_set.filter(data_inicio__lte=hoje, data_fim__gte=hoje).exists():
                Servidor.objects.filter(id=servidor_atualizado.id).update(excluido=False)
            else:
                Servidor.objects.filter(id=servidor_atualizado.id).update(excluido=True)

            historico_setores_servidor = ServidorSetorHistorico.objects.filter(servidor=servidor_atualizado).order_by(
                "-data_inicio_no_setor"
            )
            if historico_setores_servidor.exists():
                setor_mais_atual = historico_setores_servidor[0]
                if not setor_mais_atual.data_fim_no_setor:
                    setor_mais_atual.data_fim_no_setor = data_ocorrencia_exclusao
                    setor_mais_atual.save()

        data_ingresso_orgao = self._str_to_date(servidor.get("dataOcorrIngressoOrgao"))
        data_inicio_exercicio = self._str_to_date(servidor.get("dataExercicioNoOrgao"))
        data_ingresso_servico_publico = self._str_to_date(servidor.get("dataOcorrIngressoServPublico"))

        Servidor.objects.filter(id=servidor_atualizado.id).update(
            data_inicio_servico_publico=data_ingresso_servico_publico,
            data_posse_na_instituicao=data_ingresso_orgao,
            data_posse_no_cargo=servidor_atualizado.calcula_posse_no_cargo,
            data_inicio_exercicio_no_cargo=data_inicio_exercicio,
            data_fim_servico_na_instituicao=servidor_atualizado.calcula_fim_servico_na_instituicao,
        )
        self.atualiza_historico_funcao(servidor, servidor_atualizado, args)

        """
        Atualiza dados da pessoa Física a partir do serviço get_dados_endereço_residencial
        """
        pessoa_fisica = servidor_atualizado.pessoa_fisica
        if pessoa.get("logradouro") and pessoa.get("uf") and pessoa.get("nomeMunicipio"):
            municipio = Municipio.get_or_create(pessoa.get("nomeMunicipio"), pessoa.get("uf"))[0]
            for pe in PessoaEndereco.objects.filter(pessoa__id=pessoa_fisica.pk):
                pe.__skip_history = True
                pe.delete()
            endereco = PessoaEndereco(
                pessoa_id=pessoa_fisica.pk,
                logradouro=pessoa["logradouro"],
                numero=pessoa["numero"],
                complemento=pessoa["complemento"],
                bairro=pessoa["bairro"],
                municipio=municipio,
                cep=pessoa["cep"]
            )
            endereco.__skip_history = True
            endereco.save()
        if pessoa.get("dddTelefone") and pessoa.get("numTelefone"):
            for pt in PessoaTelefone.objects.filter(pessoa__id=pessoa_fisica.pk):
                pt.__skip_history = True
                pt.delete()
            fone_numero = pessoa.get("numTelefone")
            fone_ddd = pessoa.get("dddTelefone")
            if fone_numero and fone_ddd:
                telefone_formatado = format_telefone(fone_ddd, fone_numero)
                telefone = PessoaTelefone(pessoa=pessoa_fisica, numero=telefone_formatado)
                telefone.__skip_history = True
                telefone.save()

        # contracheque
        if cc and "contracheques" in settings.INSTALLED_APPS:
            if cc:
                ContraCheque = apps.get_model("contracheques", "ContraCheque")
                contra_cheque = ContraCheque()
                contra_cheque.importar_contracheque_webservice(cc)

        return servidor_atualizado, criado

    def atualiza_historico_funcao(self, servidor, servidor_atualizado, args):
        ultima_funcao_suap = (
            ServidorFuncaoHistorico.objects.filter(servidor_id=servidor_atualizado.id, funcao__funcao_siape=True)
            .order_by("data_inicio_funcao")
            .last()
        )
        setor_exercicio = Setor.siape.get(codigo=servidor.get("codUorgExercicio"))
        data_inicio_funcao_siape = self._str_to_date(servidor.get("dataIngressoFuncao"))
        data_inicio_nova_funcao_siape = self._str_to_date(servidor.get("dataIngressoNovaFuncao"))
        servidor_atualizado_kwargs = {}
        # Verifica se não é aposentado e se tem função nova
        if data_inicio_nova_funcao_siape and (
            not ultima_funcao_suap or (ultima_funcao_suap and ultima_funcao_suap.data_inicio_funcao < data_inicio_nova_funcao_siape)
        ):
            if ultima_funcao_suap and ultima_funcao_suap.data_fim_funcao is None:
                ServidorFuncaoHistorico.objects.filter(id=ultima_funcao_suap.id).update(data_fim_funcao=data_inicio_nova_funcao_siape)
            ServidorFuncaoHistorico.objects.create(
                servidor_id=servidor_atualizado.id,
                data_inicio_funcao=self._str_to_date(servidor.get("dataIngressoNovaFuncao")),
                nivel=servidor.get("codNovaFuncao")[3:],
                funcao_id=args.get("funcao").id,
                setor_id=setor_exercicio.id,
            )
            servidor_atualizado_kwargs["funcao_id"] = args.get("funcao").id
            servidor_atualizado_kwargs["funcao_codigo"] = servidor.get("codNovaFuncao")[3:]

        elif data_inicio_funcao_siape and (
            not ultima_funcao_suap or (ultima_funcao_suap and ultima_funcao_suap.data_inicio_funcao < data_inicio_funcao_siape)
        ):
            if ultima_funcao_suap and ultima_funcao_suap.data_fim_funcao is None:
                ServidorFuncaoHistorico.objects.filter(id=ultima_funcao_suap.id).update(data_fim_funcao=data_inicio_funcao_siape)
            ServidorFuncaoHistorico.objects.create(
                servidor_id=servidor_atualizado.id,
                data_inicio_funcao=self._str_to_date(servidor.get("dataIngressoFuncao")),
                nivel=servidor.get("codFuncao")[3:],
                funcao_id=args.get("funcao").id,
                setor_id=setor_exercicio.id,
                atividade_id=args.get("funcao_atividade").id,
            )
            # Atualizando dados em servidor
            servidor_atualizado_kwargs["funcao_id"] = args.get("funcao").id
            servidor_atualizado_kwargs["funcao_codigo"] = servidor.get("codFuncao")[3:]
            servidor_atualizado_kwargs["funcao_atividade"] = args.get("funcao_atividade").id

        elif data_inicio_funcao_siape and ultima_funcao_suap and data_inicio_funcao_siape == ultima_funcao_suap.data_inicio_funcao:
            ServidorFuncaoHistorico.objects.filter(id=ultima_funcao_suap.id).update(
                nivel=servidor.get("codFuncao")[3:],
                funcao_id=args.get("funcao").id,
                setor_id=setor_exercicio.id,
                atividade_id=args.get("funcao_atividade").id,
            )
            servidor_atualizado_kwargs["funcao_id"] = args.get("funcao").id
            servidor_atualizado_kwargs["funcao_codigo"] = servidor.get("codFuncao")[3:]
            servidor_atualizado_kwargs["funcao_atividade"] = args.get("funcao_atividade").id
        elif not data_inicio_funcao_siape and not data_inicio_nova_funcao_siape and servidor_atualizado.funcao:
            # Zerando o registro nos atributos em servidor
            servidor_atualizado_kwargs["funcao_id"] = None
            servidor_atualizado_kwargs["funcao_codigo"] = ""
            servidor_atualizado_kwargs["funcao_atividade"] = None

        if servidor_atualizado_kwargs:
            Servidor.objects.filter(id=servidor_atualizado.id).update(**servidor_atualizado_kwargs)

    def atualizar_ferias_afastamentos(self, cpf, mes_inicio=1, mes_fim=12, ano_inicio=date.today().year, ano_fim=date.today().year + 1):
        try:
            count = 1
            interar = True
            dados_afastamentos = None
            while interar:
                try:
                    dados_afastamentos = self.get_afastamento_historico(
                        cpf, mes_inicio=mes_inicio, mes_fim=mes_fim, ano_inicio=ano_inicio, ano_fim=ano_fim
                    )
                    interar = False
                except Exception:
                    if count < 3:
                        count += 1
                    else:
                        interar = False
            if dados_afastamentos and Ferias:
                lista_parcelas = dados_afastamentos.get("ferias")
                ferias_atualizadas = dict()
                for parcela in lista_parcelas:
                    ferias, created = Ferias.objects.get_or_create(ano=parcela["ferias"].ano, servidor=parcela["ferias"].servidor)
                    parcela["ferias"] = ferias
                    numero_parcela = parcela["numero_parcela"]
                    ParcelaFerias.objects.update_or_create(numero_parcela=numero_parcela, ferias=ferias, defaults=parcela)
                    ferias.atualiza_pelo_extrator = False
                    ferias.save()
                    if not created:
                        if ferias_atualizadas.get(ferias.pk):
                            ferias_atualizadas[ferias.pk].append(numero_parcela)
                        else:
                            ferias_atualizadas[ferias.pk] = [numero_parcela]

                for ferias_pk, parcelas in ferias_atualizadas.items():
                    ParcelaFerias.objects.filter(ferias__pk=ferias_pk).exclude(numero_parcela__in=parcelas).delete()

                lista_afastamentos = dados_afastamentos.get("afastamentos")
                for dado_afastamento in lista_afastamentos:
                    servidor = dado_afastamento["servidor"]
                    afastamento = dado_afastamento["afastamento"]
                    data_inicio = dado_afastamento["data_inicio"]
                    ServidorAfastamento.objects.update_or_create(
                        servidor=servidor, afastamento=afastamento, data_inicio=data_inicio, defaults=dado_afastamento
                    )
        except Exception:
            raise

    # '''
    # Setando setores do servidor
    # '''
    # def _set_setores(self, servidor):
    #
    #     '''
    #     Precisamos tratar os setores:
    #      - campo setor em Funcionario
    #         pelos testes realizados, é o mesmo setor de exercício
    #
    #      - campo setor_lotacao em Funcionario
    #
    #      - campo setor_funcao em Funcionario
    #         pelos testes realizados, é o mesmo setor de exercício
    #
    #      - campo setor_exercicio em Servidor
    #
    #     Verificar os históricos:
    #      - ServidorSetorHistorico
    #      - ServidorSetorLotacaoHistorico
    #     '''
    #
    #
    #
    #     return

    def importacao_servidor_completo(self, cpf):
        try:
            self.importacao_servidor(cpf)
        except Exception:
            return False
        return True

    """ Importação completa."""

    def importacao_completa(self):
        #
        # ??? 236 = COSINF

        self.get_lista_uorgs(236)

        lista = self.get_lista_servidores(self.lista_uorgs[0][0])

        cpfs_errors = list()

        for s in lista.get("236").get("servidores").Servidor:
            importou = self.importacao_servidor_completo(s.cpf)
            if not importou:
                cpfs_errors.append(s.cpf)
                continue

    """ Processamento geral de importação. Importação completa."""

    def processarImportacao(self):
        print(self.lista_uorgsq)
