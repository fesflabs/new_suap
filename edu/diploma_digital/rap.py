import os
import base64
import jsonschema
import json
import requests
from datetime import datetime
from comum.utils import get_sigla_reitoria
from djtools.utils import mask_cpf, mask_cnpj
from djtools.utils.response import XmlResponse, PDFResponse
from edu.models import Modalidade
from edu.models.cadastros_gerais import Cidade
from edu.models.cursos import Autorizacao, Reconhecimento, MatrizCurso
from edu.models.regulacao import Credenciamento
from comum.models import Configuracao
from rh.models import UnidadeOrganizacional
from edu.models.diplomas import RegistroEmissaoDiploma, SincronizacaoAssinaturaDigital
import tempfile
from djtools.storages import cache_file
from django.conf import settings

"""
"TermoResponsabilidade",
"DocumentoIdentidadeDoAluno",
"ProvaConclusaoEnsinoMedio",
"HistoricoEscolar",
"ProvaColacao",
"ComprovacaoEstagioCurricular",
"CertidaoNascimento",
"CertidaoCasamento",
"TituloEleitor",
"AtoNaturalizacao",
"Outros"

https://www.jsonschemavalidator.net/
http://validadordiplomadigital.mec.gov.br/
https://avepdf.com/pt/convert-to-pdfa
https://demo.verapdf.org/

"""
ERRO_CONECTIVIDADE = 998

STATUS = {
    0: 'Esperando geração',
    1: 'Geração iniciada',
    2: 'Arquivo Gerado',
    3: 'Assinatura em construção',
    4: 'Assinatura iniciada',
    5: 'Assinatura iniciada',
    6: 'Assinatura finalizada',
    7: 'Registro iniciado',
    8: 'Registrando',
    9: 'Registrando',
    10: 'Documento Concluído',
    11: 'Documento Suspenso',
    12: 'Revogação Solicitada',
    13: 'Revogando',
    14: 'Revogado',
    500: 'Erro preparando geração do documento',
    501: 'Erro gerando documento',
    502: 'Erro inicializando processamento de assinaturas',
    503: 'Erro finalizando processamento de assinaturas',
    504: 'Erro Iniciando processo de registro',
    505: 'Erro finalizando processo de registro',
    506: 'Erro revogando documento',
    ERRO_CONECTIVIDADE: 'Erro de conectividade com o RAP',
}

DOCUMENTO_CONCLUIDO = 10
MOCK = False


class MockedResponse:
    def __init__(self):
        self.text = '{"documentId":1}'


class AssinadorDigital:

    def __init__(self, debug=settings.DEBUG):
        self.token = None
        self.debug = debug

    def log(self, data):
        if self.debug:
            line = f'[{datetime.now()}] - {data}'
            print(line)
            with open('rap.log', 'a') as file:
                file.write(line)
                file.write('\n-------\n')

    def headers(self):
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        if self.token is None:
            url = f'{rap_api_url}/api/users/auth'
            data = {
                'email': Configuracao.get_valor_por_chave('edu', 'rap_api_user'),
                'password': Configuracao.get_valor_por_chave('edu', 'rap_api_password')
            }
            self.log(url)
            response = requests.post(url, json=data).json()
            self.log(response)
            self.token = response['accessToken']
        return {'Authorization': f'Bearer {self.token}'}

    def listar_documentos(self):
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents?page=0&limit=10'
        self.log(url)
        response = requests.get(url, headers=self.headers())
        self.log(response.text)
        return json.loads(response.text)

    def registrar_erro_cadastro(self, assinatura_digital, detalhe):
        self.log(f'{assinatura_digital.id} - {detalhe}')
        sincronizacao = SincronizacaoAssinaturaDigital.objects.filter(
            assinatura_digital=assinatura_digital
        ).order_by('-id').first()
        if sincronizacao is None or sincronizacao.detalhe != detalhe:
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe=detalhe
            )

    def consultar_documento(self, assinatura_digital, tipo):
        try:
            id_attr = f'id_{tipo}'
            status_attr = f'status_{tipo}'
            if MOCK:
                return 10
            rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
            url = f'{rap_api_url}/api/documents/{getattr(assinatura_digital, id_attr)}/'
            self.log(url)
            response = requests.get(url, headers=self.headers())
            self.log(response.text)
            codigo_retorno = json.loads(response.text).get('currentState')
            if codigo_retorno is not None:
                if codigo_retorno != getattr(assinatura_digital, status_attr):
                    detalhe = 'Alteração da situação do documento {}: {}.'.format(
                        getattr(assinatura_digital, id_attr), STATUS[codigo_retorno]
                    )
                    self.log(f'{assinatura_digital.id} - {detalhe}')
                    SincronizacaoAssinaturaDigital.objects.create(assinatura_digital=assinatura_digital, detalhe=detalhe)
                    setattr(assinatura_digital, status_attr, codigo_retorno)
                    assinatura_digital.save()
        except ConnectionError:
            return ERRO_CONECTIVIDADE
        return codigo_retorno

    def excluir_documento(self, id):
        if MOCK:
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/{id}/'
        self.log(url)
        response = requests.delete(url)
        self.log(response.text)
        return json.loads(response.text)

    def revogar_documento(self, id):
        if MOCK:
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/{id}/revoke'
        self.log(url)
        response = requests.post(url, headers=self.headers())
        self.log(response.text)
        try:
            return json.loads(response.text)
        except Exception as e:
            return {'error_message': str(e)}

    def consultar_status_documento(self, id):
        if MOCK:
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/{id}/state'
        self.log(url)
        response = requests.get(url, headers=self.headers())
        self.log(response.text)
        status = []
        data = json.loads(response.text)
        for signature in data['signatures']:
            substitute = '{} - {}'.format(
                mask_cpf(signature['substituteSigner']['identification']), signature['substituteSigner']['name']
            ) if signature['substituteSigner'] else ''
            if len(signature['signerId']) == 11:
                documento = mask_cpf(signature['signerId'])
            else:
                documento = mask_cnpj(signature['signerId'])
            status.append(
                dict(
                    documento=documento,
                    nome=signature['signer'],
                    tipo=signature['archivingSignature'] and 'ARQUIVAMENTO' or 'NORMAL',
                    situacao=signature['signatureState'] == 2 and 'ASSINADO' or 'PENDENTE',
                    substituto=substitute
                )
            )
        return status

    def reprocessar_documento(self, id):
        if MOCK:
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/{id}/restart-processing'
        self.log(url)
        response = requests.post(url, headers=self.headers())
        self.log(response.text)
        return json.loads(response.text)

    def baixar_xml(self, id, as_http_response=False):
        if MOCK:
            return '<DadosDiploma id="1"></DadosDiploma>'
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = '{}/api/documents/{}/files/{}'.format(rap_api_url, id, 'signedDocument')
        response = requests.get(url, headers=self.headers())
        if as_http_response:
            return XmlResponse(response.text)
        else:
            return response.text

    def baixar_pdf(self, id, as_http_response=False):
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = '{}/api/documents/{}/files/{}'.format(rap_api_url, id, 'signedDocument')
        response = requests.get(url, headers=self.headers())
        pdf_file_path = tempfile.mktemp('.pdf')
        with open(pdf_file_path, 'wb') as f:
            for chunk in response:
                f.write(chunk)
        if as_http_response:
            return PDFResponse(open(pdf_file_path, 'rb').read())
        else:
            return pdf_file_path

    def sincronizar(self, assinatura_digital):
        if assinatura_digital.id_documentacao_academica_digital == 0:
            self.enviar_documentacao_academica(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_DADOS:
            self.enviar_documentacao_academica(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DOCUMENTACAO:
            self.consultar_documentacao_academica(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_HISTORICO:
            self.enviar_historico_escolar(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_HISTORICO:
            self.consultar_historico_escolar(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_DADOS_DIPLOMA:
            self.enviar_dados_diploma(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DIPLOMA:
            self.consultar_dados_diploma(assinatura_digital)
        elif assinatura_digital.registro_emissao_diploma.situacao == RegistroEmissaoDiploma.AGUARDANDO_CONFECCAO_DIPLOMA:
            self.consultar_representacao_diploma(assinatura_digital)
        else:
            if assinatura_digital.status_documentacao_academica_digital == DOCUMENTO_CONCLUIDO:
                if assinatura_digital.status_dados_diploma_digital == DOCUMENTO_CONCLUIDO:
                    if assinatura_digital.status_representacao_diploma_digital == DOCUMENTO_CONCLUIDO:
                        if not assinatura_digital.concluida:
                            assinatura_digital.concluida = True
                            assinatura_digital.save()

    def consultar_documentacao_academica(self, assinatura_digital):
        codigo_retorno = self.consultar_documento(assinatura_digital, 'documentacao_academica_digital')
        if codigo_retorno is not None:
            if codigo_retorno >= 6:
                if codigo_retorno in (500, 501, 502, 503, ERRO_CONECTIVIDADE):  # ocorreu um erro na geração ou assinatura do documento
                    SincronizacaoAssinaturaDigital.objects.create(
                        assinatura_digital=assinatura_digital, detalhe=STATUS[codigo_retorno]
                    )
                else:  # ocorreu no processo de registro. no entanto, assinatura do diploma poderá ocorrer
                    self.enviar_historico_escolar(assinatura_digital)
        else:
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe='Arquivo da documentação acadêmica em criação.'
            )

    def consultar_historico_escolar(self, assinatura_digital):
        codigo_retorno = self.consultar_documento(assinatura_digital, 'historico_escolar')
        if codigo_retorno is not None:
            if codigo_retorno >= 6:
                if codigo_retorno in (500, 501, 502, 503, ERRO_CONECTIVIDADE):  # ocorreu um erro na geração ou assinatura do documento
                    SincronizacaoAssinaturaDigital.objects.create(
                        assinatura_digital=assinatura_digital, detalhe=STATUS[codigo_retorno]
                    )
                else:  # ocorreu no processo de registro. no entanto, assinatura do diploma poderá ocorrer
                    self.enviar_dados_diploma(assinatura_digital)
        else:
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe='Arquivo do histórico escolar em criação.'
            )

    def consultar_dados_diploma(self, assinatura_digital):
        self.consultar_documento(assinatura_digital, 'documentacao_academica_digital')
        codigo_retorno = self.consultar_documento(assinatura_digital, 'dados_diploma_digital')
        if codigo_retorno is not None:
            if codigo_retorno >= 6:
                if codigo_retorno in (500, 501, 502, 503, ERRO_CONECTIVIDADE):  # ocorreu um erro na geração ou assinatura do documento
                    SincronizacaoAssinaturaDigital.objects.create(
                        assinatura_digital=assinatura_digital, detalhe=STATUS[codigo_retorno]
                    )
                else:  # ocorreu no processo de registro. no entanto, o envio da representação visual pode ser feito
                    assinatura_digital = assinatura_digital.gerar_representacao_visual()
                    self.enviar_representacao_diploma(assinatura_digital)
        else:
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe='Arquivo dos dados do diploma em criação.'
            )

    def consultar_representacao_diploma(self, assinatura_digital):
        self.consultar_documento(assinatura_digital, 'documentacao_academica_digital')
        self.consultar_documento(assinatura_digital, 'dados_diploma_digital')
        codigo_retorno = self.consultar_documento(assinatura_digital, 'representacao_diploma_digital')
        if codigo_retorno == DOCUMENTO_CONCLUIDO:
            registro = assinatura_digital.registro_emissao_diploma
            registro.situacao = RegistroEmissaoDiploma.FINALIZADO
            registro.save()
            assinatura_digital.concluida = True
            assinatura_digital.save()
            registro.enviar_por_email()

    def enviar_documentacao_academica(self, assinatura_digital, apenas_validacao=False):
        erros = []
        registro = assinatura_digital.registro_emissao_diploma
        if registro.aluno.polo:
            if not registro.aluno.polo.cidade or not registro.aluno.polo.cep or not registro.aluno.polo.logradouro or not registro.aluno.polo.numero or not registro.aluno.polo.bairro:
                erros.append(f'Endereço do Polo "{registro.aluno.polo}" relacionado ao curso do aluno')
            if not registro.aluno.polo.codigo_censup:
                erros.append(f'Código EMEC do Polo "{registro.aluno.polo}"')

        situacao_enade = None
        data_prova_endade = None
        if registro.aluno.matriz_id:
            if not registro.aluno.get_participacao_colacao_grau():
                erros.append('Registro da Colação de Grau')
            registro_convocacao_enade = registro.aluno.get_convocacoes_enade().last()
            if registro_convocacao_enade is None:
                erros.append('Registro do ENADE')
            elif registro_convocacao_enade.get_situacao_para_diploma_digital() is None:
                erros.append('Situação do ENADE')
            else:
                situacao_enade = registro_convocacao_enade.get_situacao_para_diploma_digital()
                data_prova_endade = registro_convocacao_enade.convocacao_enade.data_prova.strftime('%Y-%m-%d') if 'Participante' in registro_convocacao_enade.get_situacao_para_diploma_digital() else None

        if registro.aluno.numero_rg is None:
            erros.append('Número do documento de identidade (RG)')
        if registro.aluno.uf_emissao_rg is None:
            erros.append('UF de emissão do documento de identidade (RG)')
        if registro.aluno.naturalidade is None:
            erros.append('Naturalidade do aluno')

        reitoria = UnidadeOrganizacional.objects.suap().get(setor__sigla=get_sigla_reitoria())

        nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
        codigo_mec = Configuracao.get_valor_por_chave('comum', 'codigo_mec') or '1082'
        ultima_matriz_curso = MatrizCurso.objects.filter(
            curso_campus=registro.aluno.curso_campus
        ).order_by('-matriz__data_inicio').first()

        autorizacao = Autorizacao.objects.filter(
            matriz_curso__matriz=registro.aluno.matriz or ultima_matriz_curso.matriz_id,
            matriz_curso__curso_campus=registro.aluno.curso_campus
        ).order_by('id').last()
        reconhecimento = Reconhecimento.objects.filter(
            renovacao=False,
            matriz_curso__matriz=registro.aluno.matriz or ultima_matriz_curso.matriz_id,
            matriz_curso__curso_campus=registro.aluno.curso_campus
        ).order_by('id').last()
        renovacao_reconhecimento = Reconhecimento.objects.filter(
            renovacao=True,
            matriz_curso__matriz=registro.aluno.matriz or ultima_matriz_curso.matriz_id,
            matriz_curso__curso_campus=registro.aluno.curso_campus
        ).order_by('id').last()

        credenciamento = Credenciamento.objects.filter(
            tipo=Credenciamento.CREDECIAMENTO
        ).order_by('id').last()
        recredenciamento = Credenciamento.objects.filter(
            tipo=Credenciamento.RECREDECIAMENTO
        ).order_by('id').last()
        renovacao_recredenciamento = Credenciamento.objects.filter(
            tipo=Credenciamento.RENOVACAO_RECREDECIAMENTO
        ).order_by('id').last()

        if registro.aluno.curso_campus.diretoria.setor.uo.numero is None:
            erros.append('Número do endereço do campus {}.'.format(
                registro.aluno.curso_campus.diretoria.setor.uo
            ))

        if reitoria.numero is None:
            erros.append('Número do endereço da reitoria.')

        if autorizacao is None:
            erros.append('Cadastro da autorização do curso')
        if reconhecimento is None:
            erros.append('Cadastro do reconhecimento do curso')
        if credenciamento is None and recredenciamento is None and renovacao_recredenciamento is None:
            erros.append('Cadastro do (re)credenciamento da instituição')
        if registro.aluno.curso_campus.modalidade.grupoarquivoobrigatorio_set.all().exists():
            if not registro.aluno.alunoarquivo_set.all().exists():
                erros.append('Pasta documental vazia')
            elif not registro.aluno.possui_todos_documentos_obrigatorios():
                erros.append('Documentos obrigatórios na pasta documental')
        documentos_aluno = []
        for aluno_arquivo in registro.aluno.get_documentos_obrigatorios():
            try:
                documento = {
                    "Documento": {
                        "Tipo": aluno_arquivo.get_tipo_diploma_exibicao(),
                        "Observacoes": aluno_arquivo.tipo.nome,
                        "Arquivo": base64.b64encode(open(aluno_arquivo.to_pdfa(), 'r+b').read()).decode()
                    }
                }
            except Exception:
                erros.append(
                    'O arquivo {} contido na pasta documental não pôde ser utilizado'.format(aluno_arquivo.tipo))
            documentos_aluno.append(documento)
        if erros:
            detalhe = 'É necessária a correção das seguintes informações: {}'.format(
                '; '.join(erros)
            )
            self.registrar_erro_cadastro(assinatura_digital=assinatura_digital, detalhe=detalhe)
            registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_DADOS
            registro.save()
            return

        def _titulacao(titulacao):
            if titulacao:
                if titulacao.lower().startswith('gra'):
                    return 'Graduação'
                elif titulacao.lower().startswith('esp'):
                    return 'Especialização'
                elif titulacao.lower().startswith('mes'):
                    return 'Mestrado'
                elif titulacao.lower().startswith('dou'):
                    return 'Doutorado'
            return 'Graduação'

        disciplinas = []
        if registro.aluno.is_qacademico():
            historico = registro.aluno.get_historico_legado(final=True)
            data_colacao_grau = historico['data_colacao_grau']
            dados_enade = []
            if historico['convocacoes']:
                for convocacao_enade in historico['convocacoes']:
                    situacao_enade = convocacao_enade['situacao_para_diploma_digital']
                    data_prova_endade = convocacao_enade['data_prova_enade'].strftime('%Y-%m-%d') if situacao_enade and 'Participante' in situacao_enade else None
                    if situacao_enade:
                        if situacao_enade != 'Ingressante / Participante':
                            dados_enade.append({
                                "SituacaoENADE": {
                                    "NaoHabilitado": {
                                        "Condicao": convocacao_enade['tipo_convocacao'],
                                        "Edicao": str(data_prova_endade.year),
                                        "Motivo": situacao_enade
                                    }
                                }
                            })
                        else:
                            dados_enade.append({
                                "SituacaoENADE": {
                                    "Habilitado": {
                                        "Condicao": convocacao_enade['tipo_convocacao'],
                                        "Edicao": str(data_prova_endade.year),
                                    }
                                }
                            })

            if not dados_enade:
                self.registrar_erro_cadastro(assinatura_digital=assinatura_digital, detalhe='Situação do ENADE no Q-Acadêmico')
                registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_DADOS
                registro.save()
                return
        else:
            historico = registro.aluno.get_historico(final=True, ordernar_por=2)
            data_colacao_grau = registro.aluno.get_participacao_colacao_grau().colacao_grau.data_colacao
            dados_enade = [
                convocacao.get_situacao_para_diploma_digital() for convocacao in registro.aluno.get_convocacoes_enade()
            ]

        for tipo, componentes in historico['grupos_componentes'].items():
            for componente_curricular in componentes:
                disciplinas.append(
                    {
                        "Disciplina":
                        {
                            "NomeDisciplina": componente_curricular['descricao_componente'].strip(),
                            "CodigoDisciplina": componente_curricular['sigla_componente'].strip(),
                            "PeriodoLetivo": componente_curricular['ano_periodo_letivo'].replace('/', '.'),
                            "CargaHoraria": {'HoraRelogio': '{:.2f}'.format(float(componente_curricular['carga_horaria']))},
                            "NotaAteCem": '{:.2f}'.format(componente_curricular['media_final_disciplina'] or 0),
                            "Docentes": [
                                {
                                    'Docente': {
                                        "Nome": nome.strip() if nome else 'Não Informado',
                                        "Titulacao": _titulacao(titulacao) if titulacao else 'Não Informada'
                                    }
                                    for _, _, nome, titulacao in componente_curricular.get('professores') or [(None, None, 'Não Informado', 'Graduação')]  # TODO Caso a lista esteja vazia, ocorre um erro
                                }
                            ],
                            "Situacao": {
                                "Aprovado":
                                    {
                                        "FormaIntegralizacao": "Aproveitado" if (componente_curricular['certificada'] or componente_curricular['aproveitada']) else "Cursado"  # TODO "Aprovado", "Reprovado", "Trancado"
                                    }
                            }
                        }
                    }
                )
        if registro.aluno.curso_campus.modalidade_id == Modalidade.LICENCIATURA:
            grau_conferido = 'Licenciatura'
        elif registro.aluno.curso_campus.modalidade_id == Modalidade.ENGENHARIA:
            grau_conferido = 'Bacharelado'
        elif registro.aluno.curso_campus.modalidade_id == Modalidade.BACHARELADO:
            grau_conferido = 'Bacharelado'
        else:
            grau_conferido = 'Tecnólogo'

        dados_documentacao = {
            "meta": {
                "clientId": Configuracao.get_valor_por_chave('edu', 'rap_client_id'),
                "yourNumber": f'DOC{registro.pk}',
                "dltId": "ethereum",
                "docType": "academic_doc_mec_degree",
                "mimeType": "text/xml",
                "groupId": f'REG{registro.pk}',
                "clientSignature": f'REG{registro.pk}'
            },
            "data": {
                "Versao": "1.04.1",
                "ambiente": "Homologação" if settings.DEBUG else "Produção",
                "RegistroReq": {
                    "DadosDiploma": {
                        "Diplomado": {
                            'ID': str(registro.aluno.pk),
                            'Nome': registro.aluno.pessoa_fisica.nome,
                            "Sexo": registro.aluno.pessoa_fisica.sexo,
                            "Nacionalidade": registro.aluno.nacionalidade,
                            "Naturalidade": {
                                "CodigoMunicipio": f'{registro.aluno.naturalidade.codigo}',
                                "NomeMunicipio": registro.aluno.naturalidade.nome,
                                "UF": registro.aluno.naturalidade.estado.get_sigla()
                            },
                            "CPF": registro.aluno.pessoa_fisica.cpf.replace('-', '').replace('.', ''),
                            "RG": {
                                "Numero": "{}".format(registro.aluno.numero_rg.replace('-', '').replace('.', '')),
                                "UF": registro.aluno.uf_emissao_rg.get_sigla()
                            },
                            "DataNascimento": registro.aluno.pessoa_fisica.nascimento_data.strftime('%Y-%m-%d')
                        },
                        "DadosCurso": {
                            "NomeCurso": registro.aluno.curso_campus.descricao_historico,
                            "CodigoCursoEMEC": registro.aluno.curso_campus.codigo_emec,
                            "NomeHabilitacao": [registro.aluno.curso_campus.descricao_historico],   # TODO
                            "Modalidade": 'EAD' if registro.aluno.curso_campus.natureza_participacao.descricao.lower() == 'ead' else 'Presencial',
                            "TituloConferido": dict(OutroTitulo=registro.aluno.pessoa_fisica.sexo == 'M' and registro.aluno.curso_campus.titulo_certificado_masculino or registro.aluno.curso_campus.titulo_certificado_feminino),
                            "GrauConferido": grau_conferido,
                            "EnderecoCurso": {
                                'NomeMunicipio': Cidade.get_cidade_by_municipio(
                                    registro.aluno.curso_campus.diretoria.setor.uo.municipio).nome,
                                'Número': registro.aluno.curso_campus.diretoria.setor.uo.numero,
                                'CodigoMunicipio': Cidade.get_cidade_by_municipio(
                                    registro.aluno.curso_campus.diretoria.setor.uo.municipio).codigo,
                                'Bairro': registro.aluno.curso_campus.diretoria.setor.uo.bairro,
                                'Logradouro': registro.aluno.curso_campus.diretoria.setor.uo.endereco,
                                'CEP': registro.aluno.curso_campus.diretoria.setor.uo.cep.replace('.', '').replace('-',
                                                                                                                   ''),
                                'UF': registro.aluno.curso_campus.diretoria.setor.uo.municipio.uf,
                                "Complemento": '-',
                            },
                            "Polo": registro.aluno.polo and {
                                "Nome": registro.aluno.polo.descricao,
                                "Endereco": {
                                    "Logradouro": registro.aluno.polo.logradouro,
                                    "Numero": registro.aluno.polo.numero,
                                    "Complemento": "-",
                                    "Bairro": registro.aluno.polo.bairro,
                                    "CodigoMunicipio": registro.aluno.polo.cidade.codigo,
                                    "NomeMunicipio": registro.aluno.polo.cidade.nome,
                                    "UF": registro.aluno.polo.cidade.estado.get_sigla(),
                                    "CEP": registro.aluno.polo.cep.replace('.', '').replace('-', '')
                                },
                                "CodigoEMEC": registro.aluno.polo.codigo_censup
                            } or None,
                            "Autorizacao": autorizacao and {
                                "Tipo": autorizacao.tipo,
                                "Numero": autorizacao.numero,
                                "Data": autorizacao.data.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": autorizacao.veiculo_publicacao and autorizacao.veiculo_publicacao or None,
                                "DataPublicacao": autorizacao.veiculo_publicacao and autorizacao.data_publicacao.strftime('%Y-%m-%d') or None,
                                "SecaoPublicacao": autorizacao.veiculo_publicacao and autorizacao.secao_publicacao or None,
                                "PaginaPublicacao": autorizacao.veiculo_publicacao and autorizacao.pagina_publicacao or None
                            } or None,
                            "Reconhecimento": reconhecimento and {
                                "Tipo": reconhecimento.tipo,
                                "Numero": reconhecimento.numero,
                                "Data": reconhecimento.data.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.veiculo_publicacao or None,
                                "DataPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.data_publicacao.strftime('%Y-%m-%d') or None,
                                "SecaoPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.secao_publicao or None,
                                "PaginaPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.pagina_publicao or None
                            } or None,
                            "RenovacaoReconhecimento": renovacao_reconhecimento and {
                                "Tipo": reconhecimento.tipo,
                                "Numero": reconhecimento.numero,
                                "Data": reconhecimento.data.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.veiculo_publicacao or None,
                                "DataPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.data_publicacao.strftime('%Y-%m-%d') or None,
                                "SecaoPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.secao_publicao or None,
                                "PaginaPublicacao": reconhecimento.veiculo_publicacao and reconhecimento.pagina_publicao or None
                            } or None
                        },
                        "IesEmissora": {
                            "Nome": nome_instituicao,
                            "CodigoMEC": codigo_mec,
                            "CNPJ": reitoria.cnpj.replace('.', '').replace('/', '').replace('-', ''),
                            "Endereco": {
                                'NomeMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).nome,
                                'Número': reitoria.numero,
                                'CodigoMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).codigo,
                                'Bairro': reitoria.bairro,
                                'Logradouro': reitoria.endereco,
                                'CEP': reitoria.cep.replace('.', '').replace('-', ''),
                                'UF': reitoria.municipio.uf,
                                "Complemento": '-',
                            },
                            "Credenciamento": credenciamento and {
                                "Tipo": credenciamento.tipo_ato,
                                "Numero": credenciamento.numero_ato,
                                "Data": credenciamento.data_ato.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": credenciamento.veiculo_publicacao,
                                "DataPublicacao": credenciamento.data_publicacao.strftime('%Y-%m-%d'),
                                "SecaoPublicacao": credenciamento.secao_publicacao,
                                "PaginaPublicacao": credenciamento.pagina_publicacao
                            } or None,
                            "Recredenciamento": recredenciamento and {
                                "Tipo": recredenciamento.tipo_ato,
                                "Numero": recredenciamento.numero_ato,
                                "Data": recredenciamento.data_ato.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": recredenciamento.veiculo_publicacao,
                                "DataPublicacao": recredenciamento.data_publicacao.strftime('%Y-%m-%d'),
                                "SecaoPublicacao": recredenciamento.secao_publicacao,
                                "PaginaPublicacao": recredenciamento.pagina_publicacao
                            } or None,
                            "RenovacaoDeRecredenciamento": renovacao_recredenciamento and {
                                "Tipo": renovacao_recredenciamento.tipo_ato,
                                "Numero": renovacao_recredenciamento.numero_ato,
                                "Data": renovacao_recredenciamento.data_ato.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": renovacao_recredenciamento.veiculo_publicacao,
                                "DataPublicacao": renovacao_recredenciamento.data_publicacao.strftime('%Y-%m-%d'),
                                "SecaoPublicacao": renovacao_recredenciamento.secao_publicacao,
                                "PaginaPublicacao": renovacao_recredenciamento.pagina_publicacao
                            } or None,
                            "Mantenedora": {
                                'CNPJ': reitoria.cnpj.replace('.', '').replace('/', '').replace('-', ''),
                                'RazaoSocial': nome_instituicao,
                                'Endereco': {
                                    'NomeMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).nome,
                                    'Número': reitoria.numero,
                                    'CodigoMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).codigo,
                                    'Bairro': reitoria.bairro,
                                    'Logradouro': reitoria.endereco,
                                    'CEP': reitoria.cep.replace('.', '').replace('-', ''),
                                    'UF': reitoria.municipio.uf,
                                }
                            }
                        }
                    },
                    "DadosPrivadosDiplomado": {
                        "Filiacao": [
                            registro.aluno.nome_mae and {
                                "Genitor": {
                                    "Nome": registro.aluno.nome_mae,
                                    "NomeSocial": registro.aluno.nome_mae,
                                    "Sexo": "F"
                                }
                            } or None,
                            registro.aluno.nome_pai and {
                                "Genitor": {
                                    "Nome": registro.aluno.nome_pai,
                                    "NomeSocial": registro.aluno.nome_pai,
                                    "Sexo": "M"
                                }
                            } or None
                        ],
                        "HistoricoEscolar": {
                            "ElementosHistorico": disciplinas,
                            "DataEmissaoHistorico": registro.data_registro.strftime('%Y-%m-%d'),  # TODO
                            "SituacaoAtualDiscente": {
                                "PeriodoLetivo": "2022.1",
                                "Situacao": {
                                    "Formado": {
                                        "DataConclusaoCurso": registro.aluno.dt_conclusao_curso.strftime('%Y-%m-%d'),
                                        "DataColacaoGrau": data_colacao_grau.strftime('%Y-%m-%d'),
                                        "DataExpedicaoDiploma": registro.data_expedicao.strftime('%Y-%m-%d')
                                    }
                                }
                            },
                            "ENADE": dados_enade,
                            "DataProvaEnade": data_prova_endade,
                            "CargaHorariaCurso": {'HoraRelogio': '{:.2f}'.format(float(historico['ch_total']))},
                            "IngressoCurso": {
                                "Data": registro.aluno.data_matricula.strftime('%Y-%m-%d'),
                                "FormaAcesso": 'Vestibular',  # TODO
                                # ['Programas de avaliação seriada ou continuada', 'Convenios', 'Histórico escolar', 'Sisu', 'Enem', 'Vestibular', 'Prova agendada', 'Entrevista', 'Transferência', 'Outros']
                            },
                            "CargaHorariaCursoIntegralizada": {'HoraRelogio': '{:.2f}'.format(float(historico['ch_total_cumprida']))}
                        }
                    },
                    "DocumentacaoComprobatoria": documentos_aluno
                }
            }
        }

        dados_documentacao['data']['RegistroReq']['DadosPrivadosDiplomado']['Filiacao'] = [
            filiacao for filiacao in dados_documentacao['data']['RegistroReq']['DadosPrivadosDiplomado']['Filiacao']
            if filiacao
        ]

        if dados_documentacao['data']['RegistroReq']['DadosPrivadosDiplomado']['HistoricoEscolar']['DataProvaEnade'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosPrivadosDiplomado']['HistoricoEscolar']['DataProvaEnade'])

        if dados_documentacao['data']['RegistroReq']['DadosDiploma']['IesEmissora']['Recredenciamento'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['IesEmissora']['Recredenciamento'])

        if dados_documentacao['data']['RegistroReq']['DadosDiploma']['IesEmissora']['RenovacaoDeRecredenciamento'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['IesEmissora']['RenovacaoDeRecredenciamento'])

        if dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Polo'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Polo'])

        if dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Autorizacao']['VeiculoPublicacao'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Autorizacao']['DataPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Autorizacao']['SecaoPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Autorizacao']['PaginaPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Autorizacao']['VeiculoPublicacao'])

        if dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Reconhecimento']['VeiculoPublicacao'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Reconhecimento']['DataPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Reconhecimento']['SecaoPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Reconhecimento']['PaginaPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['Reconhecimento']['VeiculoPublicacao'])

        if dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento'])
        elif dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento']['VeiculoPublicacao'] is None:
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento']['DataPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento']['SecaoPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento']['PaginaPublicacao'])
            del(dados_documentacao['data']['RegistroReq']['DadosDiploma']['DadosCurso']['RenovacaoReconhecimento']['VeiculoPublicacao'])
        s = json.dumps(dados_documentacao, ensure_ascii=False)
        # print(s)

        schema_file_path = os.path.join(settings.BASE_DIR, 'edu/diploma_digital/schemas/0.16.0/Documentacao.json')
        schema = json.load(open(schema_file_path))
        try:
            jsonschema.validate(instance=dados_documentacao, schema=schema)
            if apenas_validacao:
                return
        except jsonschema.exceptions.ValidationError as e:
            if apenas_validacao:
                print(e.message, e.path)
                return
            detalhe = 'É necessário a correção do seguinte erro: {} ({})'.format(e.message, '->'.join([str(x) for x in e.path]))
            self.registrar_erro_cadastro(assinatura_digital=assinatura_digital, detalhe=detalhe[0:255])
            registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_DADOS
            registro.save()
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/'
        data = dict(
            documentType=4,
            documentData=s,
            documentFile=''
        )
        self.log(url)
        response = MOCK and MockedResponse() or requests.post(url, data=data, headers=self.headers())
        self.log(response.text)
        data = json.loads(response.text)
        if data.get('documentId'):
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe='Envio da documentação acadêmica. ID: {}.'.format(data.get('documentId'))
            )
            assinatura_digital.id_documentacao_academica_digital = data.get('documentId')
            assinatura_digital.save()
            registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DOCUMENTACAO
            registro.save()
        else:
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe='Envio da documentação acadêmica não retornou nenhum ID.'
            )

    def enviar_historico_escolar(self, assinatura_digital, apenas_validacao=False):
        registro = assinatura_digital.registro_emissao_diploma
        reitoria = UnidadeOrganizacional.objects.suap().get(setor__sigla=get_sigla_reitoria())
        nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
        codigo_mec = Configuracao.get_valor_por_chave('comum', 'codigo_mec') or '1082'
        dados_historico = {
            "meta": {
                "clientId": Configuracao.get_valor_por_chave('edu', 'rap_client_id'),
                "yourNumber": f'HST{registro.pk}',
                "dltId": "ethereum",
                "docType": "final_academic_transcript",
                "mimeType": "text/xml",
                "groupId": f'REG{registro.pk}',
                "clientSignature": f'HST{registro.pk}'
            },
            "data": {
                "Versao": "1.04.1",
                "ambiente": "Homologação" if settings.DEBUG else "Produção",
                "infHistoricoEscolar": {
                    "Aluno": {
                        'Nome': registro.aluno.pessoa_fisica.nome,
                        'ID': str(registro.aluno.pk),
                    },
                    "DadosCurso": {
                        "CodigoCursoEMEC": registro.aluno.curso_campus.codigo_emec,
                        'NomeCurso': registro.aluno.curso_campus.descricao_historico,
                    },
                    "IesEmissora": {
                        'Nome': nome_instituicao,
                        'CodigoMEC': codigo_mec,
                        'CNPJ': reitoria.cnpj.replace('.', '').replace('/', '').replace('-', ''),
                    }
                }
            }
        }
        s = json.dumps(dados_historico, ensure_ascii=False)
        # print(s)

        schema_file_path = os.path.join(settings.BASE_DIR, 'edu/diploma_digital/schemas/0.16.0/Historico.json')
        schema = json.load(open(schema_file_path))
        try:
            jsonschema.validate(instance=dados_historico, schema=schema)
            if apenas_validacao:
                return
        except jsonschema.exceptions.ValidationError as e:
            if apenas_validacao:
                print(e.message, e.path)
                return
            detalhe = 'É necessário a correção do seguinte erro: {} ({})'.format(e.message, '->'.join([str(x) for x in e.path]))
            self.registrar_erro_cadastro(assinatura_digital=assinatura_digital, detalhe=detalhe[0:255])
            registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_HISTORICO
            registro.save()
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/'
        data = dict(
            documentType=3,
            documentData=s,
            documentFile=''
        )
        self.log(url)
        response = MOCK and MockedResponse() or requests.post(url, data=data, headers=self.headers())
        self.log(response.text)
        data = json.loads(response.text)
        if data.get('documentId'):
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital,
                detalhe='Envio do histórico escolar. ID: {}.'.format(data.get('documentId'))
            )
            assinatura_digital.id_historico_escolar = data.get('documentId')
            assinatura_digital.save()
            registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_HISTORICO
            registro.save()
        else:
            SincronizacaoAssinaturaDigital.objects.create(
                assinatura_digital=assinatura_digital, detalhe='Envio do histórico não retornou nenhum ID.'
            )

    def enviar_dados_diploma(self, assinatura_digital, apenas_validacao=False):
        registro = assinatura_digital.registro_emissao_diploma
        reitoria = UnidadeOrganizacional.objects.suap().get(setor__sigla=get_sigla_reitoria())

        nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
        codigo_mec = Configuracao.get_valor_por_chave('comum', 'codigo_mec') or '1082'

        credenciamento = Credenciamento.objects.filter(
            tipo=Credenciamento.CREDECIAMENTO
        ).order_by('id').last()
        recredenciamento = Credenciamento.objects.filter(
            tipo=Credenciamento.RECREDECIAMENTO
        ).order_by('id').last()
        renovacao_recredenciamento = Credenciamento.objects.filter(
            tipo=Credenciamento.RENOVACAO_RECREDECIAMENTO
        ).order_by('id').last()

        if registro.aluno.is_qacademico():
            historico = registro.aluno.get_historico_legado(final=True)
            data_colacao_grau = historico['data_colacao_grau']
        else:
            data_colacao_grau = registro.aluno.get_participacao_colacao_grau().colacao_grau.data_colacao

        info = {
            'meta': {
                'clientId': Configuracao.get_valor_por_chave('edu', 'rap_client_id'),
                'yourNumber': f'DIP{registro.pk}',
                'dltId': 'ethereum',
                'docType': 'digital_degree',
                'mimeType': 'text/xml',
                'clientSignature': f'REG{registro.pk}',
                "groupId": f'REG{registro.pk}'
            },
            'data': {
                'Versao': '1.04.1',
                "ambiente": "Homologação" if settings.DEBUG else "Produção",
                'infDiploma': {
                    'DadosDiploma': {
                        'Diplomado': {
                            'Nome': registro.aluno.pessoa_fisica.nome,
                            'ID': str(registro.aluno.pk),
                        },
                        'DadosCurso': {
                            "CodigoCursoEMEC": registro.aluno.curso_campus.codigo_emec,
                            'NomeCurso': registro.aluno.curso_campus.descricao_historico,
                        },
                        'IesEmissora': {
                            'Nome': nome_instituicao,
                            'CodigoMEC': codigo_mec,
                            'CNPJ': reitoria.cnpj.replace('.', '').replace('/', '').replace('-', ''),
                        }
                    },
                    'DadosRegistro': {
                        'LivroRegistro': {
                            'ProcessoDoDiploma': str(registro.processo.numero_processo),
                            'DataColacaoGrau': data_colacao_grau.strftime('%Y-%m-%d'),
                            'DataRegistroDiploma': registro.data_expedicao.strftime('%Y-%m-%d'),
                            'ResponsavelRegistro': {
                                'IDouNumeroMatricula': registro.emissor.username,
                                'CPF': registro.emissor.get_vinculo().pessoa.pessoafisica.cpf.replace('.', '').replace('-', '').replace('*', '0'),
                                'Nome': registro.emissor.get_vinculo().pessoa.nome
                            },
                            'LivroRegistro': str(registro.livro),
                            'NumeroSequenciaDoDiploma': str(registro.numero_registro),
                            'DataExpedicaoDiploma': registro.data_expedicao.strftime('%Y-%m-%d'),
                            'NumeroFolhaDoDiploma': str(registro.folha),
                        },
                        'IesRegistradora': {
                            'CNPJ': reitoria.cnpj.replace('.', '').replace('/', '').replace('-', ''),
                            'Nome': nome_instituicao,
                            'CodigoMEC': codigo_mec,
                            'Credenciamento': credenciamento and {
                                "Tipo": credenciamento.tipo_ato,
                                "Numero": credenciamento.numero_ato,
                                "Data": credenciamento.data_ato.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": credenciamento.veiculo_publicacao,
                                "DataPublicacao": credenciamento.data_publicacao.strftime('%Y-%m-%d'),
                                "SecaoPublicacao": credenciamento.secao_publicacao,
                                "PaginaPublicacao": credenciamento.pagina_publicacao
                            } or None,
                            "Recredenciamento": recredenciamento and {
                                "Tipo": recredenciamento.tipo_ato,
                                "Numero": recredenciamento.numero_ato,
                                "Data": recredenciamento.data_ato.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": recredenciamento.veiculo_publicacao,
                                "DataPublicacao": recredenciamento.data_publicacao.strftime('%Y-%m-%d'),
                                "SecaoPublicacao": recredenciamento.secao_publicacao,
                                "PaginaPublicacao": recredenciamento.pagina_publicacao
                            } or None,
                            "RenovacaoDeRecredenciamento": renovacao_recredenciamento and {
                                "Tipo": renovacao_recredenciamento.tipo_ato,
                                "Numero": renovacao_recredenciamento.numero_ato,
                                "Data": renovacao_recredenciamento.data_ato.strftime('%Y-%m-%d'),
                                "VeiculoPublicacao": renovacao_recredenciamento.veiculo_publicacao,
                                "DataPublicacao": renovacao_recredenciamento.data_publicacao.strftime('%Y-%m-%d'),
                                "SecaoPublicacao": renovacao_recredenciamento.secao_publicacao,
                                "PaginaPublicacao": renovacao_recredenciamento.pagina_publicacao
                            } or None,
                            'Mantenedora': {
                                'CNPJ': reitoria.cnpj.replace('.', '').replace('/', '').replace('-', ''),
                                'RazaoSocial': nome_instituicao,
                                'Endereco': {
                                    'NomeMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).nome,
                                    'Número': reitoria.numero,
                                    'CodigoMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).codigo,
                                    'Bairro': reitoria.bairro,
                                    'Logradouro': reitoria.endereco,
                                    'CEP': reitoria.cep.replace('.', '').replace('-', ''),
                                    'UF': reitoria.municipio.uf,
                                }
                            },
                            'Endereco': {
                                'NomeMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).nome,
                                'Número': '1',
                                'CodigoMunicipio': Cidade.get_cidade_by_municipio(reitoria.municipio).codigo,
                                'Bairro': reitoria.bairro,
                                'Logradouro': reitoria.endereco,
                                'CEP': reitoria.cep.replace('.', '').replace('-', ''),
                                'UF': reitoria.municipio.uf,
                            },
                        },
                    }
                }
            }
        }

        if not info['data']['infDiploma']['DadosRegistro']['IesRegistradora']['RenovacaoDeRecredenciamento']:
            del(info['data']['infDiploma']['DadosRegistro']['IesRegistradora']['RenovacaoDeRecredenciamento'])

        s = json.dumps(info, ensure_ascii=False)
        # print(s)

        schema_file_path = os.path.join(settings.BASE_DIR, 'edu/diploma_digital/schemas/0.16.0/Diploma.json')
        schema = json.load(open(schema_file_path))
        try:
            jsonschema.validate(instance=info, schema=schema)
            if apenas_validacao:
                return
        except jsonschema.exceptions.ValidationError as e:
            if apenas_validacao:
                print(e.message, e.path)
                return
            detalhe = 'É necessário que a TI corrija os seguinte erro: {} ({})'.format(e.message, '->'.join(e.path))
            self.registrar_erro_cadastro(assinatura_digital=assinatura_digital, detalhe=detalhe[0:255])
            registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_CORRECAO_DADOS_DIPLOMA
            registro.save()
            return
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/'
        data = dict(
            documentType=2,
            documentData=s,
            documentFile=''
        )
        self.log(url)
        response = MOCK and MockedResponse() or requests.post(url, data=data, headers=self.headers())
        self.log(response.text)
        data = json.loads(response.text)
        SincronizacaoAssinaturaDigital.objects.create(
            assinatura_digital=assinatura_digital, detalhe='Envio dos dados do diploma. ID: {}.'.format(
                data.get('documentId'))
        )
        assinatura_digital.id_dados_diploma_digital = json.loads(response.text).get('documentId')
        assinatura_digital.save()
        registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DIPLOMA
        registro.save()

    def enviar_representacao_diploma(self, assinatura_digital, apenas_validacao=False):
        registro = assinatura_digital.registro_emissao_diploma
        rap_api_url = Configuracao.get_valor_por_chave('edu', 'rap_api_url')
        url = f'{rap_api_url}/api/documents/'
        if apenas_validacao:
            referencia = '2885269.1681.a27ab1d09d04'
        else:
            response = requests.get(f'{url}{assinatura_digital.id_dados_diploma_digital}/', headers=self.headers()).json()
            referencia = response['securityCode']
        info = {
            'meta': {
                "clientId": Configuracao.get_valor_por_chave('edu', 'rap_client_id'),
                "yourNumber": f'REP{registro.pk}',
                "dltId": "ethereum",
                "docType": "visual_rep_degree",
                "mimeType": "application/pdf",
                "clientSignature": f'REP{registro.pk}',
                "isDocSigned": "false",
                "groupId": f'REG{registro.pk}'
            },
            'data': {
                'ReferenciaDiploma': f'{referencia}'
            }
        }
        schema_file_path = os.path.join(settings.BASE_DIR, 'edu/diploma_digital/schemas/0.16.0/Representacao.json')
        schema = json.load(open(schema_file_path))
        try:
            jsonschema.validate(instance=info, schema=schema)
            if apenas_validacao:
                return
        except jsonschema.exceptions.ValidationError as e:
            if apenas_validacao:
                print(e.message, e.path)
                return
        s = json.dumps(info, ensure_ascii=False)
        # print(s)
        data = dict(
            documentType='5',
            documentData=s
        )

        file_path = MOCK and os.path.join(settings.BASE_DIR, 'edu/diploma_digital/pdf/tmp44ql3sbn.pdf') or cache_file(assinatura_digital.diploma.name)
        with open(file_path, 'rb') as f:
            content = f.read()
        files = {'documentFile': ('Diploma.pdf', content, 'application/pdf')}
        self.log(url)
        response = MOCK and MockedResponse() or requests.post(url, data=data, files=files, headers=self.headers())
        self.log(response.text)
        data = json.loads(response.text)
        SincronizacaoAssinaturaDigital.objects.create(
            assinatura_digital=assinatura_digital, detalhe='Envio da representação visual do diploma. ID: {}.'.format(
                data.get('documentId'))
        )
        assinatura_digital.id_representacao_diploma_digital = json.loads(response.text).get('documentId')
        assinatura_digital.save()
        registro.situacao = RegistroEmissaoDiploma.AGUARDANDO_CONFECCAO_DIPLOMA
        registro.save()
