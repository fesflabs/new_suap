import collections
import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count, F
from django.dispatch import receiver
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from djtools.utils.response import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import get_valid_filename

from cnpq.models import CurriculoVittaeLattes, GrupoPesquisa
from cnpq.views import atualizar_grupos_pesquisa
from comum.forms import AdicionarUsuarioGrupoForm
from comum.models import Arquivo, Configuracao, Vinculo, PrestadorServico, Comentario, TrocarSenha
from comum.utils import get_uo, get_sigla_reitoria, Relatorio
from djtools import layout, documentos
from djtools.html.calendarios import CalendarioPlus
from djtools.html.graficos import ColumnChart
from djtools.html.graficos import PieChart, GroupedColumnChart
from djtools.templatetags.filters import format_
from djtools.utils import documento, rtr, httprr, permission_required, \
    send_notification, send_mail
from edu.models import Aluno, Modalidade
from pesquisa import tasks
from pesquisa.forms import (
    MetaForm,
    EtapaForm,
    DesembolsoForm,
    RecursoForm,
    ItemMemoriaCalculoForm,
    EditalAnexoForm,
    ParticipacaoServidorForm,
    ParticipacaoAlunoForm,
    EditalAnexoAuxiliarForm,
    RegistroGastoForm,
    RegistroExecucaoEtapaForm,
    AlterarCoordenadorForm,
    BuscaProjetoForm,
    RegistroConclusaoProjetoForm,
    ValidacaoConclusaoProjetoForm,
    FotoProjetoForm,
    CriterioAvaliacaoForm,
    AvaliacaoFormFactory,
    ProjetoForm,
    UploadArquivoForm,
    ReprovarExecucaoEtapaForm,
    ReprovarExecucaoGastoForm,
    ProjetoHistoricoDeEnvioForm,
    OfertaProjetoPesquisaForm,
    OfertaProjetoPesquisaFormMultiplo,
    ProjetoAvaliadorForm,
    EquipeEtapaForm,
    IndicarAvaliadoresForm,
    AvaliadoresAreaConhecimentoForm,
    EquipeProjetoForm,
    IndicarAvaliadorForm,
    RecursoPesquisaForm,
    AvaliarRecursoProjetoForm,
    ValidarRecursoProjetoForm,
    EditaisPesquisaForm,
    CancelarProjetoForm,
    AvaliarCancelamentoProjetoForm,
    ValidarCancelamentoProjetoForm,
    EditarProjetoEmExecucaoForm,
    SupervisorForm,
    ProjetosAtrasadosForm,
    CancelarAvaliacaoEtapaForm,
    CancelarAvaliacaoGastoForm,
    IndicadoresForm,
    CampusForm,
    AnoForm,
    MeusProjetosForm,
    GerenciarSupervisorForm,
    SubmeterObraForm,
    MembroObraForm,
    JustificativaPreAvaliacaoForm,
    VerificaAutenticidadeForm,
    AvaliacaoPareceristaObraForm,
    ReenviarObraForm,
    AvaliacaoConselhoEditorialForm,
    AceiteEditoraForm,
    RevisarAutorForm,
    RevisarObraForm,
    EmitirParecerRevisaoObraForm,
    CadastrarDiagramacaoObraForm,
    CadastrarISBNObraForm,
    AvaliacaoDiagramacaoForm,
    FichaCatalograficaForm,
    PublicacaoObraForm,
    AnaliseLiberacaoForm,
    UploadTermosForm,
    IndicarPareceristaForm,
    IndicarConselheiroForm,
    IndicarDiagramadorForm,
    IndicarRevisorForm,
    ChecklistObraForm,
    ConclusaoObraForm,
    TermoAssinadoForm,
    ChecklistObraDiagramadorForm,
    EstatisticasForm,
    RelatorioDimensaoForm,
    AnexosDiversosProjetoForm,
    ListaMensalBolsistaForm,
    DataInativacaoForm,
    SituacaoObraForm,
    EquipamentoLaboratorioForm,
    FotoLaboratorioForm,
    AreaConhecimentoPareceristaForm,
    AlterarAutorForm,
    PareceristasObraForm,
    ComissaoAvaliacaoPorAreaForm,
    ComissaoAvaliacaoForm,
    RegistroConclusaoProjetoObsForm,
    ClonarProjetoForm,
    ClonarEtapaForm,
    UploadProjetoAnexoForm,
    AlterarChefiaForm,
    InativarProjetoForm,
    EditaisForm,
    EmailCoordenadoresForm,
    SolicitarAlteracaoEquipeForm,
    AvaliarAlteracaoEquipeForm,
    RegistrarFrequenciaForm,
    AceiteTermoForm,
    ServicoLaboratorioForm,
    MaterialLaboratorioPesquisaForm,
    SolicitarServicoLaboratorioForm,
    AvaliarSolicitacaoLaboratorioForm,
    MinhasSolicitacoesServicosForm,
    FiltrarLaboratorioPesquisaForm,
    GerarListaFrequenciaForm,
    AutoCadastroPareceristaForm,
    ParticipacaoColaboradorForm, EditarFrequenciaForm, EditarFotoProjetoForm, RelatorioProjetoForm,
    CancelamentoObraForm,
)
from pesquisa.models import (
    Projeto,
    Participacao,
    Meta,
    Desembolso,
    ProjetoAnexo,
    Edital,
    Recurso,
    ItemMemoriaCalculo,
    EditalAnexo,
    EditalAnexoAuxiliar,
    RegistroGasto,
    RegistroExecucaoEtapa,
    RegistroConclusaoProjeto,
    FotoProjeto,
    CriterioAvaliacao,
    Avaliacao,
    HistoricoEquipe,
    Etapa,
    ItemAvaliacao,
    BolsaDisponivel,
    ProjetoHistoricoDeEnvio,
    TipoVinculo,
    AvaliadorIndicado,
    ComissaoEditalPesquisa,
    AvaliadorExterno,
    RecursoProjeto,
    ProjetoCancelado,
    EditalSubmissaoObra,
    Obra,
    MembroObra,
    ParecerObra,
    LaboratorioPesquisa,
    EquipamentoLaboratorioPesquisa,
    FotoLaboratorioPesquisa,
    AreaConhecimentoParecerista,
    SolicitacaoAlteracaoEquipe,
    RegistroFrequencia,
    ServicoLaboratorioPesquisa,
    MaterialLaboratorioPesquisa,
    SolicitacaoServicoLaboratorio,
    MaterialConsumoPesquisa, PessoaExternaObra, RelatorioProjeto,
)
from rh.models import UnidadeOrganizacional, Servidor, AreaConhecimento
from rh.views import rh_servidor_view_tab


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()
    servicos_anonimos.append(dict(categoria='Editora', url="/pesquisa/autocadastro_parecerista/", icone="file-alt", titulo='Seja um Parecerista'))
    return servicos_anonimos


@documentos.emissao_documentos()
def emissao_documentos(request, data):
    participacoes = Participacao.objects.filter(vinculo_pessoa=request.user.get_vinculo(), ativo=True, projeto__aprovado=True)
    for participacao in participacoes:
        data.append(
            ('Pesquisa', 'Projeto de Pesquisa', 'Comprovante de Participação', participacao.projeto, f'/pesquisa/emitir_declaracao_participacao_pdf/{participacao.pk}/')
        )


@layout.alerta()
def index_alertas(request):
    alertas = list()
    relacionamento = request.user.get_relacionamento()
    vinculo = request.user.get_vinculo()
    if request.user.eh_aluno:
        pendencia_aceite_termo = Participacao.objects.filter(
            ativo=True, projeto__edital__termo_compromisso_aluno__isnull=False, vinculo_pessoa=vinculo, termo_aceito_em__isnull=True
        ).exclude(projeto__edital__termo_compromisso_aluno='')
        if pendencia_aceite_termo.exists():
            for registro in pendencia_aceite_termo:
                if registro.projeto.get_status() != Projeto.STATUS_NAO_ENVIADO:
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{registro.projeto.id}/?tab=equipe',
                            titulo=f'Você <strong>precisa aceitar o termo de compromisso</strong> do projeto <strong>{registro.projeto.titulo}</strong>.',
                        )
                    )
    if request.user.eh_prestador:
        pendencia_aceite_termo = Participacao.objects.filter(
            ativo=True, projeto__edital__termo_compromisso_colaborador_externo__isnull=False, vinculo_pessoa=vinculo, termo_aceito_em__isnull=True
        ).exclude(projeto__edital__termo_compromisso_colaborador_externo='')
        if pendencia_aceite_termo.exists():
            for registro in pendencia_aceite_termo:
                if registro.projeto.get_status() != Projeto.STATUS_NAO_ENVIADO:
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{registro.projeto.id}/?tab=equipe',
                            titulo=f'Você <strong>precisa aceitar o termo de compromisso</strong> do projeto <strong>{registro.projeto.titulo}</strong>.',
                        )
                    )
    if request.user.eh_servidor:
        servidor = relacionamento
        uo = servidor.setor.uo
        agora = datetime.datetime.now()
        pendencia_aceite_termo = Participacao.objects.filter(
            ativo=True, responsavel=False, projeto__edital__termo_compromisso_servidor__isnull=False, vinculo_pessoa=vinculo, termo_aceito_em__isnull=True
        ).exclude(projeto__edital__termo_compromisso_servidor='')
        if pendencia_aceite_termo.exists():
            for registro in pendencia_aceite_termo:
                if registro.projeto.get_status() != Projeto.STATUS_NAO_ENVIADO:
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{registro.projeto.id}/?tab=equipe',
                            titulo=f'Você <strong>precisa aceitar o termpo de compromisso</strong> do projeto <strong>{registro.projeto.titulo}</strong>.',
                        )
                    )
        if (
            Projeto.objects.filter(
                pre_aprovado=False,
                aprovado=False,
                responsavel_anuencia=servidor,
                projetocancelado__isnull=True,
                anuencia_registrada_em__isnull=True,
                edital__formato=Edital.FORMATO_COMPLETO
            )
            | Projeto.objects.filter(
                pre_aprovado=False,
                aprovado=False,
                responsavel_anuencia=servidor,
                projetocancelado__isnull=True,
                edital__fim_inscricoes__gt=agora,
                edital__formato=Edital.FORMATO_SIMPLIFICADO
            )
        ).exists():
            alertas.append(dict(url='/pesquisa/projetos_pendentes_anuencia/', titulo='Existem projetos de pesquisa <strong>pendentes da sua anuência.</strong>'))

        projetos_em_execucao = Projeto.objects.filter(
            pre_aprovado=True, aprovado=True, inativado=False, projetocancelado__isnull=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, vinculo_coordenador=vinculo
        )
        if projetos_em_execucao.exists():
            alerta_vence_meta_sete_dias = False
            alerta_vence_meta_hoje = False
            alerta_fim_execucao_quinze_dias = False
            alerta_fim_execucao_hoje = False
            for projeto in projetos_em_execucao:
                if not alerta_vence_meta_sete_dias and projeto.tem_metas_vencendo_em(dias=7):
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{projeto.id}/',
                            titulo='O projeto <strong>{}</strong>, sob sua coordenação, possui meta com prazo de expiração nos próximos <strong>sete dias</strong>.'.format(
                                projeto.titulo
                            ),
                        )
                    )
                    alerta_vence_meta_sete_dias = True

                if not alerta_vence_meta_hoje and projeto.tem_metas_vencendo_em():
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{projeto.id}/',
                            titulo=f'O projeto <strong>{projeto.titulo}</strong>, sob sua coordenação, possui meta com prazo expirando <strong>hoje</strong>.',
                        )
                    )
                    alerta_vence_meta_hoje = True

                if not alerta_fim_execucao_quinze_dias and projeto.tem_data_fim_execucao_em(dias=15):
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{projeto.id}/',
                            titulo='A finalização do projeto {}, sob sua coordenação, está prevista para ocorrer nos próximos <strong>quinze dias</strong>.'.format(
                                projeto.titulo
                            ),
                        )
                    )
                    alerta_fim_execucao_quinze_dias = True

                if not alerta_fim_execucao_hoje and projeto.tem_data_fim_execucao_em():
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{projeto.id}/',
                            titulo=f'A finalização do projeto {projeto.titulo}, sob sua coordenação, está prevista para <strong>hoje</strong>.',
                        )
                    )
                    alerta_fim_execucao_hoje = True

        if servidor.areas_de_conhecimento.all().exists():
            edital_pesquisa_para_avaliar = Edital.objects.em_avaliacao()
            if edital_pesquisa_para_avaliar.exists():
                ids_editais = edital_pesquisa_para_avaliar.values_list('id', flat=True)
                indicacoes = AvaliadorIndicado.objects.filter(vinculo=vinculo, projeto__edital_id__in=ids_editais, rejeitado=False).count()
                avaliacoes = Avaliacao.objects.filter(vinculo=vinculo, projeto__edital_id__in=ids_editais).count()
                if indicacoes > avaliacoes:
                    qtd = indicacoes - avaliacoes
                    alertas.append(dict(url='/pesquisa/avaliacao/', titulo='Há Projeto{plural} de Pesquisa <strong>pendente{plural} de avaliação.</strong>'.format(plural=pluralize(qtd))))

        projeto_simplificado_pendente_conclusao = Projeto.objects.filter(
            data_finalizacao_conclusao__isnull=True, registroconclusaoprojeto__isnull=False, edital__formato=Edital.FORMATO_SIMPLIFICADO, vinculo_supervisor=vinculo
        )

        gerou_alerta_finalizacao = False
        if projeto_simplificado_pendente_conclusao.exists():
            for projeto in projeto_simplificado_pendente_conclusao:
                if not gerou_alerta_finalizacao and not projeto.tem_pendencias():
                    alertas.append(
                        dict(
                            url=f'/pesquisa/projeto/{projeto_simplificado_pendente_conclusao[0].id}/?tab=conclusao',
                            titulo='<strong>Projeto%(plural)s de Pesquisa</strong> simplificado pendente%(plural)s de finalização.'
                            % dict(plural=pluralize(projeto_simplificado_pendente_conclusao)),
                        )
                    )
                    gerou_alerta_finalizacao = True

        if request.user.groups.filter(name='Coordenador de Pesquisa').exists():
            qtd_recursos_projetos = RecursoProjeto.objects.filter(data_avaliacao__isnull=True, projeto__uo_id=uo.pk).count()
            if qtd_recursos_projetos:
                alertas.append(
                    dict(
                        url='/pesquisa/solicitacoes_de_recurso/',
                        titulo='Recurso{plural} de <strong>Projeto{plural} de Pesquisa</strong> não avaliado{plural}.'.format(plural=pluralize(qtd_recursos_projetos)),
                    )
                )

            qtd_projetos_cancelados = ProjetoCancelado.objects.filter(projeto__data_conclusao_planejamento__isnull=False, data_avaliacao__isnull=True, projeto__uo_id=uo.id).count()
            if qtd_projetos_cancelados:
                alertas.append(
                    dict(
                        url='/pesquisa/solicitacoes_de_cancelamento/',
                        titulo='Pedido{plural} de Cancelamento de <strong>Projeto{plural} de Pesquisa</strong> não avaliado{plural}.'.format(
                            plural=pluralize(qtd_projetos_cancelados)
                        ),
                    )
                )

            tem_solicitacoes_alteracoes = False
            solicitacoes_alteracoes = SolicitacaoAlteracaoEquipe.objects.filter(atendida=None, projeto__uo_id=uo.pk)
            if solicitacoes_alteracoes.exists():
                for pedido in solicitacoes_alteracoes:
                    if not tem_solicitacoes_alteracoes and pedido.projeto.pode_editar_inscricao_execucao() and not pedido.projeto.eh_somente_leitura():
                        alertas.append(
                            dict(
                                url=f'/pesquisa/solicitar_alteracao_equipe/{pedido.projeto_id}/',
                                titulo=f'Pedido de <strong>alteração na equipe</strong> do projeto de pesquisa <strong>{pedido.projeto.titulo}</strong> não avaliado.',
                            )
                        )
                        tem_solicitacoes_alteracoes = True

            if Projeto.objects.filter(
                uo=uo, edital__formato=Edital.FORMATO_SIMPLIFICADO, data_conclusao_planejamento__isnull=False, data_pre_avaliacao__isnull=True, vinculo_supervisor__isnull=True
            ).exists():
                projeto = Projeto.objects.filter(
                    uo_id=uo.pk, edital__formato=Edital.FORMATO_SIMPLIFICADO, data_conclusao_planejamento__isnull=False, data_pre_avaliacao__isnull=True, vinculo_supervisor__isnull=True
                )[0]
                alertas.append(dict(url=f'/pesquisa/projeto/{projeto.id}/', titulo='<strong>Projeto de Pesquisa</strong> de edital simplificado pendente de validação.'))

        if request.user.groups.filter(name='Diretor de Pesquisa').exists():
            qtd_recursos_aceitos = RecursoProjeto.objects.filter(data_validacao__isnull=True, parecer_favoravel=True).count()
            if qtd_recursos_aceitos:
                alertas.append(
                    dict(
                        url='/pesquisa/solicitacoes_de_recurso/',
                        titulo='Recurso{plural} de <strong>Projeto{plural} de Pesquisa</strong> pendente{plural} de validação.'.format(plural=pluralize(qtd_recursos_aceitos)),
                    )
                )

            qtd_projetos_cancelados = ProjetoCancelado.objects.filter(projeto__data_conclusao_planejamento__isnull=False, data_validacao__isnull=True, parecer_favoravel=True).count()
            if qtd_projetos_cancelados:
                alertas.append(
                    dict(
                        url='/pesquisa/solicitacoes_de_cancelamento/?edital=&situacao=Pendentes+de+Validação&editaispesquisa_form=Aguarde...',
                        titulo='Pedido{plural} de Cancelamento de <strong>Projeto{plural} de Pesquisa</strong> não validado{plural}.'.format(
                            plural=pluralize(qtd_projetos_cancelados)
                        ),
                    )
                )

            edital_pendente_autorizacao = Edital.objects.filter(autorizado__isnull=True)
            if edital_pendente_autorizacao.exists():
                alertas.append(
                    dict(url='/admin/pesquisa/edital/', titulo=f'O Edital <strong>{edital_pendente_autorizacao[0].titulo}</strong> está pendente de autorização.')
                )
        if request.user.groups.filter(name='Integrante da Editora').exists():
            obras_pendentes_indicar_parecer = ParecerObra.objects.filter(recusou_indicacao=True)
            if obras_pendentes_indicar_parecer.exists():
                alertas.append(
                    dict(
                        url=f'/pesquisa/obra/{obras_pendentes_indicar_parecer[0].obra.id}/?tab=analise_parecerista',
                        titulo='Um parecerista <strong>rejeitou a indicação</strong> e precisa ser substituído.',
                    )
                )

    if request.user.eh_servidor or request.user.eh_prestador:
        obras_pendentes_envio_correcao = Obra.objects.filter(submetido_por_vinculo=vinculo, situacao=Obra.ACEITA, situacao_conselho_editorial=Obra.FAVORAVEL_COM_RESSALVAS)
        if obras_pendentes_envio_correcao.exists():
            obras_pendentes_envio_correcao = obras_pendentes_envio_correcao[0]
            alertas.append(dict(url=f'/pesquisa/obra/{obras_pendentes_envio_correcao.id}/?tab=validacao_conselho', titulo='Você precisa enviar sua obra corrigida.'))

        obras_pendentes_envio_correcao = Obra.objects.filter(
            submetido_por_vinculo=vinculo, situacao=Obra.ASSINADA, arquivo_obra_revisada__isnull=False, revisada_pelo_autor__isnull=True
        )
        if obras_pendentes_envio_correcao.exists():
            obras_pendentes_envio_correcao = obras_pendentes_envio_correcao[0]
            alertas.append(dict(url=f'/pesquisa/obra/{obras_pendentes_envio_correcao.id}/?tab=revisao_textual', titulo='Você precisa enviar sua obra revisada.'))

        obras_pendentes_avaliacao_diagramacao = Obra.objects.filter(submetido_por_vinculo=vinculo, situacao=Obra.DIAGRAMADA, diagramacao_avaliada_em__isnull=True)
        if obras_pendentes_avaliacao_diagramacao.exists():
            obras_pendentes_avaliacao_diagramacao = obras_pendentes_avaliacao_diagramacao[0]
            alertas.append(
                dict(url=f'/pesquisa/obra/{obras_pendentes_avaliacao_diagramacao.id}/?tab=diagramacao', titulo='Você precisa avaliar a diagramação da sua obra.')
            )

        obras_pendentes_termos = Obra.objects.filter(submetido_por_vinculo=vinculo, situacao=Obra.VALIDADA, termo_autorizacao_publicacao='')
        if obras_pendentes_termos.exists():
            obras_pendentes_termos = obras_pendentes_termos[0]
            alertas.append(dict(url=f'/pesquisa/obra/{obras_pendentes_termos.id}/?tab=termos', titulo='Você precisa enviar os termos assinados da sua obra.'))

    return alertas


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.groups.filter(name__in=['Servidor', 'Aposentado']).exists():
        hoje = datetime.datetime.now()
        qtd_editais_pesquisa_sem_continuo = (
            Edital.objects.filter(inicio_inscricoes__lte=hoje, fim_inscricoes__gte=hoje).exclude(tipo_edital=Edital.PESQUISA_INOVACAO_CONTINUO).count()
        )
        if qtd_editais_pesquisa_sem_continuo:
            inscricoes.append(dict(url='/pesquisa/editais_abertos/', titulo='Você pode submeter um <strong>Projeto de Pesquisa</strong>.'))

    return inscricoes


@layout.quadro('Pesquisa', icone='globe')
def index_quadros(quadro, request):
    vinculo = request.user.get_vinculo()
    if request.user.eh_aluno or request.user.eh_prestador:
        projetos_do_usuario = Projeto.objects.filter(participacao__vinculo_pessoa=vinculo, aprovado=True)
        if projetos_do_usuario.exists():
            for projeto in projetos_do_usuario:
                quadro.add_item(layout.ItemGrupo(titulo=projeto.titulo, grupo='Meus Projetos', url=f'/pesquisa/projeto/{projeto.pk:d}/'))

    elif request.user.groups.filter(name__in=['Coordenador de Pesquisa', 'Supervisor de Projetos de Pesquisa']).exists():
        relacionamento = request.user.get_relacionamento()
        uo = relacionamento.setor.uo
        if request.user.has_perm('pesquisa.pode_pre_avaliar_projeto'):
            projetos_para_pre_avaliar = Projeto.objects.filter(
                pre_aprovado=False,
                aprovado=False,
                data_conclusao_planejamento__isnull=False,
                projetocancelado__isnull=True,
                uo=uo,
                edital__in=Edital.objects.em_pre_avaliacao().values_list('id', flat=True),
            )

            if projetos_para_pre_avaliar.exists():
                valor = projetos_para_pre_avaliar.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Projeto{pluralize(valor)}',
                        subtitulo=f'Pendente{pluralize(valor)} de pré-avaliação',
                        qtd=valor,
                        url='/pesquisa/pre_avaliacao/pesquisa/',
                    )
                )

        projetos_em_execucao = Projeto.objects.filter(pre_aprovado=True, aprovado=True, projetocancelado__isnull=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, uo=uo)
        if not request.user.groups.filter(name='Coordenador de Pesquisa').exists():
            projetos_em_execucao = projetos_em_execucao.filter(vinculo_supervisor=vinculo)
        if projetos_em_execucao.exists():
            contador_meta_expira_7_dias = list()
            contador_meta_expira_hoje = list()
            contador_projeto_finaliza_15_dias = list()
            contador_projeto_finaliza_hoje = list()
            for projeto in projetos_em_execucao:
                if projeto.tem_metas_vencendo_em(dias=7):
                    contador_meta_expira_7_dias.append(projeto.id)
                if projeto.tem_metas_vencendo_em():
                    contador_meta_expira_hoje.append(projeto.id)
                if projeto.tem_data_fim_execucao_em(dias=15):
                    contador_projeto_finaliza_15_dias.append(projeto.id)
                if projeto.tem_data_fim_execucao_em():
                    contador_projeto_finaliza_hoje.append(projeto.id)

            if contador_meta_expira_7_dias:
                valor = len(contador_meta_expira_7_dias)
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Projeto{pluralize(valor)}',
                        subtitulo=f'Com Meta{pluralize(valor)} expirando nos próximos 7 dias',
                        qtd=valor,
                        url=f'/pesquisa/projetos_em_execucao/?ids={contador_meta_expira_7_dias}',
                    )
                )
            if contador_meta_expira_hoje:
                valor = len(contador_meta_expira_hoje)
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Projeto{pluralize(valor)}',
                        subtitulo=f'Com Meta{pluralize(valor)} expirando hoje',
                        qtd=valor,
                        url=f'/pesquisa/projetos_em_execucao/?ids={contador_meta_expira_hoje}',
                    )
                )
            if contador_projeto_finaliza_15_dias:
                valor = len(contador_projeto_finaliza_15_dias)
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Projeto{pluralize(valor)}',
                        subtitulo='Com data de finalização expirando nos próximos 15 dias',
                        qtd=valor,
                        url=f'/pesquisa/projetos_em_execucao/?ids={contador_projeto_finaliza_15_dias}',
                    )
                )
            if contador_projeto_finaliza_hoje:
                valor = len(contador_projeto_finaliza_hoje)
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Projeto{pluralize(valor)}',
                        subtitulo='Com data de finalização prevista para hoje',
                        qtd=valor,
                        url=f'/pesquisa/projetos_em_execucao/?ids={contador_projeto_finaliza_hoje}',
                    )
                )

    return quadro


@layout.quadro('Submissão de Obras', icone='globe', pode_esconder=True)
def index_quadros_obras(quadro, request):
    if request.user.has_perm('pesquisa.add_editalsubmissaoobra'):
        nova_obra_submetida = Obra.objects.filter(situacao=Obra.SUBMETIDA)
        if nova_obra_submetida.exists():
            qtd = nova_obra_submetida.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(nova_obra_submetida.count())}',
                    subtitulo=f'Submetida{pluralize(nova_obra_submetida.count())}',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_submetidas',
                )
            )
        nova_obra_submetida = Obra.objects.filter(situacao=Obra.AUTENTICA, aceita_editora_realizada_por_vinculo__isnull=True)
        if nova_obra_submetida.exists():
            qtd = nova_obra_submetida.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} de aceite pela editora',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_autenticas',
                )
            )
        obras_pendentes_termos = Obra.objects.filter(situacao=Obra.VALIDADA, termos_assinados_realizado_por_vinculo__isnull=True, revisao_realizada_em__isnull=True).exclude(
            termo_autorizacao_publicacao=''
        )

        if obras_pendentes_termos.exists():
            qtd = obras_pendentes_termos.count()
            quadro.add_item(layout.ItemContador(titulo=f'Obra{pluralize(qtd)}', subtitulo='Com termos assinados', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_validadas'))

        obras_pendentes_conselheiro = Obra.objects.filter(situacao=Obra.ACEITA, julgamento_conselho_realizado_por_vinculo__isnull=True)
        if obras_pendentes_conselheiro.exists():
            qtd = obras_pendentes_conselheiro.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} de indicação de conselheiro',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_aceitas',
                )
            )
        nova_obra_submetida = Obra.objects.filter(situacao=Obra.REVISADA, diagramacao_realizada_por_vinculo__isnull=True)
        if nova_obra_submetida.exists():
            qtd = nova_obra_submetida.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} de indicação de diagramador',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_revisadas',
                )
            )
        nova_obra_submetida = Obra.objects.filter(situacao=Obra.CORRIGIDA, isbn__isnull=True)
        if nova_obra_submetida.exists():
            qtd = nova_obra_submetida.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} de cadastro do ISBN',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_corrigidas',
                )
            )

        nova_obra_submetida = Obra.objects.filter(situacao=Obra.LIBERADA, situacao_publicacao=Obra.NAO_INICIADA)
        if nova_obra_submetida.exists():
            qtd = nova_obra_submetida.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} de publicação', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_liberadas'
                )
            )

        nova_obra_submetida = Obra.objects.filter(situacao=Obra.LIBERADA).exclude(situacao_publicacao=Obra.NAO_INICIADA)
        if nova_obra_submetida.exists():
            qtd = nova_obra_submetida.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} de conclusão', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_liberadas'
                )
            )

    vinculo = request.user.get_vinculo()
    if request.user.has_perm('pesquisa.pode_avaliar_obra'):
        obras_pendentes_parecer = ParecerObra.objects.filter(parecer_realizado_por_vinculo=vinculo, situacao=ParecerObra.EM_ANALISE, recusou_indicacao=False)
        if obras_pendentes_parecer.exists():
            qtd = obras_pendentes_parecer.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} do seu parecer', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_aceitas'
                )
            )

    if request.user.has_perm('pesquisa.pode_validar_obra'):
        parecer = ParecerObra.objects.filter(nota__isnull=False, obra__situacao=Obra.ACEITA)
        obras_pendentes_parecer = Obra.objects.filter(
            id__in=parecer.values_list('obra', flat=True), julgamento_conselho_realizado_por_vinculo=vinculo, julgamento_conselho_realizado_em__isnull=True
        )
        if obras_pendentes_parecer.exists():
            qtd = obras_pendentes_parecer.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} da sua validação', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_aceitas'
                )
            )

        obras_pendentes_indicacao_parecerista = Obra.objects.filter(
            situacao=Obra.ACEITA, julgamento_conselho_realizado_por_vinculo=vinculo, julgamento_conselho_realizado_em__isnull=True
        ).exclude(id__in=ParecerObra.objects.all().values_list('obra', flat=True))
        if obras_pendentes_indicacao_parecerista.exists():
            qtd = obras_pendentes_indicacao_parecerista.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} de indicação de parecerista',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_aceitas',
                )
            )

        obras_pendentes_parecer = Obra.objects.filter(situacao=Obra.CATALOGADA, julgamento_conselho_realizado_por_vinculo=vinculo)
        if obras_pendentes_parecer.exists():
            qtd = obras_pendentes_parecer.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} da sua análise de liberação',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_catalogadas',
                )
            )

    if request.user.has_perm('pesquisa.pode_diagramar_obra'):
        obras_pendentes_diagramacao = Obra.objects.filter(situacao=Obra.REVISADA, diagramacao_realizada_por_vinculo=vinculo)
        if obras_pendentes_diagramacao.exists():
            qtd = obras_pendentes_diagramacao.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} de diagramação', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_revisadas'
                )
            )

        obras_pendentes_diagramacao_final = Obra.objects.filter(situacao=Obra.DIAGRAMADA, diagramacao_realizada_por_vinculo=vinculo, diagramacao_avaliada_em__isnull=False)
        if obras_pendentes_diagramacao_final.exists():
            qtd = obras_pendentes_diagramacao_final.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} da versão final da diagramação',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_diagramadas',
                )
            )

    if request.user.has_perm('pesquisa.pode_gerar_ficha_catalografica'):
        obras_pendentes_ficha = Obra.objects.filter(situacao=Obra.REGISTRADA_ISBN)
        if obras_pendentes_ficha.exists():
            qtd = obras_pendentes_ficha.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} de ficha catalográfica', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_isbn'
                )
            )

    if request.user.has_perm('pesquisa.pode_revisar_obra'):
        obras_pendentes_revisao = Obra.objects.filter(revisao_realizada_por_vinculo=vinculo, revisao_realizada_em__isnull=True)
        if obras_pendentes_revisao.exists():
            qtd = obras_pendentes_revisao.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)} da sua revisão', qtd=qtd, url='/admin/pesquisa/obra/?tab=tab_validadas'
                )
            )

        obras_pendentes_parecer = Obra.objects.filter(
            revisao_realizada_por_vinculo=vinculo, revisao_realizada_em__isnull=False, correcoes_enviadas_em__isnull=False, parecer_revisor__isnull=True
        )
        if obras_pendentes_parecer.exists():
            qtd = obras_pendentes_parecer.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Obra{pluralize(qtd)}',
                    subtitulo=f'Pendente{pluralize(qtd)} do parecer final da sua revisão',
                    qtd=qtd,
                    url='/admin/pesquisa/obra/?tab=tab_validadas',
                )
            )

    return quadro


@rtr()
@permission_required('pesquisa.view_edital')
def edital(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    tem_formato_completo = edital.tem_formato_completo()

    if edital.tipo_edital == edital.PESQUISA:
        title = f'{edital.titulo} - Edital de Pesquisa'
    elif edital.tipo_edital == edital.INOVACAO:
        title = f'{edital.titulo} - Edital de Inovação'
    elif edital.tipo_edital == edital.PESQUISA_INOVACAO_CONTINUO:
        title = f'{edital.titulo} - Edital de Pesquisa e Inovação - Fluxo Contínuo'

    if edital.forma_selecao == Edital.GERAL:
        titulo_box_plano_oferta_por_campus = 'Campi Participantes'
    else:
        titulo_box_plano_oferta_por_campus = 'Plano de Oferta por Campus'

    FormClass = edital.get_form()
    form = FormClass(request.POST or None)
    if form.is_valid() and not request.user.has_perm('pesquisa.pode_ver_config_edital'):
        form.save()
        return httprr('.', 'Critérios adicionados com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def meus_projetos(request):
    title = 'Meus Projetos'
    vinculo = request.user.get_vinculo()
    participacoes = Participacao.objects.filter(vinculo_pessoa=vinculo, ativo=True).order_by('-projeto__id', 'projeto__vinculo_coordenador')
    ano = request.GET.get('ano')
    form = MeusProjetosForm(request.GET or None, ano=ano)
    if form.is_valid():
        edital = form.cleaned_data.get('edital')
        situacao = form.cleaned_data.get('situacao')
        ano = form.cleaned_data.get('ano')
        if ano:
            participacoes = participacoes.filter(projeto__edital__inicio_inscricoes__year=ano)
        if edital:
            participacoes = participacoes.filter(projeto__edital=edital)

        if situacao:
            hoje = datetime.datetime.now()
            projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
            if situacao == MeusProjetosForm.PROJETOS_EM_EDICAO:
                participacoes = participacoes.filter(projeto__data_conclusao_planejamento__isnull=True, projeto__edital__fim_inscricoes__gte=hoje)
            elif situacao == MeusProjetosForm.PROJETOS_ENVIADOS:
                participacoes = participacoes.filter(
                    Q(projeto__data_conclusao_planejamento__isnull=False) | Q(projeto__data_conclusao_planejamento__isnull=True, projeto__data_pre_avaliacao__isnull=False)
                )
            elif situacao == MeusProjetosForm.PROJETOS_PRE_SELECIONADOS:
                participacoes = participacoes.filter(projeto__pre_aprovado=True, projeto__data_pre_avaliacao__isnull=False)
            elif situacao == MeusProjetosForm.PROJETOS_EM_EXECUCAO:
                participacoes = participacoes.filter(projeto__aprovado=True, projeto__registroconclusaoprojeto__dt_avaliacao__isnull=True).distinct()
            elif situacao == MeusProjetosForm.PROJETOS_ENCERRADOS:
                participacoes = (
                    participacoes.filter(projeto__aprovado=True, projeto__registroconclusaoprojeto__dt_avaliacao__isnull=False).exclude(projeto__in=projetos_cancelados).distinct()
                )
            elif situacao == MeusProjetosForm.PROJETOS_CANCELADOS:
                participacoes = participacoes.filter(projeto__in=projetos_cancelados).distinct()

    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def pre_avaliacao(request, tipo_edital):
    selecionar_avaliadores = None
    title = 'Editais em Avaliação'
    if tipo_edital == 'selecionar_avaliadores':
        selecionar_avaliadores = True
        hoje = datetime.datetime.now()
        editais = Edital.objects.filter(divulgacao_selecao__gt=hoje) | Edital.objects.filter(tipo_edital=Edital.PESQUISA_INOVACAO_CONTINUO, fim_inscricoes__gt=hoje)
        if not request.user.groups.filter(name='Diretor de Pesquisa'):
            if request.user.groups.filter(name='Coordenador de Pesquisa') and not request.user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Pesquisa'):
                editais = editais.exclude(forma_selecao=Edital.GERAL)
            elif request.user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Pesquisa') and not request.user.groups.filter(name='Coordenador de Pesquisa'):
                editais = editais.exclude(forma_selecao=Edital.CAMPUS)
    else:
        editais = Edital.objects.em_pre_avaliacao()
        if not request.user.groups.filter(name='Diretor de Pesquisa'):
            if request.user.groups.filter(name='Coordenador de Pesquisa') and not request.user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Pesquisa'):
                editais = editais.exclude(forma_selecao=Edital.GERAL)
            elif request.user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Pesquisa') and not request.user.groups.filter(name='Coordenador de Pesquisa'):
                editais = editais.exclude(forma_selecao=Edital.CAMPUS)
    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_projeto')
def avaliacao(request):
    title = 'Editais em Avaliação'
    editais_com_indicacao = AvaliadorIndicado.objects.filter(vinculo=request.user.get_vinculo())
    editais = Edital.objects.em_selecao().filter(pk__in=editais_com_indicacao.values_list('projeto__edital', flat=True))
    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_projeto')
def projetos_especial_pre_aprovados(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    if not edital.is_periodo_selecao():
        raise PermissionDenied()
    title = f'Seleção de Projetos - {edital.titulo}'
    vinculo = request.user.get_vinculo()
    projetos = Projeto.objects.filter(avaliadorindicado__vinculo=vinculo, edital=edital, pre_aprovado=True).order_by('-pontuacao_total', '-pontuacao_curriculo')
    lista_projetos = list()
    for projeto in projetos:
        if AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=vinculo, rejeitado=True).exists():
            automaticamente = AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=vinculo, rejeitado=True)[0].rejeitado_automaticamente
            lista_projetos.append([projeto, True, automaticamente])
        else:
            lista_projetos.append([projeto, False, False])
    if request.user.eh_servidor:
        servidor_apto = edital.servidor_pode_avaliar_projeto(request.user)
    else:
        servidor_apto = True
    is_gerente_sistemico = request.user.groups.filter(name='Diretor de Pesquisa')

    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def projetos_nao_avaliados(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)

    if not edital.is_periodo_pre_selecao():
        raise PermissionDenied
    if (
        edital.forma_selecao == Edital.GERAL
        and request.user.groups.filter(name='Coordenador de Pesquisa')
        and not request.user.groups.filter(name__in=['Pré-Avaliador Sistêmico de Projetos de Pesquisa', 'Diretor de Pesquisa'])
    ):
        raise PermissionDenied
    projetos = Projeto.objects.filter(edital=edital, data_conclusao_planejamento__isnull=False).order_by('titulo')

    uos = edital.get_uos_edital_pesquisa()
    if (
        not request.user.groups.filter(name__in=['Diretor de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa'])
        and not get_uo(request.user).setor.sigla == get_sigla_reitoria()
    ):
        uo = get_uo(request.user)
        projetos = projetos.filter(uo=uo)
        uos = [uo]
    for uo in uos:
        tem_oferta = edital.bolsadisponivel_set.filter(uo=uo).count()
        if tem_oferta:
            oferta = edital.bolsadisponivel_set.get(uo=uo)
            uo.qtd_enviados = edital.num_total_projetos_enviados(uo)
            uo.qtd_pre_aprovados = edital.num_total_projetos_pre_aprovados(uo)
            uo.qtd_nao_pre_aprovados = uo.qtd_enviados - uo.qtd_pre_aprovados
            uo.num_maximo_ic = oferta.num_maximo_ic
            uo.num_maximo_pesquisador = oferta.num_maximo_pesquisador

    if edital.forma_selecao == Edital.GERAL:
        enviados = edital.num_total_projetos_enviados()
        pre_aprovados = edital.num_total_projetos_pre_aprovados()
        nao_pre_aprovados = enviados - pre_aprovados
        num_maximo_ic = edital.qtd_bolsa_alunos
        num_maximo_pesquisador = edital.qtd_bolsa_servidores

    form = CampusForm(request.POST or None)
    if form.is_valid():
        if form.cleaned_data.get('uo'):
            uo_selecionado = form.cleaned_data.get('uo')
            projetos = projetos.filter(uo=uo_selecionado)

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editais_abertos(request):
    title = 'Editais de Pesquisa e de Inovação com Inscrições Abertas'
    tem_lattes = True
    pode_clonar_projeto = False
    editais = Edital.disponiveis_para_inscricoes()
    instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    vinculo = request.user.get_vinculo()
    if request.user.groups.filter(name='Diretor de Pesquisa'):
        gerente_especial_sistemico = True
    if not CurriculoVittaeLattes.objects.filter(vinculo=vinculo).exists():
        tem_lattes = False
    if tem_lattes:
        pode_clonar_projeto = Projeto.objects.filter(vinculo_coordenador=vinculo).exists()
    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto, pesquisa.pode_acessar_lista_projetos')
def projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_movimentacao = ProjetoHistoricoDeEnvio.objects.filter(projeto=projeto).exists()
    title = f'Projeto de {projeto.edital.get_tipo_edital_display()}'
    participantes = projeto.participacao_set.all()
    periodo = projeto.get_periodo()
    status = projeto.get_status()
    status_pre_selecao = projeto.get_pre_selecionado()
    status_selecao = projeto.get_selecionado()
    tem_formato_completo = projeto.edital.tem_formato_completo()
    vinculo = request.user.get_vinculo()
    is_gerente_sistemico = request.user.has_perm('pesquisa.tem_acesso_sistemico')
    is_coordenador = projeto.is_responsavel(request.user)
    is_avaliador = request.user.groups.filter(name='Avaliador Sistêmico de Projetos de Pesquisa')
    is_pre_avaliador = request.user.groups.filter(name__in=['Coordenador de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa'])
    pode_inativar_projeto = (request.user.has_perm('pesquisa.pode_gerenciar_edital') and (get_uo(request.user) == projeto.uo)) or projeto.is_gerente_sistemico(request.user)
    eh_somente_leitura = projeto.eh_somente_leitura()
    eh_participante = projeto.eh_participante(request.user)
    tem_atividades_cadastradas = projeto.tem_atividades_cadastradas()
    pode_editar_equipe_propi = projeto.pode_editar_equipe_propi(request.user)
    is_coordenador_pesquisa = request.user.groups.filter(name__in=['Coordenador de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa', 'Diretor de Pesquisa'])

    eh_supervisor = is_coordenador_pesquisa and get_uo(request.user) == projeto.uo
    is_coordenador_edu = request.user.has_perm('pesquisa.pode_acessar_lista_projetos')
    is_assessor_pesquisa = request.user.groups.filter(name='Assessor de Pesquisa')
    pode_acessar_certificado = status == (Projeto.STATUS_EM_EXECUCAO or Projeto.STATUS_CONCLUIDO)

    divulgado = Projeto.objects.filter(id=projeto_id, edital__divulgacao_selecao__lte=datetime.datetime.now())
    edital_projeto = Edital.objects.get(pk=projeto.edital.id)
    avaliador_pode_imprimir = is_avaliador and edital_projeto.is_periodo_selecao()
    mesmo_campus = projeto.uo == get_uo(request.user)
    tem_cancelamento = ProjetoCancelado.objects.filter(projeto=projeto)
    if not (
        is_coordenador_edu
        or is_coordenador_pesquisa.exists()
        or is_coordenador
        or is_gerente_sistemico
        or is_avaliador
        or is_assessor_pesquisa
        or (is_pre_avaliador and mesmo_campus)
        or eh_participante
        or projeto.vinculo_supervisor == vinculo
    ):
        raise PermissionDenied()

    if is_coordenador_edu and not request.user.has_perm('pesquisa.pode_visualizar_projeto') and get_uo(request.user) != projeto.uo:
        raise PermissionDenied()

    edicao_inscricao = False
    if is_gerente_sistemico or (is_coordenador and status == Projeto.STATUS_EM_INSCRICAO):
        edicao_inscricao = True

    edicao_inscricao_execucao = False
    if is_gerente_sistemico or (is_coordenador and (status == Projeto.STATUS_EM_INSCRICAO or status == Projeto.STATUS_EM_EXECUCAO)):
        edicao_inscricao_execucao = True

    if eh_participante and not is_coordenador:
        pode_editar = False
        edicao_inscricao = False
        edicao_inscricao_execucao = False

    resumo_recursos = []
    recursos = projeto.edital.recurso_set.filter()
    geral_planejado = Decimal(0)
    geral_executado = Decimal(0)
    for recurso in recursos:
        despesa = recurso.despesa
        valor_reservado = recurso.valor
        soma_distribuido = Decimal(0)
        soma_executado = Decimal(0)
        for item in projeto.itemmemoriacalculo_set.filter(despesa=despesa):
            soma_distribuido += item.get_subtotal()
            soma_executado += item.get_total_executado()
        valor_distribuido = soma_distribuido
        valor_executado = soma_executado
        valor_planejado = sum(projeto.desembolso_set.filter(item__despesa=despesa).values_list('valor', flat=True))
        valor_disponivel_orcamento = valor_distribuido - valor_planejado
        valor_disponivel_execucao = valor_planejado - valor_executado

        geral_planejado = geral_planejado + valor_distribuido
        geral_executado = geral_executado + valor_executado

        if valor_disponivel_orcamento < 0:
            cor_valor_disponivel_orcamento = 'False'
        else:
            cor_valor_disponivel_orcamento = 'True'
        if valor_distribuido > valor_reservado:
            cor_valor_distribuido = 'false'
        else:
            cor_valor_distribuido = 'true'
        resumo_recursos.append(
            dict(
                valor_reservado=valor_reservado,
                despesa=despesa,
                valor_distribuido=valor_distribuido,
                valor_planejado=valor_planejado,
                valor_disponivel_orcamento=valor_disponivel_orcamento,
                valor_executado=valor_executado,
                valor_disponivel_execucao=valor_disponivel_execucao,
                cor_valor_distribuido=cor_valor_distribuido,
                cor_valor_disponivel_orcamento=cor_valor_disponivel_orcamento,
            )
        )

    devolucao = None
    if (
        ProjetoHistoricoDeEnvio.objects.filter(projeto=projeto).exists()
        and status == projeto.STATUS_EM_INSCRICAO
        and ProjetoHistoricoDeEnvio.objects.filter(projeto=projeto).latest('id').situacao == ProjetoHistoricoDeEnvio.DEVOLVIDO
    ):
        devolucao = ProjetoHistoricoDeEnvio.objects.filter(projeto=projeto).latest('id')

    parametros_pontuacao = projeto.parametroprojeto_set.filter(parametro_edital__valor_parametro__gt=0.0).order_by('parametro_edital__parametro__codigo')

    registro_conclusao = projeto.get_registro_conclusao()
    tem_pendencias = projeto.tem_pendencias() or not registro_conclusao or (registro_conclusao and not registro_conclusao.dt_avaliacao)
    pode_avaliar_projeto = edital_projeto.is_periodo_selecao() and projeto.pendente_avaliacao() and AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=vinculo, rejeitado=False).exists()
    edital_exige_anuencia = edital_projeto.exige_anuencia
    anuencia_em = projeto.anuencia_registrada_em
    pode_alterar_responsavel_anuencia = projeto.edital.get_data_limite_anuencia() > datetime.datetime.now()
    registros_frequencia = RegistroFrequencia.objects.filter(projeto=projeto).order_by('-data', 'cadastrada_por')
    form_frequencias = GerarListaFrequenciaForm(request.POST or None, projeto=projeto)
    if form_frequencias.is_valid():
        data_inicio = form_frequencias.cleaned_data.get('data_inicio')
        data_termino = form_frequencias.cleaned_data.get('data_termino')
        participante = form_frequencias.cleaned_data.get('participante')
        if data_inicio:
            registros_frequencia = registros_frequencia.filter(data__gte=data_inicio)
        if data_termino:
            registros_frequencia = registros_frequencia.filter(data__lte=data_termino)
        if participante:
            registros_frequencia = registros_frequencia.filter(cadastrada_por=participante)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def imprimir_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    is_avaliador = AvaliadorIndicado.objects.filter(vinculo=request.user.get_vinculo(), projeto=projeto).exists()
    cronograma = projeto.get_cronograma_desembolso_como_lista()
    plano_aplicacao = projeto.get_plano_aplicacao_como_dict()
    edital_projeto = Edital.objects.get(pk=projeto.edital.id)
    tem_formato_completo = edital_projeto.tem_formato_completo()

    total_geral = projeto.itemmemoriacalculo_set.extra({'total': 'SUM(valor_unitario*qtd)'}).values('total')[0]['total']
    metas = projeto.get_metas()
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def relatorio_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    cronograma = projeto.get_cronograma_desembolso_como_lista()
    valor_financiamento_projeto = (
        RegistroGasto.objects.filter(item__projeto__id=projeto_id)
        .extra(select={'total': 'SUM(pesquisa_registrogasto.qtd*pesquisa_registrogasto.valor_unitario)'})
        .values('total')[0]['total']
    )
    tem_formato_completo = projeto.edital.tem_formato_completo()
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def memoria_calculo(request, projeto_id):
    title = 'Memória de Cálculo'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    url = f'/pesquisa/projeto/{projeto.id:d}/?tab=plano_aplicacao'
    tem_permissao(request, projeto)
    editavel = not projeto.data_pre_avaliacao and request.user.groups.filter(name__in=['Servidor', 'Aposentado']).exists()
    if editavel:
        editavel = Participacao.objects.filter(vinculo_pessoa=request.user.get_vinculo(), responsavel=True).count() > 0
    if request.user.groups.filter(name='Diretor de Pesquisa'):
        editavel = True

    is_operador = True

    item = None
    is_coordenador = projeto.is_coordenador(request.user)
    is_avaliador = projeto.is_avaliador(request.user)

    if 'edit_id' in request.GET:
        item = get_object_or_404(ItemMemoriaCalculo, pk=request.GET['edit_id'])
        if not (item.pode_editar_e_remover_memoria_calculo() and not projeto.eh_somente_leitura()):
            raise PermissionDenied

    if 'del_id' in request.GET:
        item = get_object_or_404(ItemMemoriaCalculo, pk=request.GET['del_id'])
        if not (item.pode_editar_e_remover_memoria_calculo() and not projeto.eh_somente_leitura()):
            raise PermissionDenied
        item.delete()
        item = None
        return httprr(url, 'Item removido com sucesso.')

    if request.method == 'POST':
        form = ItemMemoriaCalculoForm(data=request.POST, instance=item)
        if form.is_valid():
            o = form.save(False)
            o.projeto = projeto
            o.save()
            if item:
                return httprr(url, 'Item editado com sucesso.')
            else:
                return httprr('..', 'Item adicionado com sucesso.')
    else:
        form = ItemMemoriaCalculoForm(instance=item)
    form.fields['despesa'].queryset = projeto.edital.get_elementos_despesa()

    resumo_recursos = []
    recursos = projeto.edital.recurso_set.filter()
    for recurso in recursos:
        despesa = recurso.despesa
        valor_reservado = recurso.valor
        soma_distribuido = Decimal(0)
        soma_executado = Decimal(0)
        for item in projeto.itemmemoriacalculo_set.filter(despesa=despesa):
            soma_distribuido += item.get_subtotal()
            soma_executado += item.get_total_executado()
        valor_distribuido = soma_distribuido
        valor_disponivel_orcamento = valor_reservado - valor_distribuido
        valor_executado = soma_executado
        valor_disponivel_execucao = valor_distribuido - valor_executado
        if valor_disponivel_orcamento < 0:
            cor_valor_disponivel_orcamento = 'red'
        else:
            cor_valor_disponivel_orcamento = 'green'
        resumo_recursos.append(
            dict(
                despesa=despesa,
                valor_reservado=valor_reservado,
                valor_distribuido=valor_distribuido,
                valor_disponivel_orcamento=valor_disponivel_orcamento,
                valor_executado=valor_executado,
                valor_disponivel_execucao=valor_disponivel_execucao,
                cor_valor_disponivel_orcamento=cor_valor_disponivel_orcamento,
            )
        )
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def registro_conclusao(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    title = 'Conclusão do Projeto'
    registro = projeto.get_registro_conclusao()
    form = RegistroConclusaoProjetoForm(data=request.POST or None, instance=registro)
    if form.is_valid():
        registro = form.save(False)
        registro.projeto = projeto
        registro.save()
        return httprr('..', 'Conclusão do projeto registrada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def registro_gasto(request, item_id):
    title = 'Gastos Registrados'
    desembolso = get_object_or_404(Desembolso, pk=item_id)
    is_coordenador = (
        desembolso.projeto.is_coordenador(request.user) or desembolso.projeto.is_gerente_sistemico() or desembolso.projeto.is_coordenador_pesquisa_campus_projeto(request.user)
    )

    registro = None
    if not is_coordenador and not desembolso.projeto.is_avaliador(request.user):
        return httprr('..', 'Apenas o Coordenador do Projeto e o Coordenador de Pesquisa do campus tem acesso a essa página.', 'alert')

    if request.method == 'GET' and 'registro_id' in request.GET:
        RegistroGasto.objects.filter(pk=request.GET['registro_id']).delete()
        return httprr('.', 'Registro excluído com sucesso.')

    if 'editar_registro_id' in request.GET:
        registro = get_object_or_404(RegistroGasto, pk=request.GET['editar_registro_id'])

    if request.method == 'POST':
        form = RegistroGastoForm(request.POST, request.FILES, instance=registro)
        if form.is_valid():
            registro_gasto = form.save(False)
            registro_gasto.desembolso = desembolso
            registro_gasto.save()
            return httprr('.', 'Gasto registrado com sucesso.')
    else:
        if registro:
            form = RegistroGastoForm(instance=registro)
        else:
            initial = dict(descricao=desembolso.item.descricao, qtd=1, valor_unitario=desembolso.valor, ano=desembolso.ano.pk, mes=desembolso.mes)
            form = RegistroGastoForm(initial=initial)
            field_qtd = form.fields['qtd']
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def registro_execucao_etapa(request, etapa_id):
    title = 'Registro de  Execução de Atividade'
    etapa = get_object_or_404(Etapa, pk=etapa_id)
    projeto = etapa.meta.projeto
    pode_acessar = projeto.is_responsavel(request.user) or projeto.is_gerente_sistemico() or projeto.is_coordenador_pesquisa_campus_projeto(request.user)
    if pode_acessar:
        instance = etapa.get_registro_execucao()

        if request.method == 'POST':
            form = RegistroExecucaoEtapaForm(request.POST, request.FILES, instance=instance, etapa=etapa)
            if form.is_valid():
                registro_execucao_etapa = form.save(False)
                registro_execucao_etapa.etapa = etapa
                registro_execucao_etapa.save()
                return httprr('..', 'Execução registrada com sucesso.')
        else:
            if instance:
                form = RegistroExecucaoEtapaForm(instance=instance)
            else:
                initial = dict(inicio_execucao=etapa.inicio_execucao, fim_execucao=etapa.fim_execucao, etapa=etapa)
                form = RegistroExecucaoEtapaForm(initial=initial)
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_visualizar_projetos_em_monitoramento')
def validar_execucao_etapa(request, projeto_id):
    title = 'Validar Execução'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    status = projeto.get_status()
    vinculo = request.user.get_vinculo()
    pode_validar = False
    eh_membro = projeto.eh_participante(request.user)
    eh_avaliador = request.user.groups.filter(name__in=['Coordenador de Pesquisa', 'Supervisor de Projetos de Pesquisa']).exists()
    if not eh_membro and eh_avaliador and projeto.vinculo_supervisor == vinculo:
        pode_validar = True
    is_gerente_sistemico = request.user.groups.filter(name='Diretor de Pesquisa')
    is_coordenador = Participacao.objects.filter(projeto__id=projeto_id, vinculo_pessoa=vinculo, responsavel=True).exists() or is_gerente_sistemico
    if pode_validar:
        if request.method == 'GET' and 'registro_id' in request.GET:
            registro = get_object_or_404(RegistroExecucaoEtapa, pk=request.GET['registro_id'])
            registro.dt_avaliacao = datetime.date.today()
            registro.avaliador = request.user.get_relacionamento()
            registro.aprovado = True
            registro.save()
            return httprr(f'/pesquisa/validar_execucao_etapa/{projeto.pk:d}/?tab=metas', 'Execução de atividade validada com sucesso.')

        elif request.method == 'GET' and 'item_id' in request.GET:
            registro = get_object_or_404(RegistroGasto, pk=request.GET['item_id'])
            registro.dt_avaliacao = datetime.date.today()
            registro.avaliador = request.user.get_relacionamento()
            registro.aprovado = True
            registro.save()
            return httprr(f'/pesquisa/validar_execucao_etapa/{projeto.pk:d}/?tab=gastos', 'Gasto validado com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_realizar_monitoramento_projeto')
def reprovar_execucao_etapa(request, registroetapa_id):
    title = 'Justificar Não Aprovação da Atividade'
    registro = get_object_or_404(RegistroExecucaoEtapa, pk=registroetapa_id)
    projeto = registro.etapa.meta.projeto
    if projeto.vinculo_supervisor == request.user.get_vinculo() or request.user.groups.filter(name='Diretor de Pesquisa'):
        form = ReprovarExecucaoEtapaForm(request.POST or None)
        if form.is_valid():
            registro.dt_avaliacao = datetime.date.today()
            registro.avaliador = request.user.get_relacionamento()
            registro.aprovado = False
            registro.justificativa_reprovacao = form.cleaned_data['obs']
            registro.save()
            return httprr('..', 'Execução de atividade avaliada com sucesso.')
    else:
        raise PermissionDenied

    return locals()


@rtr()
@permission_required('pesquisa.pode_realizar_monitoramento_projeto')
def reprovar_execucao_gasto(request, gasto_id):
    title = 'Justificar Não Aprovação do Gasto'
    registro = get_object_or_404(RegistroGasto, pk=gasto_id)
    projeto = registro.desembolso.projeto
    if projeto.vinculo_supervisor == request.user.get_vinculo() or request.user.groups.filter(name='Diretor de Pesquisa'):
        form = ReprovarExecucaoGastoForm(request.POST or None)
        if form.is_valid():
            registro.dt_avaliacao = datetime.date.today()
            registro.avaliador = request.user.get_relacionamento()
            registro.aprovado = False
            registro.justificativa_reprovacao = form.cleaned_data['obs']
            registro.save()
            return httprr('..', 'Gasto avaliado com sucesso.')
    else:
        raise PermissionDenied
    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_participante_servidor(request, projeto_id):
    title = 'Adicionar Participante'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    if request.method == 'POST':
        form = ParticipacaoServidorForm(data=request.POST)
        form.projeto = projeto
        if form.is_valid():
            participacao = form.save(False)
            participacao.projeto = projeto
            if participacao.vinculo == TipoVinculo.BOLSISTA:
                participacao.bolsa_concedida = True
            participacao.pessoa = form.cleaned_data['servidor']
            participacao.vinculo_pessoa = form.cleaned_data['servidor'].get_vinculo()
            if Participacao.objects.filter(projeto=participacao.projeto, vinculo_pessoa=participacao.vinculo_pessoa).exists():
                return httprr('.', 'Este participante já pertence ao projeto.', tag='error')
            participacao.save()
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_ADICIONAR_SERVIDOR, data_evento=form.cleaned_data.get('data'))
            Participacao.gerar_anexos_do_participante(participacao)
            if projeto.edital.termo_compromisso_servidor:
                titulo = '[SUAP] Pesquisa: Termo de Compromisso do Servidor'
                texto = (
                    '<h1>Pesquisa</h1>'
                    '<h2>Termo de Compromisso do Servidor</h2>'
                    '<p>Você foi cadastrado(a) como membro da equipe do projeto \'{}\'. Acesse o SUAP para aceitar o termo de compromisso.</p>'.format(projeto.titulo)
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [form.cleaned_data.get('servidor').get_vinculo()])

            return httprr('..', 'Participante adicionado com sucesso.')
    else:
        form = ParticipacaoServidorForm()
        form.projeto = projeto

    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_participante_servidor(request, projeto_id, participacao_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    title = f'Editar Participação de {participacao.vinculo_pessoa.pessoa.nome}'
    alterou = False
    form = ParticipacaoServidorForm(request.POST or None, instance=participacao)
    if form.is_valid():
        participacao = form.save(False)
        if participacao.vinculo == TipoVinculo.BOLSISTA:
            participacao.bolsa_concedida = True
        participacao_anterior = Participacao.objects.get(id=participacao.id)
        if form.cleaned_data.get('vinculo') != participacao_anterior.vinculo or form.cleaned_data.get('carga_horaria') != participacao_anterior.carga_horaria:
            alterou = True
        participacao.save()

        if alterou:
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_EDICAO_SERVIDOR, data_evento=form.cleaned_data.get('data'))
            Participacao.gerar_anexos_do_participante(participacao)
        else:
            historico = HistoricoEquipe.objects.filter(participante=participacao, projeto=projeto).order_by('id')
            if historico.exists():
                registro = historico[0]
                registro.data_movimentacao = form.cleaned_data.get('data')
                registro.save()
        return httprr('..', 'Participante editado com sucesso.')

    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_participante_aluno(request, projeto_id, participacao_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    title = f'Editar Participação de {participacao.vinculo_pessoa.pessoa.nome}'
    form = ParticipacaoAlunoForm(request.POST or None, instance=participacao, projeto=projeto)
    alterou = False
    if form.is_valid():
        o = form.save(False)
        if participacao.vinculo == TipoVinculo.BOLSISTA:
            participacao.bolsa_concedida = True
        participacao_anterior = Participacao.objects.get(id=participacao.id)
        if form.cleaned_data.get('vinculo') != participacao_anterior.vinculo or form.cleaned_data.get('carga_horaria') != participacao_anterior.carga_horaria:
            alterou = True
        participacao.save()
        if alterou:
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_EDICAO_ALUNO, data_evento=form.cleaned_data.get('data'))
            Participacao.gerar_anexos_do_participante(participacao)
        else:
            historico = HistoricoEquipe.objects.filter(participante=participacao, projeto=projeto).order_by('id')
            if historico.exists() and form.cleaned_data.get('data'):
                registro = historico[0]
                registro.data_movimentacao = form.cleaned_data.get('data')
                registro.save()
        return httprr('..', 'Participante editado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def alterar_coordenador(request, projeto_id):
    title = 'Alterar Coordenador'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    participacao_anterior = Participacao.objects.get(projeto__id=projeto.pk, responsavel=True)
    participacoes = Participacao.objects.filter(projeto__id=projeto.pk, responsavel=False, ativo=True)
    participacoes = participacoes.filter(vinculo_pessoa__tipo_relacionamento__model='servidor')
    if request.method == 'POST':
        form = AlterarCoordenadorForm(data=request.POST, projeto=projeto)
        if form.is_valid():
            participacao = form.cleaned_data['participacao']
            participacao_anterior.responsavel = False
            participacao_anterior.save()
            participacao_anterior.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_COORDENADOR_DESISTITUIDO)
            participacao.responsavel = True
            participacao.save()
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_COORDENADOR_SUBSTITUIDO)
            return httprr('..', 'Coordenador alterado com sucesso.')
    else:
        form = AlterarCoordenadorForm(projeto=projeto)

    form.fields['participacao'].queryset = participacoes

    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_participante_aluno(request, projeto_id):
    title = 'Adicionar Aluno'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    if request.method == 'POST':
        form = ParticipacaoAlunoForm(data=request.POST, projeto=projeto)
        form.projeto = projeto
        if form.is_valid():
            participacao = form.save(False)
            participacao.projeto = projeto
            if participacao.vinculo == TipoVinculo.BOLSISTA:
                participacao.bolsa_concedida = True
            if Vinculo.objects.filter(id_relacionamento=form.cleaned_data['aluno'].id, tipo_relacionamento__model='aluno'):
                participacao.vinculo_pessoa = Vinculo.objects.filter(id_relacionamento=form.cleaned_data['aluno'].id, tipo_relacionamento__model='aluno')[0]
            if Participacao.objects.filter(projeto=participacao.projeto, vinculo_pessoa=participacao.vinculo_pessoa).exists():
                return httprr('.', 'Este participante já pertence ao projeto.', tag='error')
            participacao.save()
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_ADICIONAR_ALUNO)
            Participacao.gerar_anexos_do_participante(participacao)
            if projeto.edital.termo_compromisso_aluno:
                titulo = '[SUAP] Pesquisa: Termo de Compromisso do Aluno'
                texto = (
                    '<h1>Pesquisa</h1>'
                    '<h2>Termo de Compromisso do Aluno</h2>'
                    '<p>Você foi cadastrado(a) como membro da equipe do projeto \'{}\'. Acesse o SUAP para aceitar o termo de compromisso.</p>'.format(projeto.titulo)
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [form.cleaned_data.get('aluno').get_vinculo()])

            return httprr('..', 'Participante adicionado com sucesso.')
    else:
        form = ParticipacaoAlunoForm(projeto=projeto)
        form.projeto = projeto

    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def pre_aprovar(request, projeto_id):
    return pre_selecionar(request, projeto_id, rejeitar=False)


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def pre_rejeitar(request, projeto_id):
    return pre_selecionar(request, projeto_id, rejeitar=True)


@rtr()
@permission_required('pesquisa.pode_avaliar_projeto')
def avaliar(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = f'Avaliar Projeto - {projeto.titulo}'
    if not projeto.edital.is_periodo_selecao():
        raise PermissionDenied()

    avaliador = request.user.get_profile().pessoafisica
    vinculo = request.user.get_vinculo()
    pode_avaliar_projeto = AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=vinculo, rejeitado=False).exists()

    if not pode_avaliar_projeto:
        raise PermissionDenied()

    # Atualiza a pontuação do currículo lattes, este normaliza e atualiza a pontuação total do projeto.
    projeto.atualizar_pontuacao_curriculo_lattes()
    if projeto.edital.peso_avaliacao_grupo_pesquisa:
        projeto.atualizar_pontuacao_grupo_pesquisa()

    try:
        avaliacao = Avaliacao.objects.get(projeto=projeto, vinculo=vinculo)
    except Exception:
        avaliacao = None
    form = AvaliacaoFormFactory(request, avaliacao, projeto, avaliador, vinculo)
    if form.is_valid():
        form.save()
        return httprr(f'/pesquisa/projetos_especial_pre_aprovados/{projeto.edital.id}/', 'Projeto avaliado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def visualizar_ficha_avaliacao(request, avaliacao_id):
    title = 'Detalhamento da Avaliação do Projeto '
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    itens_avaliacao = ItemAvaliacao.objects.filter(avaliacao=avaliacao).order_by('-pontuacao')

    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projetos_em_monitoramento')
def projetos_em_execucao(request):
    title = 'Monitoramento'
    hoje = datetime.datetime.now()
    projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
    projetos = (
        Projeto.objects.filter(aprovado=True, inativado=False, registroconclusaoprojeto__dt_avaliacao__isnull=True)
        .filter(Q(edital__divulgacao_selecao__lte=hoje) | Q(edital__formato=Edital.FORMATO_SIMPLIFICADO))
        .exclude(id__in=projetos_cancelados)
        .order_by('-edital__divulgacao_selecao')
    )

    if not request.user.groups.filter(name__in=['Diretor de Pesquisa', 'Supervisor de Projetos de Pesquisa', 'Auditor']).exists():
        projetos = projetos.exclude(~Q(uo=get_uo(request.user)))
    ano = request.GET.get('ano')
    form = BuscaProjetoForm(data=request.GET or None, request=request, ano=ano)
    if 'ids' in request.GET:
        try:
            projetos = projetos.filter(id__in=str(request.GET.get('ids')).strip('[]').split(','))
        except Exception:
            pass

    if form.is_valid():
        if form.cleaned_data.get('palavra_chave'):
            projetos = projetos.filter(titulo__icontains=form.cleaned_data['palavra_chave'])

        if form.cleaned_data.get('uo'):
            projetos = projetos.filter(uo=form.cleaned_data['uo'])

        if form.cleaned_data.get('ano'):
            projetos = projetos.filter(edital__inicio_inscricoes__year=form.cleaned_data['ano'])

        if form.cleaned_data.get('edital'):
            projetos = projetos.filter(edital=form.cleaned_data['edital'])

    vinculo = request.user.get_vinculo()
    if (
        request.user.groups.filter(name='Supervisor de Projetos de Pesquisa').exists()
        and not request.user.groups.filter(name__in=['Diretor de Pesquisa', 'Coordenador de Pesquisa']).exists()
    ):
        projetos = projetos.filter(vinculo_supervisor=vinculo)
    else:
        projetos = projetos | projetos.filter(vinculo_supervisor=vinculo)

    if list(request.GET.keys()) and len(list(request.GET.keys())) == 1:
        projetos = projetos.filter(uo=get_uo(request.user))

    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_equipe_projeto')
def remover_participante(request, participacao_id):
    title = 'Inativar Participante'
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    projeto = participacao.projeto
    form = DataInativacaoForm(request.POST or None, projeto=projeto, participacao=participacao)
    if form.is_valid():
        data_escolhida = form.cleaned_data.get('data')
        participacao.ativo = False
        participacao.data_inativacao = data_escolhida
        participacao.save()
        participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_INATIVAR_PARTICIPANTE, data_evento=data_escolhida, obs=form.cleaned_data.get('justificativa'))
        return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=equipe', 'Participação encerrada com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_equipe_projeto')
def ativar_participante(request, participacao_id):
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    projeto = participacao.projeto

    if participacao.vinculo == TipoVinculo.BOLSISTA:
        mensagem_alerta = projeto.mensagem_restricao_adicionar_membro(categoria=Participacao.SERVIDOR, bolsista=True)
        if participacao.is_servidor() and mensagem_alerta:
            return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=equipe', mensagem_alerta, tag='error')
        mensagem_alerta = projeto.mensagem_restricao_adicionar_membro(categoria=Participacao.ALUNO, bolsista=True)
        if not participacao.is_servidor() and mensagem_alerta:
            return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=equipe', mensagem_alerta, tag='error')

    mensagem_alerta = projeto.mensagem_restricao_adicionar_membro(categoria=Participacao.SERVIDOR, bolsista=False)
    if participacao.is_servidor() and mensagem_alerta:
        return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=equipe', mensagem_alerta, tag='error')

    mensagem_alerta = projeto.mensagem_restricao_adicionar_membro(categoria=Participacao.ALUNO, bolsista=False)
    if participacao.eh_aluno() and mensagem_alerta:
        return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=equipe', mensagem_alerta, tag='error')

    participacao.ativo = True
    participacao.data_inativacao = None
    participacao.save()
    participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_ATIVAR_PARTICIPANTE)

    return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=equipe', 'Participante ativado com sucesso.')


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_meta(request, projeto_id):
    title = 'Adicionar Meta'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    if request.method == 'POST':
        form = MetaForm(data=request.POST)
        if form.is_valid():
            o = form.save(False)
            o.projeto = projeto
            o.save()
            return httprr('..', 'Meta adicionada com sucesso.')
    else:
        form = MetaForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_meta(request, meta_id):
    meta = get_object_or_404(Meta, pk=meta_id)
    tem_permissao(request, meta.projeto)
    if request.method == 'POST':
        form = MetaForm(data=request.POST, instance=meta)
        if form.is_valid():
            o = form.save(False)
            o.save()
            return httprr('..', 'Meta editada com sucesso.')
    else:
        form = MetaForm(instance=meta)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def remover_meta(request, meta_id):
    meta = get_object_or_404(Meta, pk=meta_id)
    projeto = meta.projeto
    tem_permissao(request, projeto)
    meta.delete()
    return httprr(f'/pesquisa/projeto/{projeto.pk:d}/?tab=metas', 'Meta removida com sucesso.')


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_etapa(request, meta_id):
    title = 'Adicionar Atividade'
    meta = get_object_or_404(Meta, pk=meta_id)
    projeto = meta.projeto
    tem_permissao(request, projeto)
    if request.method == 'POST':
        form = EtapaForm(data=request.POST, proj=projeto)
        if form.is_valid():
            o = form.save(False)
            o.meta = meta
            o.save()
            form.save_m2m()
            return httprr('..', 'Etapa adicionada com sucesso.')
    else:
        form = EtapaForm(proj=projeto)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def remover_etapa(request, etapa_id):
    etapa = get_object_or_404(Etapa, pk=etapa_id)
    projeto = etapa.meta.projeto
    tem_permissao(request, projeto)
    etapa.delete()
    return httprr(f'/pesquisa/projeto/{projeto.pk:d}/?tab=metas', 'Etapa removida com sucesso.')


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_etapa(request, etapa_id):
    etapa = get_object_or_404(Etapa, pk=etapa_id)
    projeto = etapa.meta.projeto
    tem_permissao(request, projeto)
    if request.method == 'POST':
        form = EtapaForm(data=request.POST, instance=etapa, proj=projeto)
        if form.is_valid():
            o = form.save(False)
            o.save()
            form.save_m2m()
            return httprr('..', 'Etapa editada com sucesso.')
    else:
        form = EtapaForm(instance=etapa, proj=projeto)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_equipe_etapa(request, etapa_id):
    etapa = get_object_or_404(Etapa, pk=etapa_id)
    projeto = etapa.meta.projeto
    tem_permissao(request, projeto)
    title = 'Editar Equipe da Atividade'
    if request.method == 'POST':
        form = EquipeEtapaForm(data=request.POST, instance=etapa, proj=projeto)
        if form.is_valid():
            o = form.save(False)
            o.save()
            form.save_m2m()
            return httprr('..', 'Etapa editada com sucesso.')
    else:
        form = EquipeEtapaForm(instance=etapa, proj=projeto)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def adicionar_recurso(request, edital_id):
    title = 'Adicionar Recurso'
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    if request.method == 'POST':
        form = RecursoForm(data=request.POST or None)
        if form.is_valid():
            o = form.save(False)
            o.edital = edital
            o.origem = form.cleaned_data.get('origem_recurso').descricao
            o.save()
            return httprr('..', 'Recurso adicionado com sucesso.')
    else:
        form = RecursoForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def remover_recurso(request, recurso_id):
    recurso = get_object_or_404(Recurso, pk=recurso_id)
    edital = recurso.edital
    tem_permissao_acesso_edital(request, edital)
    recurso.delete()
    return httprr(f'/pesquisa/edital/{edital.id:d}/', 'Recurso removido com sucesso.')


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def editar_recurso(request, recurso_id):
    recurso = get_object_or_404(Recurso, pk=recurso_id)
    edital = recurso.edital
    tem_permissao_acesso_edital(request, edital)
    if request.method == 'POST':
        form = RecursoForm(data=request.POST, instance=recurso)
        if form.is_valid():
            o = form.save(False)
            o.save()
            return httprr('..', 'Recurso editado com sucesso.')
    else:
        form = RecursoForm(instance=recurso)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def adicionar_criterio_avaliacao(request, pk):
    title = 'Adicionar Critério de Avaliação'
    edital = get_object_or_404(Edital, pk=pk)
    tem_permissao_acesso_edital(request, edital)
    if request.method == 'POST':
        form = CriterioAvaliacaoForm(data=request.POST)
        if form.is_valid():
            o = form.save(False)
            o.edital = edital
            o.save()
            return httprr('..', 'Critério de avaliação adicionado com sucesso.')
    else:
        form = CriterioAvaliacaoForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def remover_criterio_avaliacao(request, pk):
    criterio = get_object_or_404(CriterioAvaliacao, pk=pk)
    if not criterio.pode_ser_removido():
        return httprr('..', 'Critério de avaliação não pode ser removido, pois existem avaliações feitas para esse critério.', tag='error')
    edital = criterio.edital
    tem_permissao_acesso_edital(request, edital)
    criterio.delete()
    return httprr(f'/pesquisa/edital/{edital.id:d}/', 'Critério de avaliação removido com sucesso.')


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def editar_criterio_avaliacao(request, pk):
    title = 'Editar Critério de Avaliação'
    criterio = get_object_or_404(CriterioAvaliacao, pk=pk)
    tem_permissao_acesso_edital(request, criterio.edital)
    if request.method == 'POST':
        form = CriterioAvaliacaoForm(data=request.POST, instance=criterio)
        if form.is_valid():
            o = form.save(False)
            o.save()
            return httprr('..', 'Critério de avaliação editado com sucesso.')
    else:
        form = CriterioAvaliacaoForm(instance=criterio)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def adicionar_anexo_auxiliar(request, edital_id):
    title = 'Adicionar Anexo'
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    if request.method == 'POST':
        form = EditalAnexoAuxiliarForm(data=request.POST)
        if form.is_valid():
            o = form.save(False)
            o.edital = edital
            o.save()
            return httprr('..', 'Anexo adicionado com sucesso.')
    else:
        form = EditalAnexoAuxiliarForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def adicionar_anexo(request, edital_id):
    title = 'Adicionar Anexo'
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    if request.method == 'POST':
        form = EditalAnexoForm(data=request.POST)
        if form.is_valid():
            o = form.save(False)
            o.edital = edital
            o.save()
            return httprr('..', 'Anexo adicionado com sucesso.')
    else:
        form = EditalAnexoForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def remover_anexo(request, anexo_id):
    anexo = get_object_or_404(EditalAnexo, pk=anexo_id)
    edital = anexo.edital
    tem_permissao_acesso_edital(request, edital)
    anexo.delete()
    return httprr(f'/pesquisa/edital/{edital.id:d}/', 'Anexo removido com sucesso.')


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def remover_anexo_auxiliar(request, anexo_id):
    anexo = get_object_or_404(EditalAnexoAuxiliar, pk=anexo_id)
    edital = anexo.edital
    tem_permissao_acesso_edital(request, edital)
    anexo.delete()
    return httprr(f'/pesquisa/edital/{edital.id:d}/', 'Anexo removido com sucesso.')


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def editar_anexo(request, anexo_id):
    anexo = get_object_or_404(EditalAnexo, pk=anexo_id)
    tem_permissao_acesso_edital(request, anexo.edital)
    if request.method == 'POST':
        form = EditalAnexoForm(data=request.POST, instance=anexo)
        if form.is_valid():
            o = form.save(False)
            o.save()
            return httprr('..', 'Anexo editado com sucesso.')
    else:
        form = EditalAnexoForm(instance=anexo)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def editar_anexo_auxiliar(request, anexo_id):
    anexo = get_object_or_404(EditalAnexoAuxiliar, pk=anexo_id)
    tem_permissao_acesso_edital(request, anexo.edital)
    if request.method == 'POST':
        form = EditalAnexoAuxiliarForm(data=request.POST, instance=anexo)
        if form.is_valid():
            o = form.save(False)
            o.save()
            return httprr('..', 'Anexo editado com sucesso.')
    else:
        form = EditalAnexoAuxiliarForm(instance=anexo)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def adicionar_oferta_projeto(request, edital_id):
    title = 'Adicionar Oferta de Projeto'
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    if edital.forma_selecao == Edital.GERAL:
        title = 'Adicionar Campus Participante'

    if request.method == 'POST':
        form = OfertaProjetoPesquisaFormMultiplo(data=request.POST, edital=edital, request=request)
        if form.is_valid():
            campi = form.cleaned_data['campi']
            num_maximo_ic = form.cleaned_data['num_maximo_ic']
            num_maximo_pesquisador = form.cleaned_data['num_maximo_pesquisador']
            for campus in campi:
                qs = BolsaDisponivel.objects.filter(edital=edital, uo=campus)
                if qs.exists():
                    bolsa_disponivel = qs[0]
                else:
                    bolsa_disponivel = BolsaDisponivel()
                bolsa_disponivel.edital = edital
                bolsa_disponivel.uo = campus
                bolsa_disponivel.num_maximo_ic = num_maximo_ic
                bolsa_disponivel.num_maximo_pesquisador = num_maximo_pesquisador
                bolsa_disponivel.save()
            return httprr('..', 'Oferta(s) adicionada(s) com sucesso.')
    else:
        form = OfertaProjetoPesquisaFormMultiplo(edital=edital, request=request)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def remover_oferta_projeto(request, oferta_projeto_id):
    oferta = get_object_or_404(BolsaDisponivel, pk=oferta_projeto_id)
    edital = oferta.edital
    tem_permissao_acesso_edital(request, edital)
    oferta.delete()
    return httprr(f'/pesquisa/edital/{edital.id:d}/', 'Oferta removida com sucesso.')


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def editar_oferta_projeto(request, oferta_projeto_id, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    oferta = get_object_or_404(BolsaDisponivel, pk=oferta_projeto_id)
    if request.method == 'POST':
        form = OfertaProjetoPesquisaForm(data=request.POST, instance=oferta)
        if form.is_valid():
            o = form.save(False)
            o.save()
            form.save_m2m()
            return httprr('..', 'Oferta editada com sucesso.')
    else:
        form = OfertaProjetoPesquisaForm(instance=oferta)
    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_desembolso(request, projeto_id):
    title = 'Adicionar Desembolso'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    if request.method == 'POST':
        form = DesembolsoForm(data=request.POST, proj=projeto)
        if form.is_valid():
            o = form.save(False)
            o.projeto = projeto
            if form.cleaned_data['clonar_operacao']:
                o.save()
                quantidade = form.cleaned_data['clonar_operacao'] - form.cleaned_data['mes']
                i = 1
                mes = form.cleaned_data['mes']
                while i <= quantidade:
                    o.pk = None
                    o.mes = mes + 1
                    o.save()
                    mes = mes + 1
                    i = i + 1
            else:
                o.save()
            return httprr('..', 'Desembolso adicionado com sucesso.')
    else:
        form = DesembolsoForm(proj=projeto)
    return locals()


def tem_permissao(request, projeto):
    is_responsavel = projeto.is_responsavel(request.user) or projeto.is_gerente_sistemico()
    if not is_responsavel:
        raise PermissionDenied()


def tem_permissao_acesso_edital(request, edital):
    if request.user.has_perm('pesquisa.tem_acesso_sistemico') or request.user.has_perm('pesquisa.pode_ver_config_edital'):
        return True
    elif request.user.has_perm('pesquisa.pode_gerenciar_edital') and ((edital.cadastrado_por_vinculo and edital.cadastrado_por_vinculo.setor.uo == get_uo(request.user)) or (edital.autorizado_em and BolsaDisponivel.objects.filter(edital=edital, uo=get_uo(request.user)).exists())):
        return True
    raise PermissionDenied()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_desembolso(request, desembolso_id):
    title = 'Editar Desembolso'
    desembolso = get_object_or_404(Desembolso, pk=desembolso_id)
    tem_permissao(request, desembolso.projeto)

    if request.method == 'POST':
        form = DesembolsoForm(data=request.POST, instance=desembolso)
        if form.is_valid():
            o = form.save(False)
            o.save()
            return httprr('..', 'Desembolso editado com sucesso.')
    else:
        form = DesembolsoForm(instance=desembolso)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def remover_desembolso(request, desembolso_id):
    desembolso = get_object_or_404(Desembolso, pk=desembolso_id)
    tem_permissao(request, desembolso.projeto)
    projeto = desembolso.projeto
    url = f'/pesquisa/projeto/{projeto.id:d}/?tab=plano_desembolso'
    desembolso.delete()
    return httprr(url, 'Desembolso removido com sucesso.')


def salvar_arquivo(projeto_anexo, arquivo_up, vinculo, request):
    arquivo_up.seek(0)
    content = arquivo_up.read()
    nome = arquivo_up.name
    if projeto_anexo.arquivo:
        arquivo = projeto_anexo.arquivo
    else:
        arquivo = Arquivo()
    arquivo.save(nome, vinculo)
    projeto_anexo.arquivo = arquivo
    projeto_anexo.save()
    arquivo.store(request.user, content)

    return arquivo


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def upload_anexo(request, anexo_id):
    title = 'Upload de Arquivo'
    anexo = get_object_or_404(ProjetoAnexo, pk=anexo_id)
    tem_permissao(request, anexo.projeto)
    origem = request.GET.get('origem')
    if request.method == 'POST':
        form = UploadProjetoAnexoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            if not (arquivo_up.name.lower().endswith('.pdf')):
                return httprr('.', 'Apenas arquivos com o formato PDF são permitidos.', tag='error')
            vinculo = request.user.get_vinculo()
            salvar_arquivo(anexo, arquivo_up, vinculo, request)
            if form.cleaned_data.get('origem'):
                return httprr(f'/pesquisa/projeto/{anexo.projeto.id}/?tab=anexos', 'Arquivo enviado com sucesso.')
            else:
                return httprr('..', 'Arquivo enviado com sucesso.')
    else:
        form = UploadProjetoAnexoForm(origem=origem)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_anexo_do_projeto(request, participacao_id):
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    projeto = get_object_or_404(Projeto, pk=participacao.projeto.id)
    tem_permissao(request, projeto)
    title = 'Anexos do Participante  '
    Participacao.gerar_anexos_do_participante(participacao)

    anexos = ProjetoAnexo.objects.filter(projeto=participacao.projeto, vinculo_membro_equipe=participacao.vinculo_pessoa)
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def upload_anexo_auxiliar(request, anexo_id):
    title = 'Upload de Arquivo'
    anexo = get_object_or_404(EditalAnexoAuxiliar, pk=anexo_id)
    tem_permissao_acesso_edital(request, anexo.edital)
    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if anexo.arquivo:
                arquivo = anexo.arquivo
            else:
                arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            anexo.arquivo = arquivo
            anexo.save()
            arquivo.store(request.user, content)
            return httprr(f'/pesquisa/edital/{anexo.edital.id:d}/', 'Arquivo enviado com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_gerenciar_edital')
def upload_edital(request, edital_id):
    title = 'Adicionar Edital'
    edital = get_object_or_404(Edital, pk=edital_id)
    tem_permissao_acesso_edital(request, edital)
    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            o = form.save(False)
            o.edital = edital
            o.data_cadastro = datetime.datetime.now()
            o.vinculo_autor = request.user.get_vinculo()
            o.save()
            return httprr(f'/pesquisa/edital/{edital.id:d}/', 'Arquivo enviado com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def visualizar_arquivo(request, arquivo_id):
    arquivo = get_object_or_404(Arquivo, pk=arquivo_id)
    content = arquivo.load(request.user)
    if content:
        response = HttpResponse(content, content_type=arquivo.get_content_type(content))
        response['Content-Disposition'] = f'inline; filename={get_valid_filename(arquivo.nome)}'
        return response
    else:
        return HttpResponse("O arquivo solicitado foi adulterado ou não existe.")


@rtr()
@permission_required('pesquisa.pode_realizar_monitoramento_projeto')
def avaliar_conclusao_projeto(request, registro_id):
    title = 'Validação da Conclusão do Projeto'
    registro = get_object_or_404(RegistroConclusaoProjeto, pk=registro_id)

    if registro.projeto.vinculo_supervisor == request.user.get_vinculo() or request.user.groups.filter(name='Diretor de Pesquisa'):
        form = ValidacaoConclusaoProjetoForm(request.POST or None, registro=registro)
        if form.is_valid():
            aprovado = form.cleaned_data['aprovado']
            obs = form.cleaned_data['obs']

            registro.dt_avaliacao = datetime.date.today()
            registro.avaliador = request.user.get_relacionamento()
            registro.aprovado = aprovado
            registro.obs_avaliador = obs
            registro.save()
            return httprr('..', 'Conclusão do projeto registrada com sucesso.')
    else:
        raise PermissionDenied
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_foto(request, projeto_id):
    title = 'Adicionar Foto'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    if request.method == 'POST':
        form = FotoProjetoForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            for imagem in request.FILES.getlist("fotos"):
                nova_imagem = FotoProjeto()
                nova_imagem.projeto = projeto
                nova_imagem.legenda = form.cleaned_data.get('legenda')
                nova_imagem.imagem = imagem
                try:
                    nova_imagem.save()
                except Exception:
                    return httprr('..', 'O arquivo é inválido.', tag='error')
            return httprr('..', 'Foto adicionada com sucesso.')
    else:
        form = FotoProjetoForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def remover_foto(request, foto_id):
    foto = get_object_or_404(FotoProjeto, pk=foto_id)
    tem_permissao(request, foto.projeto)
    projeto_id = foto.projeto.id
    foto.delete()
    return httprr(f'/pesquisa/projeto/{projeto_id:d}/?tab=fotos', 'Foto removida com sucesso.')


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_projeto(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    vinculo = request.user.get_vinculo()
    if not CurriculoVittaeLattes.objects.filter(vinculo=vinculo).exists():
        raise PermissionDenied()

    if not request.user.get_vinculo().relacionamento.areas_de_conhecimento.exists():
        return httprr('/pesquisa/tornar_avaliador/', 'Você precisa se cadastrar como avaliador interno para poder submeter um projeto de pesquisa.', tag='error')
    hoje = datetime.datetime.now().date()
    if (
        edital.impedir_coordenador_com_pendencia
        and Projeto.objects.exclude(edital=edital)
        .filter(pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, inativado=False, fim_execucao__lt=hoje, vinculo_coordenador=vinculo)
        .exclude(projetocancelado__cancelado=True, projetocancelado__data_avaliacao__isnull=False)
        .exists()
    ):
        return httprr('/pesquisa/editais_abertos/', 'Este edital não permite a submissão de projeto de coordenadores que possuem projetos com conclusão em atraso.', tag='error')
    hoje = datetime.datetime.now().date()
    curriculo = CurriculoVittaeLattes.objects.filter(vinculo=vinculo)[0]
    if curriculo.datahora_atualizacao and curriculo.datahora_atualizacao.date() < (hoje - relativedelta(months=+edital.tempo_maximo_meses_curriculo_desatualizado)):
        return httprr(
            '/pesquisa/editais_abertos/',
            'Seu currículo lattes não foi atualizado nos últimos {} meses. Acesse a Plataforma Lattes para '
            'atualizá-lo.'.format(edital.tempo_maximo_meses_curriculo_desatualizado),
            tag='error',
        )

    title = 'Adicionar Projeto'
    grupo_pesquisa_online = True

    setores = ()
    if request.user.get_relacionamento().setor_lotacao:
        setores += (request.user.get_relacionamento().setor_lotacao.uo.id,)
    if request.user.get_relacionamento().setor_exercicio:
        setores += (request.user.get_relacionamento().setor_exercicio.uo.id,)
    if request.user.get_relacionamento().setor:
        setores += (request.user.get_relacionamento().setor.uo.id,)

    if not BolsaDisponivel.objects.filter(edital=edital, uo_id__in=setores).exists():
        return httprr('/pesquisa/editais_abertos/', 'Este edital não possui oferta para o seu campus.', tag='error')

    instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    try:
        status = atualizar_grupos_pesquisa(curriculo.id)
        if status == 0 and edital.exige_grupo_pesquisa:
            return httprr(
                '/pesquisa/editais_abertos/',
                'O SUAP não encontrou nenhum Grupo de Pesquisa do {} ao qual você esteja vinculado. '
                'Solicitamos que atualize seu Currículo Lattes e aguarde a disponibilização pública na base '
                'CNPQ para então iniciar a submissão do seu projeto.'.format(instituicao_sigla),
                tag='error',
            )
        if status == 3:
            erro_grupo_pesquisa_offline = True
    except Exception:
        grupo_pesquisa_online = False
    instance = Projeto()
    instance.edital = edital
    instance.coordenador = request.user.pessoafisica
    instance.vinculo_coordenador = vinculo
    form = ProjetoForm(request.POST or None, instance=instance, user=request.user, request=request, edital=edital, grupo_pesquisa_online=grupo_pesquisa_online)
    if request.method == 'POST':
        if form.is_valid():
            if form.cleaned_data["deseja_receber_bolsa"]:
                instance.bolsa_coordenador = form.cleaned_data["deseja_receber_bolsa"]
            else:
                instance.bolsa_coordenador = False

            form.save()
            projeto_id = Participacao.objects.filter(projeto__edital__id=edital_id, vinculo_pessoa=vinculo, responsavel=True).order_by('-id')[0].projeto.id
            return httprr(f'/pesquisa/projeto/{projeto_id:d}/', 'Projeto cadastrado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_projeto(request, projeto_id):
    title = 'Editar Projeto'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    if projeto.get_periodo() == Projeto.PERIODO_EXECUCAO:
        form = EditarProjetoEmExecucaoForm(request.POST or None, instance=projeto, request=request)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/projeto/{projeto.id:d}/', 'Projeto editado com sucesso.')
    elif projeto.get_periodo() == Projeto.PERIODO_INSCRICAO:
        grupo_pesquisa_online = True
        try:
            curriculo = CurriculoVittaeLattes.objects.filter(vinculo=request.user.get_vinculo())[0]
            status = atualizar_grupos_pesquisa(curriculo.id)
        except Exception:
            grupo_pesquisa_online = False

        form = ProjetoForm(request.POST or None, instance=projeto, request=request, user=request.user, grupo_pesquisa_online=grupo_pesquisa_online, edital=projeto.edital)

        if request.method == 'POST':
            if form.is_valid():
                registro_do_coordenador = Participacao.objects.get(projeto=projeto, responsavel=True)
                if not form.cleaned_data["deseja_receber_bolsa"]:
                    registro_do_coordenador.vinculo = TipoVinculo.VOLUNTARIO
                    registro_do_coordenador.bolsa_concedida = False
                else:
                    registro_do_coordenador.vinculo = TipoVinculo.BOLSISTA
                    registro_do_coordenador.bolsa_concedida = True
                registro_do_coordenador.save()

                form.save()
                return httprr(f'/pesquisa/projeto/{projeto.id:d}/', 'Projeto editado com sucesso.')
    else:
        raise PermissionDenied()

    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def pre_selecionar(request, projeto_id, rejeitar=None, url=None):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = f'Justificativa da Pré-Avaliação - {projeto.titulo}'

    if not url:
        url = request.META.get('HTTP_REFERER', '.')

    if not projeto.edital.is_periodo_pre_selecao():
        raise PermissionDenied

    if projeto.data_conclusao_planejamento is None:
        return httprr(url, 'Impossível realizar essa operação, projeto não foi enviado.', tag="error")

    if projeto.edital.impedir_projeto_sem_anexo and projeto.tem_registro_anexos_pendente():
        return httprr(f'/pesquisa/projetos_nao_avaliados/{projeto.edital.id}/', 'Este projeto possui anexos pendentes e não pode ser pré-avaliado.', tag="error")

    if projeto.edital.exige_anuencia and projeto.pendente_anuencia():
        return httprr(
            f'/pesquisa/projetos_nao_avaliados/{projeto.edital.id}/', 'Este projeto não foi deferido pela chefia imediata e não pode ser pré-avaliado.', tag="error"
        )
    if projeto.tem_aceite_pendente():
        return httprr(f'/pesquisa/projetos_nao_avaliados/{projeto.edital.id}/', 'Este projeto possui aceite de termo de compromisso pendente.', tag="error")

    form = JustificativaPreAvaliacaoForm(request.POST or None, instance=projeto)
    if form.is_valid():
        projeto.vinculo_autor_pre_avaliacao = request.user.get_vinculo()
        projeto.data_pre_avaliacao = datetime.date.today()

        if projeto.pre_aprovado or rejeitar:
            projeto.pre_aprovado = False
        else:
            projeto.pre_aprovado = True
            projeto.vinculo_supervisor = request.user.get_vinculo()
        projeto.save()
        return httprr(f'/pesquisa/projetos_nao_avaliados/{projeto.edital.id}/', 'Projeto pré-avaliado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def historico_equipe(request, participacao_id):
    title = 'Histórico da Participação'
    eh_sistemico = request.user.has_perm('pesquisa.add_origemrecursoedital')
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    historico = HistoricoEquipe.objects.filter(participante=participacao_id).order_by('id').exclude(movimentacao='Ativado')
    como_coordenador = historico.filter(categoria=HistoricoEquipe.COORDENADOR)
    como_membro = historico.filter(categoria=HistoricoEquipe.MEMBRO)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def concluir_planejamento(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    if projeto.edital.tem_formato_completo() and projeto.get_periodo() != Projeto.PERIODO_INSCRICAO:
        raise PermissionDenied()

    metas = Meta.objects.filter(projeto_id=projeto_id)

    tem_desembolso = True
    tem_plano_aplicacao = True
    mensagem_erro = ''
    if projeto.edital.tem_formato_completo():
        if projeto.edital.tem_fonte_recurso():
            qs_plano_de_aplicacao = ItemMemoriaCalculo.objects.filter(projeto_id=projeto_id)
            if qs_plano_de_aplicacao:
                for memoria_calculo in qs_plano_de_aplicacao:
                    if not Desembolso.objects.filter(item=memoria_calculo).exists():
                        tem_desembolso = False
            else:
                tem_plano_aplicacao = False

        if projeto.edital.tipo_edital == Edital.PESQUISA_INOVACAO_CONTINUO:
            tem_desembolso = True
            tem_plano_aplicacao = True

        if projeto.edital.participa_aluno and not projeto.tem_aluno():
            mensagem_erro = mensagem_erro + '* O projeto deve ter pelo menos um aluno na equipe.</br>'

        if not projeto.grupo_pesquisa and projeto.edital.exige_grupo_pesquisa:
            mensagem_erro = mensagem_erro + '* Projeto sem grupo de pesquisa. Edite o projeto e informe o grupo de pesquisa.</br>'

        if not tem_desembolso:
            mensagem_erro = mensagem_erro + '* Cadastre o Plano de Desembolso para cada Item de Mémoria de Cálculo antes de enviar o Projeto.</br>'

        if not tem_plano_aplicacao:
            mensagem_erro = mensagem_erro + '* Cadastre o Plano de Aplicação antes de enviar o Projeto.</br>'

        if not metas:
            mensagem_erro = mensagem_erro + '* Cadastre as Metas/Atividades antes de enviar o Projeto.</br>'

        if projeto.edital.atividade_todo_mes and not projeto.tem_atividade_todo_mes():
            mensagem_erro = mensagem_erro + '* O projeto deve ter pelo menos uma atividade sendo executada em cada mês.</br>'

        else:
            tem_atividade = False
            for meta in metas:
                atividade = Etapa.objects.filter(meta_id=meta.id)
                if atividade:
                    tem_atividade = True
            if not tem_atividade:
                mensagem_erro = mensagem_erro + '* Cadastre as Atividades de cada Meta antes de enviar o Projeto.</br>'
    if mensagem_erro != '':
        return httprr(f'/pesquisa/projeto/{projeto.id:d}/', mark_safe('Atenção! O projeto não pode ser enviado. Resolva as pendências a seguir:<br>' + mensagem_erro), tag="error")
    agora = datetime.datetime.now()
    projeto.data_conclusao_planejamento = agora
    if not projeto.vinculo_coordenador:
        projeto.vinculo_coordenador = Participacao.objects.filter(projeto=projeto, responsavel=True)[0].vinculo_pessoa
    projeto.save()
    historico_projeto = ProjetoHistoricoDeEnvio()
    historico_projeto.projeto = projeto
    historico_projeto.data_operacao = agora
    historico_projeto.situacao = ProjetoHistoricoDeEnvio.ENVIADO
    historico_projeto.operador = request.user.get_relacionamento()
    historico_projeto.save()

    if projeto.edital.exige_anuencia:
        chefes = request.user.get_relacionamento().funcionario.chefes_na_data(agora.date())
        if chefes:
            chefe_servidor = chefes[0].servidor
            projeto.responsavel_anuencia = chefe_servidor
            projeto.save()
            titulo = '[SUAP] Pesquisa: Anuência de Projeto de Pesquisa'
            texto = f'<h1>Pesquisa</h1><h2>Anuência de Projeto de Pesquisa</h2><p>Foi solicitada sua anuência no projeto de pesquisa: {projeto.titulo}. Acesse o SUAP para mais detalhes.</p>'
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [chefe_servidor.get_vinculo()])

    return httprr(f'/pesquisa/projeto/{projeto.id:d}/', 'Projeto enviado com sucesso.')


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def finalizar_conclusao(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not projeto.edital.tem_monitoramento_por_atividades():
        tem_permissao(request, projeto)
        if not projeto.data_finalizacao_conclusao and not projeto.relatorioprojeto_set.filter(avaliado_em__isnull=True).exists() and projeto.relatorioprojeto_set.filter(tipo=RelatorioProjeto.FINAL).exists():
            projeto.data_finalizacao_conclusao = datetime.datetime.now()
            projeto.save()
            historico = ProjetoHistoricoDeEnvio()
            historico.projeto = projeto
            historico.data_operacao = datetime.datetime.now()
            historico.situacao = ProjetoHistoricoDeEnvio.FINALIZADO
            historico.operador = request.user.get_relacionamento()
            historico.save()
            movimentacoes_sem_data_saida = HistoricoEquipe.objects.filter(projeto=projeto,
                                                                          data_movimentacao_saida__isnull=True)
            if movimentacoes_sem_data_saida:
                for movimentacao in movimentacoes_sem_data_saida:
                    movimentacao.data_movimentacao_saida = datetime.datetime.today()
                    movimentacao.save()

            return httprr(f'/pesquisa/projeto/{projeto.id:d}/', 'Conclusão finalizada com sucesso.')
        else:
            mensagem_erro = 'Projeto não pode ser finalizado, pois não há registro de relatório final ou o relatório final não foi avaliado pelo supervisor do projeto.'
            return httprr(f'/pesquisa/projeto/{projeto.id:d}/', mensagem_erro, tag="error")

    if projeto.edital.tem_formato_completo():
        tem_permissao(request, projeto)
        mensagem_erro = ''
        if projeto.tem_registro_execucao_etapa_pendente():
            mensagem_erro = 'Projeto não pode ser finalizado, pois não há registro de execução de atividades ou existe registro não avaliados pelo Diretor(a) ou Coordenador(a) de Pesquisa do Campus'
        if projeto.tem_registro_gasto_pendente():
            mensagem_erro = 'Projeto não pode ser finalizado, pois existem desembolsos sem o registro das despesas realizadas ou existe despesa não avaliada pelo Diretor(a) ou Coordenador(a) de Pesquisa do Campus.'
        if projeto.tem_registro_anexos_pendente():
            mensagem_erro = 'Projeto não pode ser finalizado, pois não há registro dos anexos do projeto.'

        if mensagem_erro != '':
            return httprr(f'/pesquisa/projeto/{projeto.id:d}/?tab=conclusao', mensagem_erro, tag="error")
    else:
        if not (projeto.vinculo_supervisor == request.user.get_vinculo()):
            raise PermissionDenied()

    registro = RegistroConclusaoProjeto.objects.filter(projeto=projeto)[0]
    if not projeto.edital.tem_formato_completo():
        title = 'Finalizar Projeto'
        if request.method == 'POST':
            form = RegistroConclusaoProjetoObsForm(data=request.POST, instance=registro)
            if form.is_valid():
                registro = form.save(False)
                registro.projeto = projeto
                registro.dt_avaliacao = datetime.datetime.now()
                registro.avaliador = request.user.get_relacionamento()
                registro.save()
        else:
            form = RegistroConclusaoProjetoObsForm(instance=registro)

    if projeto.edital.tem_formato_completo() or registro.avaliador:
        projeto.data_finalizacao_conclusao = datetime.datetime.now()
        projeto.save()
        historico = ProjetoHistoricoDeEnvio()
        historico.projeto = projeto
        historico.data_operacao = datetime.datetime.now()
        historico.situacao = ProjetoHistoricoDeEnvio.FINALIZADO
        historico.operador = request.user.get_relacionamento()
        historico.save()
        movimentacoes_sem_data_saida = HistoricoEquipe.objects.filter(projeto=projeto, data_movimentacao_saida__isnull=True)
        if movimentacoes_sem_data_saida:
            for movimentacao in movimentacoes_sem_data_saida:
                movimentacao.data_movimentacao_saida = datetime.datetime.today()
                movimentacao.save()

        return httprr(f'/pesquisa/projeto/{projeto.id:d}/', 'Conclusão finalizada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def gerenciar_historico_projeto(request, projeto_id):
    historico = ProjetoHistoricoDeEnvio.objects.filter(projeto=projeto_id).order_by('data_operacao')
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = f'Movimentação do Projeto: {projeto.titulo}'
    is_pre_avaliador = projeto.is_pre_avaliador(request.user) or projeto.is_gerente_sistemico(request.user)
    form = ProjetoHistoricoDeEnvioForm(request.POST or None)
    if form.is_valid():
        o = form.save(False)
        o.projeto = projeto
        o.data_operacao = datetime.datetime.now()
        o.situacao = ProjetoHistoricoDeEnvio.DEVOLVIDO
        o.operador = request.user.get_relacionamento()
        o.save()
        projeto.data_conclusao_planejamento = None
        projeto.save()
        responsavel = Participacao.objects.get(projeto__id=projeto_id, responsavel=True)
        titulo = '[SUAP] Pesquisa: Devolução de Projeto'
        texto = '<h1>Pesquisa</h1>' '<h2>Devolução de Projeto</h2>' '<p>O Projeto \'{}\' foi devolvido pelo Gestor de Pesquisa e Inovação.</p>'.format(projeto.titulo)
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [responsavel.vinculo_pessoa])
        return httprr('.', 'Devolução do projeto registrada com sucesso.')
    else:
        form = ProjetoHistoricoDeEnvioForm()
    return locals()


@rtr()
@transaction.atomic
@permission_required('pesquisa.pode_interagir_com_projeto')
def tornar_avaliador(request):
    title = 'Áreas de Conhecimento - Avaliação de Projetos de Pesquisa'
    pessoa = request.user.get_relacionamento()
    areas_conhecimentos = pessoa.areas_de_conhecimento.all().order_by('superior')
    form = ProjetoAvaliadorForm(data=request.POST or None, request=request, pessoa=pessoa)
    if form.is_valid():
        ids_areas = list()
        for area in form.cleaned_data.get('areas_de_conhecimento'):
            ids_areas.append(area.id)
            if area not in pessoa.areas_de_conhecimento.all():
                pessoa.areas_de_conhecimento.add(area)
        outras_areas = pessoa.areas_de_conhecimento.exclude(id__in=ids_areas)
        if outras_areas.exists():
            for area in outras_areas:
                pessoa.areas_de_conhecimento.remove(area)

        return httprr('.', 'Área de conhecimento cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.add_edital')
def distribuir_bolsas(request):
    title = 'Distribuição de Bolsas dos Projetos de Pesquisa'
    editais = Edital.objects.em_distribuicao_bolsa()
    uos = None

    if request.user.groups.filter(name='Coordenador de Pesquisa') and not request.user.groups.filter(name='Diretor de Pesquisa'):
        uos = (request.user.get_relacionamento().setor_lotacao.uo, request.user.get_relacionamento().setor.uo, request.user.get_relacionamento().setor_exercicio.uo)
        editais = editais.filter(forma_selecao=Edital.CAMPUS)
    edital_parcial = False
    return locals()


@rtr()
@permission_required('pesquisa.add_edital')
def gerenciar_bolsas(request, edital_id, campus_id=None):
    title = 'Gerenciamento de Bolsas dos Projetos de Pesquisa'
    qtd_bolsa_pesquisador_distribuida = 0
    qtd_bolsa_ic_distribuida = 0
    qtd_bolsa_pesquisador_solicitada = 0
    qtd_bolsa_ic_solicitada = 0
    edital = get_object_or_404(Edital, id=edital_id)
    campus = None
    if edital.forma_selecao == Edital.CAMPUS and campus_id:
        campus = get_object_or_404(UnidadeOrganizacional, id=campus_id)
        if request.user.groups.filter(name='Coordenador de Pesquisa') and not request.user.groups.filter(name='Diretor de Pesquisa'):
            campi = (request.user.get_relacionamento().setor_lotacao.uo, request.user.get_relacionamento().setor.uo, request.user.get_relacionamento().setor_exercicio.uo)
            if not campus in campi:
                raise PermissionDenied()

    if not request.POST:
        edital.classifica_projetos_pesquisa(campus)

    if edital.forma_selecao == Edital.GERAL:
        projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True).order_by('-pontuacao_total')
    else:
        projetos = Projeto.objects.filter(edital=edital, uo=campus, pre_aprovado=True).order_by('-pontuacao_total')
    if projetos:
        if edital.forma_selecao == Edital.CAMPUS and edital.bolsadisponivel_set.filter(uo=campus):
            qtd_bolsa_pesquisador = edital.bolsadisponivel_set.get(uo=campus).num_maximo_pesquisador
            qtd_bolsa_ic = edital.bolsadisponivel_set.get(uo=campus).num_maximo_ic
            participacoes = Participacao.objects.filter(projeto__in=projetos.values_list('id', flat=True)).order_by('vinculo')
        elif edital.forma_selecao == Edital.GERAL:
            qtd_bolsa_pesquisador = edital.qtd_bolsa_servidores
            qtd_bolsa_ic = edital.qtd_bolsa_alunos
            participacoes = Participacao.objects.filter(projeto__in=projetos.values_list('id', flat=True)).order_by('vinculo')
        for participacao in participacoes:
            if participacao.is_servidor():
                if participacao.vinculo == TipoVinculo.BOLSISTA:
                    qtd_bolsa_pesquisador_solicitada = qtd_bolsa_pesquisador_solicitada + 1
                if participacao.bolsa_concedida == True and participacao.vinculo == TipoVinculo.BOLSISTA:
                    qtd_bolsa_pesquisador_distribuida = qtd_bolsa_pesquisador_distribuida + 1
            else:
                if participacao.vinculo == TipoVinculo.BOLSISTA:
                    qtd_bolsa_ic_solicitada = qtd_bolsa_ic_solicitada + 1
                if participacao.bolsa_concedida == True and participacao.vinculo == TipoVinculo.BOLSISTA:
                    qtd_bolsa_ic_distribuida = qtd_bolsa_ic_distribuida + 1
        saldo_bolsa_pesquisador = qtd_bolsa_pesquisador - qtd_bolsa_pesquisador_distribuida
        saldo_bolsa_ic = qtd_bolsa_ic - qtd_bolsa_ic_distribuida

    if 'xls' in request.GET:
        return gerenciar_bolsas_export_to_xls(request, projetos)

    if request.POST:
        ids_participacao_de_servidor_bolsa_concedida = request.POST.getlist('participacoes_pesquisadores')
        ids_participacao_de_aluno_bolsa_concedidas = request.POST.getlist('participacoes_ic')
        ids_projetos_aprovados = request.POST.getlist('situacao')
        if campus:
            superou_cota_pesquisador, superou_cota_ic = edital.distribuir_bolsas(
                ids_participacao_de_servidor_bolsa_concedida, ids_participacao_de_aluno_bolsa_concedidas, ids_projetos_aprovados, id_uo=campus.id
            )
        else:
            superou_cota_pesquisador, superou_cota_ic = edital.distribuir_bolsas(
                ids_participacao_de_servidor_bolsa_concedida, ids_participacao_de_aluno_bolsa_concedidas, ids_projetos_aprovados
            )

        if not superou_cota_pesquisador and not superou_cota_ic and campus_id:
            return httprr(f'/pesquisa/gerenciar_bolsas/{edital_id}/{campus_id}/', 'Bolsas salvas com sucesso.')
        elif not superou_cota_pesquisador and not superou_cota_ic:
            return httprr(f'/pesquisa/gerenciar_bolsas/{edital_id}/', 'Bolsas salvas com sucesso.')
        elif superou_cota_pesquisador and campus_id:
            return httprr(
                f'/pesquisa/gerenciar_bolsas/{edital_id}/{campus_id}/',
                'A quantidade de bolsas distribuídas para pesquisadores superou a cota destinada para o campus.',
                tag='error',
            )
        else:
            return httprr(
                f'/pesquisa/gerenciar_bolsas/{edital_id}/',
                'A quantidade de bolsas distribuídas de iniciação científica superou a cota destinada para o campus.',
                tag='error',
            )
    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def plano_trabalho_participante(request, projeto_id, participacao_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    descricao_plano = []
    metas = projeto.get_metas()
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    participante = get_object_or_404(Participacao, id=participacao_id)
    for meta in metas:
        etapas = meta.etapa_set.filter(integrantes__in=[participante.id]).order_by('ordem')
        if etapas:
            for etapa in etapas:
                descricao_plano.append(etapa)

    return locals()


@rtr()
@permission_required('pesquisa.add_origemrecursoedital')
def reabrir_projeto(request, projeto_id):
    historico = ProjetoHistoricoDeEnvio.objects.filter(projeto=projeto_id).order_by('data_operacao')
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = f'Reabertura do Projeto: {projeto.titulo} '
    form = ProjetoHistoricoDeEnvioForm(request.POST or None)
    if form.is_valid():
        o = form.save(False)
        o.projeto = projeto
        o.situacao = ProjetoHistoricoDeEnvio.REBAERTO
        o.data_operacao = datetime.datetime.now()
        o.operador = request.user.get_relacionamento()
        o.save()
        projeto.data_finalizacao_conclusao = None
        projeto.save()
        if RegistroConclusaoProjeto.objects.filter(projeto=projeto).exists():
            registro_conclusao = RegistroConclusaoProjeto.objects.get(projeto=projeto)
            registro_conclusao.aprovado = False
            registro_conclusao.dt_avaliacao = None
            registro_conclusao.save()
        responsavel = Participacao.objects.get(projeto__id=projeto_id, responsavel=True)
        titulo = '[SUAP] Pesquisa: Reabetura de Projeto'
        texto = '<h1>Pesquisa</h1>' '<h2>Reabetura de Projeto</h2>' '<p>O Projeto \'{}\' foi reaberto pelo gestor de pesquisa e inovação.</p>'.format(projeto.titulo)
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [responsavel.vinculo_pessoa])
        return httprr('..', 'Reabertura do projeto realizada com sucesso.')

    else:
        form = ProjetoHistoricoDeEnvioForm()
    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def selecionar_avaliadores(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    title = f'Selecionar Avaliadores dos Projetos do {edital.titulo}'
    if request.user.groups.filter(name='Coordenador de Pesquisa'):
        projetos = Projeto.objects.filter(edital=edital, uo=get_uo(request.user), pre_aprovado=True).order_by('titulo')
    else:
        projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True).order_by('titulo')

    form = IndicarAvaliadorForm(request.GET or None, request=request)
    if form.is_valid():
        status_avaliacao = form.cleaned_data['status_avaliacao']
        palavra_chave = form.cleaned_data['palavra_chave']
        uo = form.cleaned_data['uo']
        if uo:
            projetos = projetos.filter(uo__id=uo.id)
        if palavra_chave:
            projetos = projetos.filter(avaliadorindicado__vinculo__pessoa__nome__icontains=palavra_chave)
        if status_avaliacao:
            if int(status_avaliacao) == 1:  # avaliados
                projetos = projetos.filter(avaliacao__isnull=False).distinct()
            elif int(status_avaliacao) == 2:  # não avaliados
                projetos = projetos.filter(avaliacao__isnull=True).distinct()
            elif int(status_avaliacao) == 3:  # parcialmente avaliados
                ids = list()
                for projeto in projetos:
                    tem_avaliacao_realizada = nao_tem_avaliacao_realizada = False
                    ids_avaliadores = AvaliadorIndicado.objects.filter(projeto=projeto).values_list('vinculo', flat=True)
                    for id in ids_avaliadores:
                        if not tem_avaliacao_realizada:
                            tem_avaliacao_realizada = Avaliacao.objects.filter(projeto=projeto, vinculo=id).exists()
                        if not nao_tem_avaliacao_realizada:
                            nao_tem_avaliacao_realizada = not Avaliacao.objects.filter(projeto=projeto, vinculo=id).exists()

                    if tem_avaliacao_realizada and nao_tem_avaliacao_realizada:
                        ids.append(projeto.id)

                projetos = projetos.filter(id__in=ids)

    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def selecionar_avaliadores_do_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = f'Indicar Avaliadores do Projeto {projeto.titulo}'
    url = request.get_full_path().split('url=')[1]
    form = IndicarAvaliadoresForm(request.POST or None)
    if form.is_valid():
        avaliadores_cadastrados = AvaliadorIndicado.objects.filter(projeto=projeto)
        edital = projeto.edital
        if edital.exige_comissao:
            if request.user.groups.filter(name='Coordenador de Pesquisa'):
                membros_comissao = Vinculo.objects.filter(id__in=ComissaoEditalPesquisa.objects.filter(edital=projeto.edital, uo=get_uo(request.user)).values_list('vinculos_membros', flat=True))
            else:
                membros_comissao = Vinculo.objects.filter(
                    id__in=ComissaoEditalPesquisa.objects.filter(edital=projeto.edital).values_list('vinculos_membros',
                                                                                                    flat=True))

        else:
            titulacoes = edital.titulacoes_avaliador.all().values_list('codigo', flat=True)
            ids_externos = set(
                AvaliadorExterno.objects.filter(titulacao__codigo__in=titulacoes, vinculo__in=PrestadorServico.objects.filter(
                    areas_de_conhecimento__isnull=False).values_list('vinculos',
                                                                     flat=True)).values_list(
                    'vinculo',
                    flat=True))
            ids_internos = set(Servidor.objects.filter(titulacao__codigo__in=titulacoes, areas_de_conhecimento__isnull=False).values_list('vinculo', flat=True))
            union = set.union(ids_externos, ids_internos)
            membros_comissao = Vinculo.objects.filter(id__in=union)
        avaliadores_da_area = Servidor.objects.all()
        buscou = False
        if form.cleaned_data.get('nome'):
            membros_comissao = membros_comissao.filter(pessoa__nome__icontains=form.cleaned_data.get('nome'))
        if form.cleaned_data.get('matricula'):
            buscou = True
            avaliadores_da_area = avaliadores_da_area.filter(matricula=form.cleaned_data.get('matricula'))
        if form.cleaned_data.get('titulacao'):
            ids_externos = set(AvaliadorExterno.objects.filter(titulacao=form.cleaned_data.get('titulacao')).values_list('vinculo', flat=True))
            avaliadores_da_area = avaliadores_da_area.filter(titulacao=form.cleaned_data.get('titulacao'))
            ids_internos = set(avaliadores_da_area.values_list('vinculo', flat=True))
            union = set.union(ids_externos, ids_internos)
            membros_comissao = membros_comissao.filter(id__in=union)
        if form.cleaned_data.get('filtrar_por_area'):
            avaliadores_da_area = avaliadores_da_area.filter(areas_de_conhecimento=projeto.area_conhecimento)
            ids_externos = set(
                AvaliadorExterno.objects.filter(vinculo__in=PrestadorServico.objects.filter(areas_de_conhecimento=projeto.area_conhecimento).values_list('vinculos',
                                                                                                                                                         flat=True)).values_list('vinculo', flat=True))
            ids_internos = set(avaliadores_da_area.values_list('vinculo', flat=True))
            union = set.union(ids_externos, ids_internos)
            membros_comissao = membros_comissao.filter(id__in=union)
        if form.cleaned_data.get('area_conhecimento'):
            avaliadores_da_area = avaliadores_da_area.filter(areas_de_conhecimento=form.cleaned_data.get('area_conhecimento'))
            ids_externos = set(
                AvaliadorExterno.objects.filter(vinculo__in=PrestadorServico.objects.filter(
                    areas_de_conhecimento=form.cleaned_data.get('area_conhecimento')).values_list('vinculos',
                                                                                                  flat=True)).values_list('vinculo',
                                                                                                                          flat=True))
            ids_internos = set(avaliadores_da_area.values_list('vinculo', flat=True))
            union = set.union(ids_externos, ids_internos)
            membros_comissao = membros_comissao.filter(id__in=union)
        if form.cleaned_data.get('disciplina_ingresso'):
            buscou = True
            ids_pela_disciplina = list()
            for servidor in avaliadores_da_area.filter(professor__isnull=False):
                if servidor.professor_set.first().disciplina == form.cleaned_data.get('disciplina_ingresso'):
                    ids_pela_disciplina.append(servidor.id)
            avaliadores_da_area = avaliadores_da_area.filter(id__in=ids_pela_disciplina)
        if buscou:
            membros_comissao = membros_comissao.filter(id__in=avaliadores_da_area.values_list('vinculos', flat=True))
        servidores_equipes = projeto.get_participacoes_servidores_ativos()
        ids_servidores = []
        for servidor in servidores_equipes:
            ids_servidores.append(servidor.vinculo_pessoa.id)

        if not projeto.edital.campus_especifico:
            pessoas = membros_comissao.exclude(id__in=ids_servidores).exclude(setor__uo=projeto.uo)
        else:
            pessoas = membros_comissao.exclude(id__in=ids_servidores)

        lista_avaliadores = list()

        if request.GET.get('sorteio'):
            avaliadores_da_area = Servidor.objects.filter(areas_de_conhecimento=projeto.area_conhecimento)
            membros_comissao = membros_comissao.filter(id__in=avaliadores_da_area.values_list('vinculos', flat=True))

            lista_qtd = list()

            for pessoa in membros_comissao.order_by('pessoa__nome'):
                lista_qtd.append([pessoa, AvaliadorIndicado.objects.filter(vinculo=pessoa, projeto__edital=projeto.edital).count()])
            lista_qtd.sort(key=lambda x: x[1])
            quantidade_indicada = 0
            tamanho_da_lista = len(lista_qtd)
            for pessoa in pessoas.order_by('pessoa__nome'):
                indicacoes_no_edital = AvaliadorIndicado.objects.filter(vinculo=pessoa,
                                                                        projeto__edital=projeto.edital).count()
                indicacoes_total = AvaliadorIndicado.objects.filter(vinculo=pessoa).count()
                avaliacoes_total = Avaliacao.objects.filter(vinculo=pessoa).count()
                if quantidade_indicada < 3:
                    if quantidade_indicada < tamanho_da_lista and pessoa.id == lista_qtd[quantidade_indicada][0].id:
                        lista_avaliadores.append([pessoa, True, indicacoes_no_edital, indicacoes_total, avaliacoes_total])
                        quantidade_indicada = quantidade_indicada + 1
                    else:
                        lista_avaliadores.append([pessoa, False, indicacoes_no_edital, indicacoes_total, avaliacoes_total])
                else:
                    lista_avaliadores.append([pessoa, False, indicacoes_no_edital, indicacoes_total, avaliacoes_total])
        else:
            for pessoa in pessoas.order_by('pessoa__nome'):
                indicacoes_no_edital = AvaliadorIndicado.objects.filter(vinculo=pessoa, projeto__edital=projeto.edital).count()
                indicacoes_total = AvaliadorIndicado.objects.filter(vinculo=pessoa).count()
                avaliacoes_total = Avaliacao.objects.filter(vinculo=pessoa).count()
                if pessoa.id in avaliadores_cadastrados.values_list('vinculo', flat=True):
                    lista_avaliadores.append([pessoa, True, indicacoes_no_edital, indicacoes_total, avaliacoes_total])
                else:
                    lista_avaliadores.append([pessoa, False, indicacoes_no_edital, indicacoes_total, avaliacoes_total])

    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def salvar_avaliadores_do_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    avaliadores_cadastrados = AvaliadorIndicado.objects.filter(projeto=projeto)
    grupo = Group.objects.get(name='Avaliador Sistêmico de Projetos de Pesquisa')
    escolhidos = request.POST.getlist('registros')
    url = request.get_full_path().split('url=')[1]
    ids_escolhidos = list()
    if escolhidos:
        for item in escolhidos:
            ids_escolhidos.append(int(item))
    for avaliador in avaliadores_cadastrados:
        if avaliador.vinculo.id not in ids_escolhidos:
            avaliador.delete()
            if not AvaliadorIndicado.objects.filter(vinculo=avaliador.vinculo).exists():
                avaliador.vinculo.user.groups.remove(grupo)
    for avaliador in Vinculo.objects.filter(id__in=ids_escolhidos):
        if avaliador.user and avaliador.id not in avaliadores_cadastrados.values_list('vinculo', flat=True):
            novo_avaliador = AvaliadorIndicado()
            novo_avaliador.vinculo = avaliador
            novo_avaliador.projeto = projeto
            if projeto.edital.prazo_aceite_indicacao:
                prazo_aceite = datetime.datetime.now() + relativedelta(days=projeto.edital.prazo_aceite_indicacao)
                prazo_avaliacao = prazo_aceite + relativedelta(days=projeto.edital.prazo_avaliacao)
                novo_avaliador.prazo_para_aceite = prazo_aceite
                novo_avaliador.prazo_para_avaliacao = prazo_avaliacao
            novo_avaliador.save()
            novo_avaliador.vinculo.user.groups.add(grupo)

            fim_selecao = projeto.edital.fim_selecao
            if projeto.edital.eh_edital_continuo():
                fim_selecao = projeto.edital.fim_inscricoes
            titulo = '[SUAP] Avaliação de Projeto de Pesquisa'
            if projeto.edital.prazo_aceite_indicacao:
                texto = (
                    '<h1>Avaliação de Projeto de Pesquisa</h1>'
                    '<h2>{0}</h2>'
                    '<p>Foi solicitada sua avaliação do projeto de pesquisa: {0}.</p>'
                    '<p>Prazo para registrar que aceita a indicação: {5}.</p>'
                    '<p>Prazo para realizar a avaliação: {6}.</p>'
                    '<p>Caso os prazos não sejam cumpridos, a indicação será cancelada automaticamente.</p>'
                    '<p>O registro de aceite e a avaliação poderão ser realizados através do seguinte endereço: <a href="{1}/pesquisa/projetos_especial_pre_aprovados/{2}/">{1}/pesquisa/projetos_especial_pre_aprovados/{2}/</a></p>'
                    '<p>Seu acesso ao projeto estará disponível no SUAP durante o período de avaliação do edital: {3} - {4}.</p>'.format(
                        projeto.titulo, settings.SITE_URL, projeto.edital.id, format_(projeto.edital.inicio_selecao),
                        format_(fim_selecao), format_(novo_avaliador.prazo_para_aceite), format_(novo_avaliador.prazo_para_avaliacao)
                    )
                )

            else:
                texto = (
                    '<h1>Avaliação de Projeto de Pesquisa</h1>'
                    '<h2>{0}</h2>'
                    '<p>Foi solicitada sua avaliação do projeto de pesquisa: {0}.</p>'
                    '<p>A avaliação poderá ser realizada através do seguinte endereço: <a href="{1}/pesquisa/projetos_especial_pre_aprovados/{2}/">{1}/pesquisa/projetos_especial_pre_aprovados/{2}/</a></p>'
                    '<p>Seu acesso ao projeto estará disponível no SUAP durante o período de avaliação do edital: {3} - {4}.</p>'.format(
                        projeto.titulo, settings.SITE_URL, projeto.edital.id, format_(projeto.edital.inicio_selecao), format_(fim_selecao)
                    )
                )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [avaliador])
    return httprr(url, 'Avaliadores cadastrados com sucesso.')


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def atualizar_pontuacao(request, projeto_id):
    """
    Esta ação é oriundo do botão atualizar pontuação que está disponível na aba pontuação do currículo lattes da tela de visualização de projetos
    :param request:
    :param projeto_id:
    :return:
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if projeto.edital.is_periodo_antes_pre_selecao() and not projeto.data_avaliacao:
        url = request.META.get('HTTP_REFERER', '.')
        if projeto:
            # Atualiza a pontuação do currículo lattes, este normaliza e atualiza a pontuação total do projeto.
            projeto.atualizar_pontuacao_curriculo_lattes()
            if projeto.edital.peso_avaliacao_grupo_pesquisa:
                projeto.atualizar_pontuacao_grupo_pesquisa()
            return httprr(url, 'Atualização realizada com sucesso.')
    else:
        raise PermissionDenied


@permission_required('pesquisa.pode_interagir_com_projeto')
def atualizar_grupos_de_pesquisa(request):
    curriculo = get_object_or_404(CurriculoVittaeLattes, vinculo=request.user.get_vinculo())
    numero_identificador = curriculo.numero_identificador

    url = request.META.get('HTTP_REFERER', '.')

    instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')

    try:
        status = atualizar_grupos_pesquisa(curriculo.id)
        if status == 3:
            return httprr(url, 'Diretório dos grupos de pesquisa no Lattes em manutenção.', tag='error')

        if not curriculo.grupos_pesquisa.filter(instituicao=instituicao_sigla).exists():
            return httprr(
                url,
                mark_safe('Não há grupos de pesquisa vinculado ao {}. Consulte seu {}'.format(
                    instituicao_sigla, f'<a href="http://dgp.cnpq.br/dgp/espelhorh/{numero_identificador}"> Diretório dos Grupos de Pesquisa do Lattes. </a>'
                )),
                tag='error',
            )
    except Exception:
        return httprr(url, 'Diretório dos grupos de pesquisa no Lattes indisponível (off-line).', tag='error')
    # http://dgp.cnpq.br/dgp/espelhorh/3571057110440770.
    return httprr(url)


@rtr()
@permission_required('pesquisa.view_avaliadorexterno')
def listar_avaliadores(request):
    title = 'Listar Avaliadores Internos'
    avaliadores = Servidor.objects.filter(areas_de_conhecimento__isnull=False)
    form = AvaliadoresAreaConhecimentoForm(request.GET or None)
    if form.is_valid():
        area_conhecimento = form.cleaned_data['area_conhecimento']
        palavra_chave = form.cleaned_data['palavra_chave']
        uo = form.cleaned_data['uo']
        titulacao = form.cleaned_data['titulacao']
        situacao = form.cleaned_data['situacao']
        if situacao:
            if situacao == 'Ativos':
                avaliadores = Servidor.objects.ativos().filter(areas_de_conhecimento__isnull=False, excluido=False)
            else:
                avaliadores = Servidor.objects.inativos().filter(areas_de_conhecimento__isnull=False) | Servidor.objects.filter(areas_de_conhecimento__isnull=False, excluido=True)
        if area_conhecimento:
            area = AreaConhecimento.objects.filter(id=area_conhecimento.id)
            avaliadores = avaliadores.filter(areas_de_conhecimento__in=area.values_list('id', flat=True))
        if uo:
            avaliadores = avaliadores.filter(setor__uo__id=uo.id)
        if palavra_chave:
            avaliadores = avaliadores.filter(nome__icontains=palavra_chave)
        if titulacao:
            avaliadores = avaliadores.filter(titulacao=titulacao)

    avaliadores = avaliadores.distinct()
    if 'xls' in request.GET:
        return tasks.listar_avaliadores_export_to_xls(avaliadores)
    return locals()


@rtr()
@permission_required('pesquisa.pode_ver_equipe_projeto')
def listar_equipes_dos_projetos(request):
    title = 'Lista de Equipes dos Projetos'
    form = EquipeProjetoForm(data=request.GET or None)
    tipo_exibicao = 0  # Detalhado
    dados_do_projeto = []
    participacoes = None
    tem_permissao_propi = request.user.has_perm('pesquisa.tem_acesso_sistemico')
    if request.GET:

        if not (not request.GET.get('edital') and not request.GET.get('campus') and not request.GET.get('pessoa') and (request.GET.get('ano') == 'Selecione um ano')):
            projetos = Projeto.objects.filter(aprovado=True)
            if request.GET.get('ano'):
                projetos = projetos.filter(edital__inicio_inscricoes__year=request.GET.get('ano'))
            if request.GET.get('edital'):
                projetos = projetos.filter(edital=request.GET.get('edital'))

            if request.GET.get('campus'):
                projetos = projetos.filter(uo=request.GET.get('campus'))

            if request.GET.get('pessoa'):
                participacoes = Participacao.objects.filter(vinculo_pessoa=request.GET.get('pessoa'), projeto__aprovado=True)
                projetos = projetos.filter(participacao__in=participacoes)

            situacao = int(request.GET.get('situacao', 0))
            projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
            if situacao == 1:
                projetos = projetos.filter(registroconclusaoprojeto__dt_avaliacao__isnull=False).exclude(id__in=projetos_cancelados)

            elif situacao == 2:
                projetos = projetos.filter(registroconclusaoprojeto__dt_avaliacao__isnull=True).exclude(id__in=projetos_cancelados)

            tipo_exibicao = int(request.GET.get('tipo_de_exibicao', 0))
            if tipo_exibicao == 1:
                if not participacoes:
                    participacoes = Participacao.objects.filter(projeto__in=projetos, ativo=True).order_by('vinculo_pessoa__pessoa__nome')
                else:
                    participacoes = participacoes.filter(ativo=True).order_by('vinculo_pessoa__pessoa__nome')
                dados_do_projeto = get_lista_de_equipes(participacoes)

            if 'xls' in request.GET:
                return tasks.listar_equipes_dos_projetos_export_to_xls(projetos)

    return locals()


def get_lista_de_equipes(participacoes):
    lista = []
    pessoa_id_anterior = 0
    for participacao in participacoes:
        em_duplicidade = False
        if participacao.vinculo_pessoa and pessoa_id_anterior == participacao.vinculo_pessoa.id:
            em_duplicidade = True
            lista[-1]['em_duplicidade'] = True

        participante = participacao.get_participante()
        matricula = participacao.get_identificador()
        if participacao.ativo:
            ativo = 'Sim'
        else:
            ativo = 'Não'
        titulacao = participacao.get_titulacao()
        curso = ''
        lattes = ''
        if participacao.vinculo_pessoa and not participacao.vinculo_pessoa.eh_aluno():
            nome = participante.nome
        else:
            nome = participacao.get_nome()
            if participante:
                lattes = participante.pessoa_fisica.lattes
                curso = participante.curso_campus
        if participacao.responsavel:
            vinculo = 'Coordenador'
        else:
            vinculo = 'Membro'
        if participacao.vinculo == 'Bolsista' and participacao.bolsa_concedida:
            vinculo = vinculo + ' Bolsista'
        else:
            vinculo = vinculo + ' Não Bolsista'

        item = {
            'idprojeto': participacao.projeto.id,
            'projeto': participacao.projeto.titulo,
            'nome': nome,
            'lattes': lattes,
            'matricula': matricula,
            'vinculo': vinculo,
            'ativo': ativo,
            'titulacao': titulacao,
            'curso': curso,
            'edital': participacao.projeto.edital.titulo,
            'campus': participacao.projeto.uo.sigla,
            'ehcoordenador': participacao.responsavel,
            'em_duplicidade': em_duplicidade,
        }
        lista.append(item)
        pessoa_id_anterior = participacao.vinculo_pessoa.id
    return lista


@rtr()
@permission_required('pesquisa.view_comissaoeditalpesquisa')
def lista_emails_comissao(request, comissao_id):
    comissao = get_object_or_404(ComissaoEditalPesquisa, pk=comissao_id)
    title = 'Lista de Emails dos Membros da Comissão'

    emails = ''
    emails_avaliador = ''
    contador_avaliador = 0

    for contador, membro in enumerate(comissao.vinculos_membros.all(), 1):
        emails = emails + membro.pessoa.email + ';'
        if AvaliadorIndicado.objects.filter(vinculo=membro).exists():
            emails_avaliador = emails_avaliador + membro.pessoa.email + ';'
            contador_avaliador = contador_avaliador + 1
        if contador % 10:
            emails = emails + "\n"
        if contador_avaliador % 10:
            emails_avaliador = emails_avaliador + "\n"

    return locals()


@permission_required('pesquisa.add_origemrecursoedital')
def atualizar_curriculo_lattes(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    url = request.META.get('HTTP_REFERER', '.')
    return tasks.atualizar_curriculo_lattes(url, edital)


@permission_required('pesquisa.add_edital')
def gerenciar_bolsas_export_to_xls(request, projetos):
    return tasks.exportar_bolsas_para_xls(projetos)


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def cancelar_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not projeto.pode_cancelar_projeto():
        raise PermissionDenied()
    title = 'Cancelar Projeto'
    form = CancelarProjetoForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        o = form.save(False)
        o.projeto = projeto
        o.data_solicitacao = datetime.datetime.now()
        o.save()
        return httprr('..', 'Solicitação encaminhada para análise.')
    return locals()


@rtr()
@permission_required('pesquisa.view_edital')
def solicitacoes_de_cancelamento(request):
    title = 'Projetos com Solicitações de Cancelamento'
    projetos_cancelados = ProjetoCancelado.objects.filter(
        projeto__edital__tipo_edital__in=(Edital.PESQUISA, Edital.INOVACAO, Edital.PESQUISA_INOVACAO_CONTINUO), projeto__data_conclusao_planejamento__isnull=False
    )
    if request.user.groups.filter(name='Coordenador de Pesquisa').exists():
        projetos_cancelados = projetos_cancelados.filter(projeto__uo=get_uo(request.user))
    form = EditaisPesquisaForm(request.GET or None, request=request)
    if form.is_valid():
        if form.cleaned_data.get('edital'):
            projetos_cancelados = projetos_cancelados.filter(projeto__edital=form.cleaned_data["edital"])
        if form.cleaned_data.get('situacao'):
            if form.cleaned_data.get('situacao') == EditaisPesquisaForm.PENDENTES_ACEITE:
                projetos_cancelados = projetos_cancelados.filter(data_avaliacao__isnull=True)
            elif form.cleaned_data.get('situacao') == EditaisPesquisaForm.PENDENTES_VALIDACAO:
                projetos_cancelados = projetos_cancelados.filter(data_validacao__isnull=True, parecer_favoravel=True)
            elif form.cleaned_data.get('situacao') == EditaisPesquisaForm.PARECER_FAVORAVEL:
                projetos_cancelados = projetos_cancelados.filter(parecer_favoravel=True)
            elif form.cleaned_data.get('situacao') == EditaisPesquisaForm.VALIDADO:
                projetos_cancelados = projetos_cancelados.filter(cancelado=True, parecer_favoravel=True, data_validacao__isnull=False)
    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_cancelamento_projeto')
def avaliar_cancelamento_projeto(request, cancelamento_id):
    pedido_cancelamento = get_object_or_404(ProjetoCancelado, pk=cancelamento_id)
    title = 'Avaliar Cancelamento do Projeto'

    form = AvaliarCancelamentoProjetoForm(request.POST or None, instance=pedido_cancelamento)
    if form.is_valid():
        o = form.save(False)
        o.projeto = pedido_cancelamento.projeto
        o.data_avaliacao = datetime.datetime.now()
        o.avaliador = request.user.get_relacionamento()
        o.save()
        if o.cancelado == True:
            participantes = Participacao.ativos.filter(projeto=pedido_cancelamento.projeto, vinculo='Bolsista')
            for participante in participantes:
                if not participante.is_servidor():
                    participante.gerencia_bolsa_ae()

            if form.cleaned_data["aprova_proximo"] == True:
                if pedido_cancelamento.projeto.edital.forma_selecao == Edital.GERAL:
                    proximo_projeto = Projeto.objects.filter(edital=pedido_cancelamento.projeto.edital, aprovado=False).order_by('-pontuacao')
                else:
                    proximo_projeto = Projeto.objects.filter(edital=pedido_cancelamento.projeto.edital, uo=pedido_cancelamento.projeto.uo, aprovado=False).order_by('-pontuacao')

                if proximo_projeto.exists():
                    o.proximo_projeto = proximo_projeto[0]
                    o.save()
                    projeto = proximo_projeto[0]
                    projeto.aprovado = True
                    projeto.save()

                    responsavel = Participacao.objects.get(projeto__id=projeto.id, responsavel=True)
                    titulo = '[SUAP] Pesquisa: Aprovação de Projeto'
                    texto = '<h1>Pesquisa</h1>' '<h2>Aprovação de Projeto</h2>' '<p>O Projeto \'{}\' foi aprovado em decorrência de uma desistência.</p>'.format(projeto.titulo)
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [responsavel.vinculo_pessoa])

        return httprr('/pesquisa/solicitacoes_de_cancelamento/', 'Cancelamento avaliado com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def enviar_recurso(request, projeto_id):
    title = 'Enviar Recurso'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    if not projeto.pode_enviar_recurso():
        raise PermissionDenied()

    form = RecursoPesquisaForm(request.POST or None)
    if form.is_valid():
        o = form.save(False)
        o.projeto = projeto
        o.data_solicitacao = datetime.datetime.now()
        o.save()
        return httprr(f'/pesquisa/projeto/{projeto.id}', 'Recurso encaminhado para análise.')
    return locals()


@rtr()
@permission_required('pesquisa.add_edital')
def avaliar_recurso_projeto(request, recurso_id):
    projeto = get_object_or_404(RecursoProjeto, pk=recurso_id)
    title = 'Avaliar Recurso'
    form = AvaliarRecursoProjetoForm(request.POST or None, instance=projeto)
    if form.is_valid():
        o = form.save(False)
        o.projeto = projeto.projeto
        o.data_avaliacao = datetime.datetime.now()
        o.avaliador = request.user.get_relacionamento()
        o.save()

        return httprr('/pesquisa/solicitacoes_de_recurso/', 'Recurso avaliado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.add_origemrecursoedital')
def validar_recurso_projeto(request, recurso_id):
    projeto = get_object_or_404(RecursoProjeto, pk=recurso_id)
    title = 'Validar Recurso'
    form = ValidarRecursoProjetoForm(request.POST or None, instance=projeto)
    if form.is_valid():
        o = form.save(False)
        o.data_validacao = datetime.datetime.now()
        o.validador = request.user.get_relacionamento()
        o.save()
        if form.cleaned_data["aprovar_projeto"] == True:
            projeto.aprovado = True
            projeto.save()
        return httprr('/pesquisa/solicitacoes_de_recurso/', 'Recurso validado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.view_edital')
def solicitacoes_de_recurso(request):
    title = 'Projetos com Solicitações de Recurso'
    if request.user.groups.filter(name__in=['Diretor de Pesquisa', 'Auditor']):
        projetos_com_recurso = RecursoProjeto.objects.filter(
            projeto__edital__tipo_edital__in=(Edital.PESQUISA, Edital.INOVACAO, Edital.PESQUISA_INOVACAO_CONTINUO), projeto__data_conclusao_planejamento__isnull=False
        )
    else:
        projetos_com_recurso = RecursoProjeto.objects.filter(
            projeto__uo=get_uo(request.user), projeto__edital__tipo_edital__in=(Edital.PESQUISA, Edital.INOVACAO, Edital.PESQUISA_INOVACAO_CONTINUO)
        )
    form = EditaisPesquisaForm(request.GET or None, request=request)
    if form.is_valid():
        if form.is_valid():
            if form.cleaned_data.get('edital'):
                projetos_com_recurso = projetos_com_recurso.filter(projeto__edital=form.cleaned_data["edital"])
            if form.cleaned_data.get('situacao'):
                if form.cleaned_data.get('situacao') == EditaisPesquisaForm.PENDENTES_ACEITE:
                    projetos_com_recurso = projetos_com_recurso.filter(data_avaliacao__isnull=True)
                elif form.cleaned_data.get('situacao') == EditaisPesquisaForm.PENDENTES_VALIDACAO:
                    projetos_com_recurso = projetos_com_recurso.filter(data_validacao__isnull=True, parecer_favoravel=True)
                elif form.cleaned_data.get('situacao') == EditaisPesquisaForm.PARECER_FAVORAVEL:
                    projetos_com_recurso = projetos_com_recurso.filter(parecer_favoravel=True)
                elif form.cleaned_data.get('situacao') == EditaisPesquisaForm.VALIDADO:
                    projetos_com_recurso = projetos_com_recurso.filter(aceito=True, parecer_favoravel=True, data_validacao__isnull=False)

    return locals()


@rtr()
@permission_required('pesquisa.add_edital')
def recurso_projeto(request, recurso_id):
    recurso = get_object_or_404(RecursoProjeto, pk=recurso_id)
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def emitir_declaracao_avaliador(request):
    title = 'Declarações'
    projetos_avaliados = (
        Avaliacao.objects.filter(projeto__edital__tipo_edital__in=[Edital.PESQUISA, Edital.INOVACAO, Edital.PESQUISA_INOVACAO_CONTINUO], vinculo=request.user.get_vinculo())
        .values('projeto__edital__titulo', 'projeto__edital')
        .annotate(total=Count('projeto'))
        .order_by('-projeto__edital')
    )

    return locals()


@documento('Declaração de Avaliador', forcar_recriacao=True, enumerar_paginas=False, modelo='pesquisa.edital')
@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def emitir_declaracao_avaliador_pdf(request, pk):
    edital = get_object_or_404(Edital, pk=pk)
    vinculo = request.user.get_vinculo()
    nome = vinculo.pessoa.nome
    hoje = datetime.datetime.now()
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    meses = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
    mes = meses[hoje.month - 1]
    ano = edital.inicio_inscricoes.year
    projetos = Avaliacao.objects.filter(projeto__edital=edital, vinculo=vinculo).order_by('projeto__titulo')
    cidade = 'Natal'
    if projetos.exists():
        cidade = projetos[0].projeto.uo.municipio.nome
    projetos_avaliados = projetos.values('projeto__area_conhecimento', 'projeto__area_conhecimento__descricao').annotate(total=Count('projeto__area_conhecimento'))
    dados = []
    for projeto in projetos_avaliados:
        dados.append([projeto['projeto__area_conhecimento__descricao'], projeto['total']])

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def resultado_edital(request):
    title = 'Editais com Resultados Disponíveis'
    hoje = datetime.datetime.now()
    editais = Edital.objects.filter(divulgacao_selecao__lt=hoje, data_avaliacao_classificacao__isnull=False).order_by('-divulgacao_selecao')
    form = AnoForm(request.GET or None)
    if form.is_valid():
        if form.cleaned_data.get('ano') and form.cleaned_data.get('ano') != 'Selecione um ano':
            ano = int(form.cleaned_data['ano'])
            editais = editais.filter(inicio_inscricoes__year=ano)
    return locals()


@rtr("pesquisa/templates/distribuir_bolsas.html")
@permission_required('pesquisa.pode_interagir_com_projeto')
def resultado_edital_parcial(request):
    title = 'Editais com Resultados Parciais Disponíveis'
    hoje = datetime.datetime.now()
    editais = Edital.objects.filter(data_recurso__gte=hoje, divulgacao_selecao__gt=hoje, data_avaliacao_classificacao__isnull=False)
    edital_parcial = True
    return locals()


@rtr()
def divulgar_resultado_edital(self, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    tabela = {}
    resultado = {}
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    if edital.tem_formato_completo() and edital.pode_divulgar_resultado_pesquisa():

        if edital.forma_selecao == Edital.GERAL:
            projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True, aprovado=True).order_by('-pontuacao_total', '-pontuacao')
            tabela['Geral'] = []
            for projeto in projetos:
                tabela['Geral'].append(projeto)
        else:
            projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True, aprovado=True).order_by('uo__sigla', '-pontuacao_total', '-pontuacao')
            campi = projetos.values('uo__sigla', 'uo__nome').distinct()
            for campus in campi:
                chave = '{}'.format(campus['uo__nome'])
                tabela[chave] = []

            for projeto in projetos:
                chave = f'{projeto.uo.nome}'
                tabela[chave].append(projeto)

        resultado = collections.OrderedDict(sorted(tabela.items()))

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def divulgar_resultado_edital_parcial(request, edital_id, campus_id=None):
    title = 'Resultado Parcial'
    qtd_bolsa_pesquisador_distribuida = 0
    qtd_bolsa_ic_distribuida = 0
    qtd_bolsa_pesquisador_solicitada = 0
    qtd_bolsa_ic_solicitada = 0
    edital = get_object_or_404(Edital, pk=edital_id)
    if edital.tem_formato_completo():
        campus = None
        if edital.forma_selecao == Edital.GERAL:
            projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True).order_by('-pontuacao_total')
        else:
            campus = get_object_or_404(UnidadeOrganizacional, id=campus_id)
            projetos = Projeto.objects.filter(edital=edital, uo=campus, pre_aprovado=True).order_by('-pontuacao_total')
        if projetos:
            if edital.forma_selecao == Edital.CAMPUS and edital.bolsadisponivel_set.filter(uo=campus):
                qtd_bolsa_pesquisador = edital.bolsadisponivel_set.get(uo=campus).num_maximo_pesquisador
                qtd_bolsa_ic = edital.bolsadisponivel_set.get(uo=campus).num_maximo_ic
                participacoes = Participacao.objects.filter(projeto__in=projetos.values_list('id', flat=True)).order_by('vinculo')
            elif edital.forma_selecao == Edital.GERAL:
                qtd_bolsa_pesquisador = edital.qtd_bolsa_servidores
                qtd_bolsa_ic = edital.qtd_bolsa_alunos
                participacoes = Participacao.objects.filter(projeto__in=projetos.values_list('id', flat=True)).order_by('vinculo')
            for participacao in participacoes:
                if participacao.is_servidor():
                    if participacao.vinculo == TipoVinculo.BOLSISTA:
                        qtd_bolsa_pesquisador_solicitada = qtd_bolsa_pesquisador_solicitada + 1
                    if participacao.bolsa_concedida == True and participacao.vinculo == TipoVinculo.BOLSISTA:
                        qtd_bolsa_pesquisador_distribuida = qtd_bolsa_pesquisador_distribuida + 1
                else:
                    if participacao.vinculo == TipoVinculo.BOLSISTA:
                        qtd_bolsa_ic_solicitada = qtd_bolsa_ic_solicitada + 1
                    if participacao.bolsa_concedida == True and participacao.vinculo == TipoVinculo.BOLSISTA:
                        qtd_bolsa_ic_distribuida = qtd_bolsa_ic_distribuida + 1
            saldo_bolsa_pesquisador = qtd_bolsa_pesquisador - qtd_bolsa_pesquisador_distribuida
            saldo_bolsa_ic = qtd_bolsa_ic - qtd_bolsa_ic_distribuida
    return locals()


@documento('Declaração de Participação', enumerar_paginas=False, modelo='pesquisa.participacao', forcar_recriacao=True)
@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def emitir_declaracao_participacao_pdf(self, pk):
    participacao = get_object_or_404(Participacao, pk=pk)
    carga_horaria = participacao.carga_horaria
    participante = participacao.get_participante()
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    tipo_projeto = 'pesquisa'

    eh_aluno = False
    possui_bolsa = False
    if participacao.vinculo == TipoVinculo.BOLSISTA and participacao.bolsa_concedida:
        possui_bolsa = True

    eh_coordenador = False
    eh_externo = False
    if participacao.responsavel:
        eh_coordenador = True

    if participacao.is_servidor():
        nome = participante.nome
        cpf = participante.cpf
        rg = participante.rg
        rg_orgao = participante.rg_orgao
        rg_uf = participante.rg_uf
        if participacao.responsavel:
            vinculo = 'coordenador(a)'
        else:
            vinculo = 'membro'
        logradouro = participante.endereco_logradouro
        bairro = participante.endereco_bairro
        cidade = participante.endereco_municipio

    elif participacao.eh_aluno():  # participante é aluno
        eh_aluno = True
        nome = participacao.get_nome()
        cpf = participante.pessoa_fisica.cpf
        rg = participante.pessoa_fisica.rg
        rg_orgao = participante.pessoa_fisica.rg_orgao
        rg_uf = participante.pessoa_fisica.rg_uf
        logradouro = participante.logradouro
        bairro = participante.bairro
        cidade = participante.cidade

        vinculo = 'membro'
    else:
        eh_externo = True
        nome = participante.nome
        cpf = participante.prestador.cpf
        rg = participante.prestador.rg
        rg_orgao = participante.prestador.rg_orgao
        rg_uf = participante.prestador.rg_uf
        logradouro = participante.prestador.endereco_logradouro
        bairro = participante.prestador.endereco_bairro
        cidade = participante.prestador.endereco_municipio
        vinculo = 'membro'
    if participacao.historicoequipe_set.exists():
        if participacao.historicoequipe_set.first().data_movimentacao > participacao.projeto.inicio_execucao:
            data_inicio_vinculo = participacao.historicoequipe_set.first().data_movimentacao
        else:
            data_inicio_vinculo = participacao.projeto.inicio_execucao

        if not participacao.ativo and participacao.data_inativacao:
            data_fim_vinculo = participacao.data_inativacao
        elif not participacao.ativo and participacao.historicoequipe_set.filter(tipo_de_evento=HistoricoEquipe.EVENTO_INATIVAR_PARTICIPANTE).exists():
            data_fim_vinculo = participacao.historicoequipe_set.filter(tipo_de_evento=HistoricoEquipe.EVENTO_INATIVAR_PARTICIPANTE)[0].data_movimentacao
        else:
            if participacao.historicoequipe_set.last().data_movimentacao_saida:
                if participacao.historicoequipe_set.last().data_movimentacao_saida < participacao.projeto.fim_execucao:
                    data_fim_vinculo = participacao.historicoequipe_set.last().data_movimentacao_saida
                else:
                    data_fim_vinculo = participacao.projeto.fim_execucao
            else:
                data_fim_vinculo = participacao.projeto.fim_execucao

    else:
        data_inicio_vinculo = participacao.projeto.inicio_execucao
        data_fim_vinculo = participacao.projeto.fim_execucao

    matricula = None
    if participacao.eh_aluno() or participacao.is_servidor():
        matricula = participante.matricula

    hoje = datetime.datetime.now()
    meses = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
    mes = meses[hoje.month - 1]

    return locals()


@rtr()
@permission_required('pesquisa.add_origemrecursoedital')
def validar_cancelamento_projeto(request, projeto_id):
    pedido_cancelamento = get_object_or_404(ProjetoCancelado, pk=projeto_id)
    title = 'Validar Cancelamento'
    form = ValidarCancelamentoProjetoForm(request.POST or None, instance=pedido_cancelamento)
    if form.is_valid():
        o = form.save(False)
        o.data_validacao = datetime.datetime.now()
        o.validador = request.user.get_relacionamento()
        o.save()
        if o.cancelado == True:
            participantes = Participacao.ativos.filter(projeto=pedido_cancelamento.projeto, vinculo='Bolsista')
            for participante in participantes:
                if not participante.is_servidor():
                    participante.gerencia_bolsa_ae()

            if form.cleaned_data["aprova_proximo"] == True:
                if pedido_cancelamento.projeto.edital.forma_selecao == Edital.GERAL:
                    proximo_projeto = Projeto.objects.filter(edital=pedido_cancelamento.projeto.edital, aprovado=False).order_by('-pontuacao_total')
                else:
                    proximo_projeto = Projeto.objects.filter(edital=pedido_cancelamento.projeto.edital, uo=pedido_cancelamento.projeto.uo, aprovado=False).order_by(
                        '-pontuacao_total'
                    )

                if proximo_projeto.exists():
                    o.proximo_projeto = proximo_projeto[0]
                    o.save()
                    projeto = proximo_projeto[0]
                    projeto.aprovado = True
                    projeto.save()

                    responsavel = Participacao.objects.get(projeto__id=projeto.id, responsavel=True)
                    titulo = '[SUAP] Pesquisa: Aprovação de Projeto'
                    texto = '<h1>Pesquisa</h1>' '<h2>Aprovação de Projeto</h2>' '<p>O projeto \'{}\' foi aprovado em decorrência de uma desistência.</p>'.format(projeto.titulo)
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [responsavel.vinculo_pessoa])

        return httprr('/pesquisa/solicitacoes_de_cancelamento/', 'Solicitação de cancelamento validado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def deletar_participante(request, participacao_id):
    url = request.META.get('HTTP_REFERER', '.')
    participante = get_object_or_404(Participacao, pk=participacao_id)
    if not participante.projeto.is_coordenador(request.user) or not participante.pode_remover_participacao():
        raise PermissionDenied()
    if (
        Etapa.objects.filter(meta__projeto=participante.projeto, integrantes__in=[participante.id]).exists()
        or Etapa.objects.filter(meta__projeto=participante.projeto, responsavel=participante).exists()
    ):
        if Etapa.objects.filter(meta__projeto=participante.projeto, integrantes__in=[participante.id]).exists():
            etapa = Etapa.objects.filter(meta__projeto=participante.projeto, integrantes__in=[participante.id])[0]
            return httprr(url, f'O participante está vinculado à uma atividade e não pode ser removido. Meta: {etapa.meta.ordem} - Etapa: {etapa.ordem}', tag='error')
        else:
            etapa = Etapa.objects.filter(meta__projeto=participante.projeto, responsavel=participante)[0]
            return httprr(url, f'O participante é o responsável por uma atividade e não pode ser removido. Meta: {etapa.meta.ordem} - Etapa: {etapa.ordem}', tag='error')

    else:
        ProjetoAnexo.objects.filter(projeto=participante.projeto, vinculo_membro_equipe=participante.vinculo_pessoa).delete()
        participante.delete()
        return httprr(url, 'Participante removido com sucesso.')


@rtr()
@permission_required('pesquisa.add_edital')
def gerenciar_supervisores(request):
    title = 'Gerenciar Supervisores'
    editais_com_projetos_nao_encerrados = Projeto.objects.filter(data_finalizacao_conclusao__isnull=True, aprovado=True).values_list('edital__id', flat=True)
    editais = Edital.objects.filter(id__in=editais_com_projetos_nao_encerrados).order_by('-id')
    ano = request.GET.get('ano')
    form = GerenciarSupervisorForm(request.GET or None, ano=ano)
    if form.is_valid():
        edital = form.cleaned_data.get('edital')
        ano = form.cleaned_data.get('ano')
        if ano:
            editais = editais.filter(inicio_inscricoes__year=ano)
        if edital:
            editais = editais.filter(id=edital.id)

    return locals()


@rtr()
@permission_required('pesquisa.add_edital')
def selecionar_supervisor(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    title = f'Selecionar Supervisores - {edital.titulo}'
    if request.user.groups.filter(name='Diretor de Pesquisa'):
        projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True, aprovado=True)
    else:
        projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True, aprovado=True, uo=get_uo(request.user))

    participacoes = Participacao.objects.filter(projeto__in=projetos.values_list('id', flat=True), projeto__vinculo_supervisor__id=F('vinculo_pessoa__id'), projeto__aprovado=True)
    com_avaliador_externo = projetos.filter(vinculo_supervisor__in=AvaliadorExterno.objects.all().values_list('vinculo', flat=True))
    com_conflito = projetos.filter(id__in=participacoes.values_list('projeto', flat=True)).order_by('uo', 'titulo')
    projetos = com_conflito | com_avaliador_externo

    form = SupervisorForm(request.POST or None)
    if form.is_valid():
        palavra_chave = form.cleaned_data['palavra_chave']
        uo = form.cleaned_data['uo']
        situacao = form.cleaned_data.get('situacao')
        if situacao:
            if int(situacao) == 0:
                if request.user.has_perm('pesquisa.tem_acesso_sistemico'):
                    projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True, aprovado=True)
                else:
                    projetos = Projeto.objects.filter(edital=edital, pre_aprovado=True, aprovado=True, uo=get_uo(request.user))
        if uo:
            projetos = projetos.filter(uo__id=uo.id)

        if palavra_chave:
            projetos = projetos.filter(vinculo_supervisor__pessoa__nome__icontains=palavra_chave)

    return locals()


@rtr()
@permission_required('pesquisa.add_edital')
def selecionar_supervisor_do_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not projeto.uo == get_uo(request.user) and not request.user.has_perm('pesquisa.tem_acesso_sistemico'):
        return httprr(f'/pesquisa/selecionar_supervisor/{projeto.edital_id}/', 'Você só pode indicar supervisores para projetos do seu campus.', tag='error')

    title = 'Indicar Supervisor'
    grupo = Group.objects.get(name='Supervisor de Projetos de Pesquisa')

    form = AdicionarUsuarioGrupoForm(request.POST or None)
    if form.is_valid():
        for usuario in form.cleaned_data['user']:
            projeto.vinculo_supervisor = usuario.get_vinculo()
            usuario.groups.add(grupo)
            projeto.save()
        return httprr('..', 'Supervisor cadastrado com sucesso.')
    return locals()


@documento('Certificado de Participação', enumerar_paginas=False, modelo='pesquisa.participacao', forcar_recriacao=True)
@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def emitir_certificado_pdf(request, pk):
    participacao = get_object_or_404(Participacao, pk=pk)
    if not participacao.pode_emitir_certificado_de_participacao():
        return httprr('/', 'Você não tem permissão para este acesso.', 'error')
    else:
        nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
        nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
        hoje = datetime.datetime.now()
        meses = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
        mes = meses[hoje.month - 1]

        title = str(participacao.projeto)
        movimentacao = HistoricoEquipe.objects.filter(participante=pk).order_by('id')
        if movimentacao:
            como_coordenador = movimentacao.filter(categoria=HistoricoEquipe.COORDENADOR)
            como_membro = movimentacao.filter(categoria=HistoricoEquipe.MEMBRO)
            if movimentacao.filter(tipo_de_evento=HistoricoEquipe.EVENTO_INATIVAR_PARTICIPANTE).exists():
                data_inativacao = movimentacao.filter(tipo_de_evento=HistoricoEquipe.EVENTO_INATIVAR_PARTICIPANTE)[0].data_movimentacao
                como_coordenador = como_coordenador.exclude(data_movimentacao__gte=data_inativacao)
                como_membro = como_membro.exclude(data_movimentacao__gte=data_inativacao)

            if como_coordenador.exists() or como_membro.exists():
                return locals()
            else:
                return httprr(f'/pesquisa/projeto/{participacao.projeto_id}/', 'Não existe certificado disponível para este participante.', 'error')

        else:
            return httprr(f'/pesquisa/projeto/{participacao.projeto_id}/', 'Não existe movimentação para este participante.', 'error')


@documento('Declaração de Orientação', enumerar_paginas=False, modelo='pesquisa.participacao')
@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def emitir_declaracao_orientacao_pdf(request, pk):
    participacao = get_object_or_404(Participacao, pk=pk)
    if not participacao.pode_emitir_declaracao_orientacao():
        return httprr('/', 'Você não tem permissão para este acesso.', 'error')
    else:
        nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
        nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
        hoje = datetime.datetime.now()
        meses = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
        mes = meses[hoje.month - 1]

        title = str(participacao.projeto)
        participante = participacao.get_participante()
        nome = participante.nome
        matricula = participante.matricula
        cpf = participante.cpf
        rg = participante.rg
        rg_orgao = participante.rg_orgao
        rg_uf = participante.rg_uf
        vinculo = 'coordenador(a)'

        logradouro = participante.endereco_logradouro
        bairro = participante.endereco_bairro
        cidade = participante.endereco_municipio
        alunos = participacao.projeto.get_participacoes_alunos()
        if not alunos:
            return httprr('/', 'Não existem alunos neste projeto.', 'error')

    return locals()


@rtr()
@permission_required('pesquisa.view_edital')
def listar_projetos_em_atraso(request):
    title = 'Lista de Projetos em Atraso'
    form = ProjetosAtrasadosForm(request.GET or None, request=request)
    projetos = Projeto.objects.filter(pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, inativado=False).order_by('fim_execucao')
    if form.is_valid():
        situacao = form.cleaned_data.get('situacao')
        edital = form.cleaned_data.get('edital')
        ano = form.cleaned_data.get('ano')
        campus = form.cleaned_data.get('campus')
        if campus:
            projetos = projetos.filter(uo=campus)
        if ano:
            projetos = projetos.filter(edital__inicio_inscricoes__year=ano)
        if edital:
            projetos = projetos.filter(edital=edital)

        if situacao:
            hoje = datetime.datetime.now().date()
            if int(situacao) == 1:
                projetos = projetos.filter(fim_execucao__lt=hoje)
            elif int(situacao) == 2:
                etapas_atrasadas = Etapa.objects.filter(fim_execucao__lt=hoje, registroexecucaoetapa__isnull=True)
                projetos = projetos.filter(id__in=etapas_atrasadas.values_list('meta__projeto', flat=True))
            elif int(situacao) == 3:
                etapas_atrasadas = Etapa.objects.filter(fim_execucao__lt=hoje, registroexecucaoetapa__isnull=True)
                projetos = projetos.filter(fim_execucao__gte=hoje).exclude(id__in=etapas_atrasadas.values_list('meta__projeto', flat=True))

        if 'xls' in request.GET:
            return tasks.listar_projetos_em_atraso_export_to_xls(projetos)

    return locals()


@rtr()
@permission_required('pesquisa.tem_acesso_sistemico')
def cancelar_avaliacao_execucao_etapa(request, registro_id):
    title = 'Cancelar Avaliação de Execução de Etapa'
    registro = get_object_or_404(RegistroExecucaoEtapa, pk=registro_id)
    form = CancelarAvaliacaoEtapaForm(request.POST or None, instance=registro)
    if form.is_valid():
        o = form.save(False)
        o.avaliacao_cancelada_em = datetime.datetime.now()
        o.avaliacao_cancelada_por = request.user.get_relacionamento()
        o.dt_avaliacao = None
        o.avaliador = None
        o.aprovado = False
        o.save()
        return httprr(f'/pesquisa/validar_execucao_etapa/{registro.etapa.meta.projeto_id}/?tab=metas', 'Avaliação cancelada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.tem_acesso_sistemico')
def cancelar_avaliacao_execucao_gasto(request, registro_id):
    title = 'Cancelar Avaliação de Registro de Gasto'
    registro = get_object_or_404(RegistroGasto, pk=registro_id)
    form = CancelarAvaliacaoGastoForm(request.POST or None, instance=registro)
    if form.is_valid():
        o = form.save(False)
        o.avaliacao_cancelada_em = datetime.datetime.now()
        o.avaliacao_cancelada_por = request.user.get_relacionamento()
        o.dt_avaliacao = None
        o.avaliador = None
        o.aprovado = False
        o.justificativa_reprovacao = None
        o.save()
        return httprr(f'/pesquisa/validar_execucao_etapa/{registro.desembolso.projeto_id}/?tab=gastos', 'Avaliação cancelada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.add_origemrecursoedital, pesquisa.pode_ver_config_edital')
def relatorio_indicadores(request):
    title = 'Indicadores'
    form = IndicadoresForm(request.GET, request=request)
    form.is_valid()
    campus = form.cleaned_data.get('campus')
    indicador = form.cleaned_data.get('indicador')
    ano_inicio = form.cleaned_data.get('ano_inicio')
    ano_fim = form.cleaned_data.get('ano_fim')

    plot_options = {'series': {'dataLabels': {'enabled': True}}}
    grafico_opcao = {'plotOptions': plot_options}
    titulo_grafico = dict(form.INDICADORES_CHOICES)[indicador]

    titulo_box = list()
    titulo_box.append(dict(form.INDICADORES_CHOICES)[indicador])
    if campus:
        titulo_box.append(str(campus))
    if ano_inicio and ano_fim:
        titulo_box.append(f'{ano_inicio} a {ano_fim}')
    elif ano_inicio:
        titulo_box.append(f'a partir de {ano_inicio}')
    elif ano_fim:
        titulo_box.append(f'até {ano_fim}')
    titulo_box = ' - '.join(titulo_box)

    dados_numero_de_participante = Participacao.get_dados_quantitativos_de_participantes(campus, ano_inicio, ano_fim)
    dados_numero_de_participante = Relatorio.ordernar(dados_numero_de_participante)

    graficos = []
    graficos.append(ColumnChart('grafico1', title='Quantidade de Participante', minPointLength=3, data=dados_numero_de_participante, **grafico_opcao))

    return locals()


@rtr()
@permission_required('pesquisa.add_origemrecursoedital')
def refazer_distribuicao_bolsas(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    campus_id = request.GET.get('campus')
    if campus_id:
        oferta = get_object_or_404(BolsaDisponivel, uo=campus_id, edital=edital)
        oferta.data_avaliacao_classificacao = None
        oferta.save()
        return httprr(f'/pesquisa/gerenciar_bolsas/{edital_id}/{campus_id}/', 'Distribuição de Bolsas do campus refeita.')

    else:
        edital.data_avaliacao_classificacao = None
        edital.save()
        return httprr(f'/pesquisa/gerenciar_bolsas/{edital_id}/', 'Distribuição de Bolsas refeita.')


@rtr()
@permission_required('pesquisa.add_origemrecursoedital, pesquisa.pode_ver_config_edital')
def relatorio_quantitativo_docentes_por_campus(request):
    title = 'Quantitativo de Docentes por Campus'
    form = CampusForm(request.POST or None)
    tabela = {}
    uos = UnidadeOrganizacional.objects.uo().all().order_by('sigla')
    total = 0
    if form.is_valid():
        servidor = Servidor.objects.filter(data_exclusao_instituidor__isnull=True, excluido=False, eh_docente=True)
        if form.cleaned_data.get('uo'):
            uos = uos.filter(id=form.cleaned_data.get('uo').id)
        for uo in uos:
            chave = f'{uo.nome}'
            quantidade = servidor.filter(setor_lotacao__uo__equivalente=uo).count()
            tabela[chave] = quantidade
            total = total + quantidade

        resultado = collections.OrderedDict(sorted(tabela.items()))

    return locals()


@permission_required('pesquisa.pode_interagir_com_projeto')
def filtrar_editais_por_ano(request):
    data = []
    if request.method == 'GET':
        ano = request.GET.get('ano')
        if ano and ano != 'Selecione um ano':
            registro = Edital.objects.filter(inicio_inscricoes__year=ano).order_by('-inicio_inscricoes')
            if registro.exists():
                from django.core import serializers

                data = serializers.serialize('json', list(registro.all()), fields=('titulo', 'id'))
    return HttpResponse(data, content_type='application/json')


@permission_required('pesquisa.tem_acesso_sistemico')
def autorizar_edital(request, edital_id, opcao):
    edital = get_object_or_404(Edital, pk=edital_id)
    if request.user.groups.filter(name='Diretor de Pesquisa') and edital.autorizado is None:
        if opcao == '1':
            edital.autorizado = True
        elif opcao == '2':
            edital.autorizado = False

        edital.autorizado_por_vinculo = request.user.get_vinculo()
        edital.autorizado_em = datetime.datetime.now()
        edital.save()
        return httprr('/admin/pesquisa/edital/', 'Edital avaliado com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editais(request):
    title = 'Editais'
    editais = Edital.objects.all().order_by('-inicio_inscricoes')
    form = EditaisForm(request.GET or None)
    if form.is_valid():
        ano = form.cleaned_data.get('ano')
        uo = form.cleaned_data.get('uo')
        if ano and ano != 'Selecione um ano':
            editais = editais.filter(inicio_inscricoes__year=ano)
        if uo:
            editais = editais.filter(id__in=BolsaDisponivel.objects.filter(uo=uo).values_list('edital', flat=True))
        periodo = form.cleaned_data.get('periodo')
        if periodo:
            if periodo == EditaisForm.INSCRICAO:
                editais = editais.em_inscricao()
            elif periodo == EditaisForm.PRE_SELECAO:
                editais = editais.em_pre_avaliacao()
            elif periodo == EditaisForm.SELECAO:
                editais = editais.em_selecao()
            elif periodo == EditaisForm.EXECUCAO:
                editais = editais.em_execucao()
            elif periodo == EditaisForm.CONCLUIDO:
                editais = editais.concluidos()
        editais = editais.order_by('-inicio_inscricoes')

    return locals()


@rtr()
@permission_required('pesquisa.add_obra')
def editais_abertos_submissao_obra(request):
    title = 'Editais Abertos para Submissão de Obras'
    agora = datetime.datetime.now()
    editais = EditalSubmissaoObra.objects.filter(data_inicio_submissao__lte=agora, data_termino_submissao__gte=agora)

    return locals()


@rtr()
@permission_required('pesquisa.add_obra')
def submeter_obra(request, edital_id):
    edital = get_object_or_404(EditalSubmissaoObra, pk=edital_id)
    title = f'Submeter Obra: {edital.titulo}'
    instance = Obra()
    instance.edital = edital

    form = SubmeterObraForm(request.POST or None, request.FILES or None, instance=instance, request=request)
    if form.is_valid():
        o = form.save(False)
        if request.user.is_authenticated:
            o.submetido_por_vinculo = request.user.get_vinculo()
            if form.cleaned_data.get('eh_autor_organizador'):
                o.responsavel_vinculo = request.user.get_vinculo()
        o.submetido_em = datetime.datetime.now()
        o.save()

        return httprr(f'/pesquisa/obra/{form.instance.id}/', 'Obra submetida com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.add_obra')
def obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    title = f'Visualizar Obra: {obra.titulo}'
    edital = obra.edital
    vinculo = request.user.get_vinculo()
    pessoa_fisica = request.user.pessoafisica
    eh_autor = vinculo == obra.submetido_por_vinculo
    eh_sistemico = request.user.has_perm('pesquisa.add_linhaeditorial')
    eh_conselheiro = vinculo == obra.julgamento_conselho_realizado_por_vinculo
    eh_parecerista = ParecerObra.objects.filter(parecer_realizado_por_vinculo=vinculo, obra=obra, recusou_indicacao=False).exists()
    eh_revisor = vinculo == obra.revisao_realizada_por_vinculo
    eh_diagramador = vinculo == obra.diagramacao_realizada_por_vinculo
    eh_bibliotecario = request.user.groups.filter(name='Bibliotecário da Pesquisa').exists()
    pode_gerenciar_termos = (eh_autor and not obra.foi_assinada()) or request.user.has_perm('pesquisa.add_editalsubmissaoobra')
    autores = MembroObra.objects.filter(obra=obra)
    pode_ver_aba_conselho = eh_sistemico or eh_conselheiro or (eh_autor and obra.situacao_conselho_editorial == Obra.FAVORAVEL_COM_RESSALVAS)
    form = VerificaAutenticidadeForm(request.POST or None, instance=obra)
    aceiteform = AceiteEditoraForm(request.POST or None, instance=obra)
    uploadtermosform = UploadTermosForm(request.POST, request.FILES, instance=obra)
    publicacaoform = PublicacaoObraForm(request.POST or None, instance=obra, request=request)
    analiseliberacaoform = AnaliseLiberacaoForm(request.POST or None, instance=obra)
    if form.is_valid():
        o = form.save(False)
        o.autenticidade_verificada_por_vinculo = vinculo
        o.autenticidade_verificada_em = datetime.datetime.now()
        if form.cleaned_data.get('autentica') == obra.NAO:
            o.situacao = obra.CANCELADA
            o.cancelada_por_vinculo = vinculo
            o.cancelada_em = datetime.datetime.now()
        else:
            o.situacao = obra.AUTENTICA
        o.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=verificacao_autenticidade', 'Verificação de autenticidade realizada com sucesso.')

    if 'status_obra' in request.POST and aceiteform.is_valid():
        o = aceiteform.save(False)
        o.aceita_editora_realizada_por_vinculo = vinculo
        o.aceita_editora_realizada_em = datetime.datetime.now()
        if aceiteform.cleaned_data.get('status_obra') == Obra.HABILITADA:
            o.situacao = obra.ACEITA
        else:
            o.situacao = obra.CANCELADA
            o.cancelada_por_vinculo = vinculo
            o.cancelada_em = datetime.datetime.now()
        o.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=aceite', 'Avaliação da editora realizada com sucesso.')

    if (
        'termo_autorizacao_publicacao' in request.POST
        or 'termo_cessao_direitos_autorais' in request.POST
        or 'termo_uso_imagem' in request.POST
        or 'termo_nome_menor' in request.POST
        or 'contrato_cessao_direitos' in request.POST
        or 'termo_autorizacao_uso_imagem' in request.POST
    ) and uploadtermosform.is_valid():
        uploadtermosform.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=termos', 'Envio dos termos realizado com sucesso.')

    if ('situacao_publicacao' in request.POST or 'data_liberacao_repositorio_virtual' in request.POST) and publicacaoform.is_valid():
        o = publicacaoform.save(False)
        if o.situacao_publicacao == Obra.CATALOGADA:
            o.situacao = Obra.CORRIGIDA
        o.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=publicacao', 'Dados da publicação registrados com sucesso.')

    if 'aprovacao_liberacao_publicacao' in request.POST and analiseliberacaoform.is_valid():
        o = analiseliberacaoform.save(False)
        if analiseliberacaoform.cleaned_data.get('aprovacao_liberacao_publicacao') == Obra.SIM:
            o.situacao = obra.LIBERADA
        o.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=validacao_conselho', 'Análise da liberação da obra realizada com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.add_obra')
def minhas_obras(request):
    title = 'Minhas Obras'
    obras = Obra.objects.filter(submetido_por_vinculo=request.user.get_vinculo())
    return locals()


@rtr()
@permission_required('pesquisa.add_obra')
def adicionar_autor_obra(request, obra_id, vinculo_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.submetido_por_vinculo and obra.pode_cadastrar_autores():
        if vinculo_id == '1':
            titulo = 'Autor'
        elif vinculo_id == '2':
            titulo = 'Organizador'
        else:
            titulo = 'Coautor'
        title = f'Adicionar {titulo} - {obra.titulo}'
        form = MembroObraForm(request.POST or None)
        if form.is_valid():
            o = form.save(False)
            o.obra = obra
            if vinculo_id == '1':
                o.tipo_autor = MembroObra.AUTOR
            elif vinculo_id == '2':
                o.tipo_autor = MembroObra.ORGANIZADOR
            else:
                o.tipo_autor = MembroObra.COAUTOR
            o.save()
            return httprr(f'/pesquisa/obra/{obra.id}', 'Autor/Coautor cadastrado com sucesso.')

        return locals()

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_validar_obra, pesquisa.add_linhaeditorial')
def indicar_parecerista_obra(request, obra_id):
    title = 'Indicar Parecerista'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = IndicarPareceristaForm(request.POST or None)
    if form.is_valid():
        for usuario in form.cleaned_data['user']:
            if not ParecerObra.objects.filter(obra=obra, parecer_realizado_por_vinculo=usuario.get_vinculo()).exists():
                vinculo = usuario.get_vinculo()
                novo_parecerista = ParecerObra()
                novo_parecerista.obra = obra
                novo_parecerista.parecer_realizado_por_vinculo = vinculo
                novo_parecerista.indicado_em = datetime.datetime.now()
                novo_parecerista.save()

                titulo = '[SUAP] Pesquisa: Indicação de Parecerista de Obra'
                texto = (
                    '<h1>Pesquisa</h1>'
                    '<h2>Parecerista de Obra</h2>'
                    '<p>Você foi indicado como parecerista da Obra \'{0}\'.</p>'
                    '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo])
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=analise_parecerista', 'Parecerista indicado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_obra')
def parecerista_avaliar_obra(request, obra_id):
    title = 'Avaliar Obra'
    if request.user.get_vinculo().eh_servidor() and not request.user.get_relacionamento().areas_de_conhecimento.exists():
        return httprr('/pesquisa/tornar_avaliador/', 'Cadastre suas áreas de conhecimento antes de poder emitir parecer.')

    if request.user.get_vinculo().eh_prestador() and not AreaConhecimentoParecerista.objects.filter(parecerista=request.user.get_relacionamento()).exists():
        return httprr('/pesquisa/indicar_areas_conhecimento_de_interesse/', 'Cadastre suas áreas de conhecimento antes de poder emitir parecer.')

    obra = get_object_or_404(Obra, pk=obra_id)
    parecer = ParecerObra.objects.filter(parecer_realizado_por_vinculo=request.user.get_vinculo(), obra=obra)
    if parecer.exists() and obra.dentro_prazo_avaliar_obra() and not obra.julgamento_conselho_realizado_em:
        form = AvaliacaoPareceristaObraForm(request.POST or None, request.FILES or None, instance=parecer[0], initial={'nota': parecer[0].nota})
        if form.is_valid():
            o = form.save(False)
            o.parecer_realizado_em = datetime.datetime.now()
            o.save()
            titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
            texto = '''<h1>Pesquisa</h1>'
                        <h2>Submissão de Obra</h2>
                        <p>Prezado autor, Sua obra recebeu avaliação de um parecerista no SUAP. Ressaltamos que a avaliação de um parecerista não corresponde à avaliação geral da obra,
                        já que a Editora IFRN juntamente com o seu Conselho Editorial se responsabilizam pela publicação do resultado final,
                        após reunir todos as notas emitidas por, pelo menos, 02 pareceristas sobre sua obra,
                        sendo publicado no portal do IFRN em data estabelecida em edital quando todas as obras submetidas para análise forem avaliadas.
                        Caso a obra tenha sido aprovada com ressalvas pelo parecerista, será necessário o reenvio da obra contemplando as sugestões do parecerista.</p>
                        <p>Para mais informações, acesse: <a href="{0}/pesquisa/obra/{1}/">{0}/pesquisa/obra/{1}/</a></p>'''.format(settings.SITE_URL, obra.id)

            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=analise_parecerista', 'Parecer salvo com sucesso.')

        return locals()

    raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_obra')
def reenviar_obra(request, obra_id):
    title = 'Reenviar Obra'
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.submetido_por_vinculo:
        form = ReenviarObraForm(request.POST or None, request.FILES or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.situacao_conselho_editorial = None
            o.obs_conselho_editorial = None
            o.julgamento_conselho_realizado_em = None
            o.save()
            titulo = '[SUAP] Pesquisa: Conselheiro Editorial'
            texto = (
                '<h1>Pesquisa</h1>'
                '<h2>Conselheiro Editorial</h2>'
                '<p>O autor da Obra \'{0}\' enviou a versão corrigida para receber seu parecer. Acesse o SUAP para mais detalhes.</p>'
                '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
            )

            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.julgamento_conselho_realizado_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=validacao_conselho', 'Obra reenviada com sucesso.')
        return locals()
    raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def indicar_conselheiro_obra(request, obra_id):
    title = 'Indicar Conselheiro'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = IndicarConselheiroForm(request.POST or None)
    if form.is_valid():
        for usuario in form.cleaned_data['user']:
            obra.julgamento_conselho_realizado_por_vinculo = usuario.get_vinculo()
        obra.save()

        titulo = '[SUAP] Pesquisa: Indicação de Conselheiro Editorial'
        texto = (
            '<h1>Pesquisa</h1>'
            '<h2>Conselheiro Editorial de obra</h2>'
            '<p>Você foi indicado como conselheiro editorial da Obra \'{0}\'.</p>'
            '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'
            ''.format(obra.titulo, settings.SITE_URL, obra.id)
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.julgamento_conselho_realizado_por_vinculo])

        return httprr(f'/pesquisa/obra/{obra.id}/?tab=validacao_conselho', 'Conselheiro indicado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_validar_obra, pesquisa.add_linhaeditorial')
def registrar_posicao_conselho_obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    title = 'Emitir Parecer'
    if request.user.get_vinculo() == obra.julgamento_conselho_realizado_por_vinculo or request.user.has_perm('pesquisa.add_linhaeditorial'):
        form = AvaliacaoConselhoEditorialForm(request.POST or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.julgamento_conselho_realizado_em = datetime.datetime.now()
            if o.situacao_conselho_editorial == Obra.FAVORAVEL:
                situacao = 'foi aceita'
                o.situacao = Obra.VALIDADA
            elif o.situacao_conselho_editorial == Obra.FAVORAVEL_COM_RESSALVAS:
                situacao = 'foi aceita com ressalvas'
            else:
                situacao = 'não foi aceita'
                o.situacao = Obra.CANCELADA
                o.cancelada_por_vinculo = request.user.get_vinculo()
                o.cancelada_em = datetime.datetime.now()
            o.save()
            titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
            texto = (
                '<h1>Pesquisa</h1><h2>Submissão de Obra</h2><p>O pedido de publicação da obra \'{0}\' {1} pelo conselho editorial. Caso tenha sido aprovada com ressalvas, é necessário o reenvio da obra corrigida.</p>'
                '<p>Para mais informações, acesse: <a href="{2}/pesquisa/obra/{3}/">{2}/pesquisa/obra/{3}/</a></p>'.format(obra.titulo, situacao, settings.SITE_URL, obra.id)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=validacao_conselho', 'Parecer registrado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def indicar_revisor_obra(request, obra_id):
    title = 'Indicar Revisor'
    obra = get_object_or_404(Obra, pk=obra_id)
    if obra.dentro_prazo_revisao():
        form = IndicarRevisorForm(request.POST or None)
        if form.is_valid():
            for usuario in form.cleaned_data['user']:
                obra.revisao_realizada_por_vinculo = usuario.get_vinculo()
            obra.save()

            titulo = '[SUAP] Pesquisa: Indicação de Revisor de Obra'
            texto = (
                '<h1>Pesquisa</h1>'
                '<h2>Revisor de obra</h2>'
                '<p>Você foi indicado como revisor da Obra \'{0}\'.</p>'
                '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.revisao_realizada_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=revisao_textual', 'Revisor indicado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_revisar_obra')
def revisar_obra(request, obra_id):
    title = 'Revisar Obra'
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.revisao_realizada_por_vinculo and obra.dentro_prazo_revisao():
        form = RevisarObraForm(request.POST or None, request.FILES or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.revisao_realizada_em = datetime.datetime.now()
            o.save()
            titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
            texto = (
                '<h1>Pesquisa</h1><h2>Submissão de Obra</h2><p>O pedido de publicação da obra \'{0}\' foi revisada.</p>'
                '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=revisao_textual', 'Revisão salva com sucesso.')
        return locals()
    raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_obra')
def enviar_arquivo_corrigido(request, obra_id):
    title = 'Enviar Revisão do Autor'
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.submetido_por_vinculo and obra.dentro_prazo_revisao():
        form = RevisarAutorForm(request.POST or None, request.FILES or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.correcoes_enviadas_em = datetime.datetime.now()
            o.save()
            titulo = '[SUAP] Pesquisa: Versão Revisada de Obra'
            texto = (
                '<h1>Pesquisa</h1>'
                '<h2>Revisor de obra</h2>'
                '<p>O autor da Obra \'{0}\' enviou a versão revisada.</p>'
                '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.revisao_realizada_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=revisao_textual', 'Correções enviadas com sucesso.')
        return locals()
    raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_revisar_obra')
def revisor_emitir_parecer(request, obra_id):
    title = 'Emitir Parecer da Revisão'
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.revisao_realizada_por_vinculo and obra.dentro_prazo_revisao():
        form = EmitirParecerRevisaoObraForm(request.POST or None, request.FILES or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.situacao = Obra.REVISADA
            o.versao_final_revisao_em = datetime.datetime.now()
            o.save()
            titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
            texto = (
                '<h1>Pesquisa</h1><h2>Submissão de Obra</h2><p>O parecer final do revisor da obra \'{0}\' foi cadastrado.</p>'
                '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=revisao_textual', 'Parecer salvo com sucesso.')
        return locals()


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def indicar_diagramador_obra(request, obra_id):
    title = 'Indicar Diagramador'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = IndicarDiagramadorForm(request.POST or None)
    if form.is_valid():
        for usuario in form.cleaned_data['user']:
            obra.diagramacao_realizada_por_vinculo = usuario.get_vinculo()
        obra.save()

        titulo = '[SUAP] Pesquisa: Indicação de Diagramador de obra'
        texto = (
            '<h1>Pesquisa</h1>'
            '<h2>Diagramador de obra</h2>'
            '<p>Você foi indicado como diagramador da Obra \'{0}\'</p>.'
            '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.diagramacao_realizada_por_vinculo])
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=diagramacao', 'Diagramador indicado com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.add_obra')
def avaliar_diagramacao(request, obra_id):
    title = 'Avaliar Diagramação'
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.submetido_por_vinculo:
        form = AvaliacaoDiagramacaoForm(request.POST or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.diagramacao_avaliada_em = datetime.datetime.now()
            o.save()
            titulo = '[SUAP] Notificação sobre Diagramação de Obra'
            texto = (
                '<h1>Pesquisa</h1><h2>Diagramação de Obra</h2><p>A diagramação da obra \'{0}\' foi avaliada pelo autor.</p>'
                '<p>Para mais informações, acesse: <a href="{1}/pesquisa/obra/{2}/">{1}/pesquisa/obra/{2}/</a></p>'.format(obra.titulo, settings.SITE_URL, obra.id)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.diagramacao_realizada_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=diagramacao', 'Diagramação avaliada com sucesso.')
        return locals()
    raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_diagramar_obra')
def cadastrar_diagramacao(request, obra_id):
    title = 'Cadastrar Diagramação'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = CadastrarDiagramacaoObraForm(request.POST or None, request.FILES or None, instance=obra)
    if form.is_valid():
        o = form.save(False)
        if obra.diagramacao_avaliada_em:
            obra.situacao = Obra.CORRIGIDA
            obra.diagramacao_concluida = True
        else:
            obra.situacao = Obra.DIAGRAMADA
        o.save()
        titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
        texto = f'<h1>Pesquisa</h1><h2>Submissão de Obra</h2><p>A diagramação da obra \'{obra.titulo}\' foi cadastrada. Por favor, acesse o SUAP para mais detalhes.</p>'
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=diagramacao', 'Diagramação cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def cadastrar_isbn(request, obra_id):
    title = 'Cadastrar ISBN'
    obra = get_object_or_404(Obra, pk=obra_id)
    if obra.eh_periodo_pedido_isbn():
        form = CadastrarISBNObraForm(request.POST or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.situacao = Obra.REGISTRADA_ISBN
            o.save()
            titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
            texto = f'<h1>Pesquisa</h1><h2>Submissão de Obra</h2><p>O ISBN da obra \'{obra.titulo}\' foi cadastrado. Por favor, acesse o SUAP para mais detalhes.</p>'
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=cadastro_isbn', 'ISBN cadastrado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_obra')
def registrar_conclusao_obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    if request.user.get_vinculo() == obra.submetido_por_vinculo:
        obra.situacao = Obra.CONCLUIDA
        obra.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=publicacao', 'Publicação de obra concluída com sucesso.')
    raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def cancelar_obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    if not obra.situacao == obra.CONCLUIDA:
        if not obra.situacao == obra.CANCELADA:
            title = f'Justificar Cancelamento - {obra}'
            form = CancelamentoObraForm(request.POST or None, instance=obra)
            if form.is_valid():
                o = form.save(False)
                o.situacao = obra.CANCELADA
                o.cancelada_por_vinculo = request.user.get_vinculo()
                o.cancelada_em = datetime.datetime.now()
                o.save()
                return httprr(f'/pesquisa/obra/{obra.id}/', 'Obra cancelada com sucesso.')
        else:
            obra.situacao = obra.SUBMETIDA
            obra.cancelada_por_vinculo = None
            obra.cancelada_em = None
            obra.justificativa_cancelamento = None
            obra.save()
            return httprr(f'/pesquisa/obra/{obra.id}/', 'Cancelamento revertido com sucesso.')
        return locals()

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_gerar_ficha_catalografica')
def cadastrar_ficha_catalografica(request, obra_id):
    title = 'Cadastrar Ficha Catalográfica'
    obra = get_object_or_404(Obra, pk=obra_id)
    if obra.eh_ativa():
        form = FichaCatalograficaForm(request.POST or None, request.FILES or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.situacao = Obra.CATALOGADA
            o.save()
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=ficha_catalografica', 'Ficha catalográfica cadastrada com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def concluir_obra(request, obra_id):
    title = 'Concluir Publicação de Obra'
    obra = get_object_or_404(Obra, pk=obra_id)
    if obra.situacao == obra.LIBERADA:
        form = ConclusaoObraForm(request.POST or None, request.FILES or None, instance=obra)
        if form.is_valid():
            o = form.save(False)
            o.situacao = Obra.CONCLUIDA
            o.obra_concluida_em = datetime.datetime.now()
            o.save()
            return httprr(f'/pesquisa/obra/{obra.id}/?tab=conclusao', 'Obra concluída com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def checklist_obra(request, obra_id):
    title = 'Checklist'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = ChecklistObraForm(request.POST or None, instance=obra)
    if form.is_valid():
        form.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=conclusao', 'Checklist salvo com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def checklist_obra_diagramador(request, obra_id):
    title = 'Checklist'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = ChecklistObraDiagramadorForm(request.POST or None, instance=obra)
    if form.is_valid():
        form.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=diagramacao', 'Checklist salvo com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def validar_termos(request, obra_id):
    title = 'Validar os Termos'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = TermoAssinadoForm(request.POST or None, instance=obra)
    if form.is_valid():
        o = form.save(False)
        o.termos_assinados_realizado_por_vinculo = request.user.get_vinculo()
        o.termos_assinados_realizado_em = datetime.datetime.now()
        o.save()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=termos', 'Termos validados com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.view_edital')
def estatisticas(request):
    projetos = Projeto.objects.all()
    if not request.user.has_perm('pesquisa.add_origemrecursoedital') and not request.user.has_perm('pesquisa.pode_ver_config_edital'):
        campus_do_usuario = get_uo(request.user)
        projetos = projetos.filter(uo=campus_do_usuario)
        title = f'Estatísticas dos Projetos de Pesquisa - Campus {campus_do_usuario}'
    else:
        title = 'Estatísticas dos Projetos de Pesquisa'
    ano = request.GET.get('ano')
    form = EstatisticasForm(request.GET or None, ano=ano, request=request)
    if form.is_valid():
        edital = form.cleaned_data.get('edital')
        formato_edital = form.cleaned_data.get('formato_edital')
        campus = form.cleaned_data.get('campus')
        ano = form.cleaned_data.get('ano')
        grupo_pesquisa = form.cleaned_data.get('grupo_pesquisa')
        situacao = form.cleaned_data.get('situacao')

        if ano:
            projetos = projetos.filter(edital__inicio_inscricoes__year=ano)
        if edital:
            projetos = projetos.filter(edital=edital)
        if campus:
            projetos = projetos.filter(uo=campus)
        if grupo_pesquisa:
            projetos = projetos.filter(grupo_pesquisa=grupo_pesquisa)

        if formato_edital:
            projetos = projetos.filter(edital__formato=formato_edital)

        hoje = datetime.datetime.now()
        enviados = projetos.filter(Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False))
        projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True, data_avaliacao__isnull=False).values_list('projeto', flat=True)
        aprovados = enviados.filter(aprovado=True, edital__divulgacao_selecao__lt=hoje) | enviados.filter(aprovado=True, edital__formato=Edital.FORMATO_SIMPLIFICADO)
        execucao = aprovados.filter(
            pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, edital__divulgacao_selecao__lt=hoje, inativado=False
        ).exclude(id__in=projetos_cancelados)
        concluidos = aprovados.filter(registroconclusaoprojeto__dt_avaliacao__isnull=False)
        cancelados = aprovados.filter(id__in=projetos_cancelados)
        inativados = aprovados.filter(inativado=True)
        dados = list()
        dados.append(['Projetos em Execução', execucao.count()])
        dados.append(['Projetos Concluídos', concluidos.count()])
        dados.append(['Projetos Cancelados', cancelados.count()])
        dados.append(['Projetos Inativados', inativados.count()])
        grafico = PieChart(
            'grafico', title='Situação Atual dos Projetos Aprovados', subtitle='Quantidade de projetos aprovados em execução, concluídos e cancelados', minPointLength=0, data=dados
        )

        setattr(grafico, 'id', 'grafico')

        if situacao != 'Todos':
            titulo = situacao
            if situacao == EstatisticasForm.PROJETOS_ENVIADOS:
                queryset_para_graficos = enviados
            elif situacao == EstatisticasForm.PROJETOS_PRE_SELECIONADOS:
                queryset_para_graficos = enviados.filter(pre_aprovado=True)
            elif situacao == EstatisticasForm.PROJETOS_APROVADOS:
                queryset_para_graficos = aprovados
            elif situacao == EstatisticasForm.PROJETOS_EM_EXECUCAO:
                queryset_para_graficos = execucao
            elif situacao == EstatisticasForm.PROJETOS_CONCLUIDOS:
                queryset_para_graficos = concluidos
            elif situacao == EstatisticasForm.PROJETOS_CANCELADOS:
                queryset_para_graficos = cancelados
            elif situacao == EstatisticasForm.PROJETOS_INATIVADOS:
                queryset_para_graficos = inativados
        else:
            queryset_para_graficos = enviados
            titulo = 'Projetos Enviados'

        dados2 = list()
        for area in AreaConhecimento.objects.filter(superior__isnull=False):
            valor = queryset_para_graficos.filter(area_conhecimento=area).count()
            if valor:
                dados2.append([area.descricao, valor])

        grafico2 = PieChart(
            'grafico2', title=f'{titulo} por Área de Conhecimento', subtitle='Quantidade de projetos por área de conhecimento', minPointLength=0, data=dados2
        )

        setattr(grafico2, 'id', 'grafico2')

        dados3 = list()
        participacoes = Participacao.objects.filter(projeto__in=queryset_para_graficos.values_list('id')).distinct()
        alunos = Aluno.objects.filter(vinculos__in=participacoes.values_list('vinculo_pessoa_id')).distinct()
        docentes = Servidor.objects.filter(excluido=False, vinculos__in=participacoes.values_list('vinculo_pessoa_id'), eh_docente=True).distinct()
        tecnicos_adm = Servidor.objects.filter(excluido=False, id__in=participacoes.values_list('vinculo_pessoa_id'), eh_tecnico_administrativo=True).distinct()
        dados3.append(['Discentes', alunos.count()])
        dados3.append(['Docentes', docentes.count()])
        dados3.append(['Técnicos Administrativos', tecnicos_adm.count()])

        grafico3 = PieChart(
            'grafico3',
            title=f'Participantes em {titulo} por Categoria',
            subtitle='Quantidade de discentes, téc. administrativos e docentes únicos envolvidos',
            minPointLength=0,
            data=dados3,
        )

        setattr(grafico3, 'id', 'grafico3')

        bolsistas = Participacao.objects.filter(vinculo="Bolsista", projeto__in=queryset_para_graficos.values_list('id')).distinct()
        voluntarios = Participacao.objects.filter(vinculo="Voluntário", projeto__in=queryset_para_graficos.values_list('id')).distinct()

        alunos_bolsistas = Aluno.objects.filter(vinculos__in=bolsistas.values_list('vinculo_pessoa_id')).distinct().count()
        alunos_voluntarios = Aluno.objects.filter(vinculos__in=voluntarios.values_list('vinculo_pessoa_id')).distinct().count()
        docentes_bolsistas = Servidor.objects.filter(excluido=False, vinculos__in=bolsistas.values_list('vinculo_pessoa_id'), eh_docente=True).distinct().count()
        docentes_voluntarios = Servidor.objects.filter(excluido=False, vinculos__in=voluntarios.values_list('vinculo_pessoa_id'), eh_docente=True).distinct().count()
        tecnicos_adm_bolsistas = Servidor.objects.filter(excluido=False, vinculos__in=bolsistas.values_list('vinculo_pessoa_id'), eh_tecnico_administrativo=True).distinct().count()
        tecnicos_adm_voluntarios = (
            Servidor.objects.filter(excluido=False, vinculos__in=voluntarios.values_list('vinculo_pessoa_id'), eh_tecnico_administrativo=True).distinct().count()
        )

        series2 = []
        serie = ['Discentes']
        serie.append(alunos_bolsistas)
        serie.append(alunos_voluntarios)
        series2.append(serie)

        serie = ['Docentes']
        serie.append(docentes_bolsistas)
        serie.append(docentes_voluntarios)
        series2.append(serie)

        serie = ['Técnicos Administrativos']
        serie.append(tecnicos_adm_bolsistas)
        serie.append(tecnicos_adm_voluntarios)
        series2.append(serie)

        groups = []
        for tipo in ['Bolsistas', 'Voluntários']:
            groups.append(tipo)

        grafico4 = GroupedColumnChart(
            'grafico4',
            title=f'Tipo de Vínculo por Categoria em {titulo}',
            subtitle='Quantidade de bolsistas e voluntários por categoria',
            data=series2,
            groups=groups,
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
        )

        setattr(grafico4, 'id', 'grafico4')

        dados5 = list()
        for modalidade in Modalidade.objects.all():
            valor = alunos.filter(curso_campus__modalidade=modalidade).count()
            if valor > 0:
                dados5.append([modalidade.descricao, valor])

        grafico5 = PieChart(
            'grafico5',
            title=f'Discentes por Modalidade de Ensino em {titulo}',
            subtitle='Quantidade de discentes classificados por modalidade de ensino',
            minPointLength=0,
            data=dados5,
        )

        setattr(grafico5, 'id', 'grafico5')

        pie_chart_lists = [grafico, grafico2, grafico3, grafico4, grafico5]

    return locals()


@rtr()
@permission_required('pesquisa.pode_validar_obra')
def remover_parecerista(request, parecerobra_id):
    parecer = get_object_or_404(ParecerObra, pk=parecerobra_id)
    obra = parecer.obra
    eh_conselheiro = request.user.get_vinculo() == obra.julgamento_conselho_realizado_por_vinculo
    if eh_conselheiro:
        parecer.delete()
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=analise_parecerista', 'Parecerista removido com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.view_edital')
def relatorio_dimensao(request):
    # ----------------------------------------------------
    quantidade_projetos = list()
    quantidade_participantes = list()
    participantes_por_area_conhecimento = list()
    # ----------------------------------------------------
    escolheu_ano = False
    form = RelatorioDimensaoForm(data=request.GET or None, request=request)
    soma_total = 0
    soma_aprovados = 0
    soma_concluidos = 0

    if request.user.groups.filter(name='Coordenador de Pesquisa'):
        campus_relatorio = get_uo(request.user)
    else:
        campus_relatorio = None
    hoje = datetime.datetime.now()
    if form.is_valid():

        if form.cleaned_data.get('ano') and form.cleaned_data.get('ano') != 'Selecione um ano':
            ano = int(form.cleaned_data['ano'])
            escolheu_ano = True
            ppg = form.cleaned_data.get('ppg')
            formato = form.cleaned_data['formato_edital']
            if form.cleaned_data.get('campus'):
                campus_escolhido = form.cleaned_data.get('campus')
                campus_relatorio = get_object_or_404(UnidadeOrganizacional, pk=campus_escolhido.id)
            if campus_relatorio:
                editais_tem_oferta = BolsaDisponivel.objects.filter(uo=campus_relatorio).values_list('edital', flat=True)
                editais = Edital.objects.filter(inicio_inscricoes__year=ano, id__in=editais_tem_oferta)
                editais = editais.filter(
                    id__in=Projeto.objects.filter(Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False))
                    .filter(uo=campus_relatorio)
                    .values_list('edital', flat=True)
                ).order_by('inicio_inscricoes')
            else:
                editais = Edital.objects.filter(inicio_inscricoes__year=ano).order_by('inicio_inscricoes')

            if formato == Edital.FORMATO_COMPLETO:
                editais = editais.filter(formato=Edital.FORMATO_COMPLETO)
            elif formato == Edital.FORMATO_SIMPLIFICADO:
                editais = editais.filter(formato=Edital.FORMATO_SIMPLIFICADO)

            total_membros_edital_geral = 0
            total_membros_edital_alunos_bolsistas = 0
            total_membros_edital_alunos_voluntarios = 0
            total_membros_edital_docentes_bolsistas = 0
            total_membros_edital_docentes_voluntarios = 0
            total_membros_edital_tecnicos_adm_bolsistas = 0
            total_membros_edital_tecnicos_adm_voluntarios = 0

            area_tematica_total_docente_bols = 0
            area_tematica_total_docente_vol = 0
            area_tematica_total_tec_adm_bols = 0
            area_tematica_total_tec_adm_vol = 0
            area_tematica_total_aluno_bols = 0
            area_tematica_total_aluno_vol = 0
            area_tematica_total_geral = 0

            soma_areas_total = {}
            soma_areas_aprovados = {}
            lista_qtd = dict()
            lista_total = list()
            areas = list()
            for area in AreaConhecimento.objects.filter(superior__isnull=False).order_by('descricao'):
                tem_a_area = Projeto.objects.filter(edital__in=editais.values_list('id', flat=True), area_conhecimento=area)
                if ppg:
                    tem_a_area = tem_a_area.filter(ppg=ppg)

                tem_a_area = tem_a_area.filter(Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False))
                if campus_relatorio:
                    tem_a_area = tem_a_area.filter(uo=campus_relatorio)
                if tem_a_area.exists():
                    areas.append(area.descricao)

            for edital in editais.order_by('titulo'):
                areas_total = {}
                areas_aprovados = {}

                # ----------------------------------------------------
                if campus_relatorio:
                    projetos_por_edital_total = Projeto.objects.filter(edital=edital, uo=campus_relatorio)
                else:
                    projetos_por_edital_total = Projeto.objects.filter(edital=edital)
                if ppg:
                    projetos_por_edital_total = projetos_por_edital_total.filter(ppg=ppg)
                projetos_por_edital_total = projetos_por_edital_total.filter(
                    Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False)
                )
                projetos_por_edital_aprovados = projetos_por_edital_total.filter(aprovado=True, edital__divulgacao_selecao__lt=hoje)
                projetos_por_edital_concluidos = projetos_por_edital_aprovados.filter(registroconclusaoprojeto__dt_avaliacao__isnull=False)
                soma_total = soma_total + projetos_por_edital_total.count()
                soma_aprovados = soma_aprovados + projetos_por_edital_aprovados.count()
                soma_concluidos = soma_concluidos + projetos_por_edital_concluidos.count()
                # ----------------------------------------------------
                lista_qtd[edital.titulo] = dict(valores=list())
                for area in AreaConhecimento.objects.filter(superior__isnull=False).order_by('descricao'):
                    if area.descricao in areas:
                        lista_qtd[edital.titulo]['valores'].append(projetos_por_edital_total.filter(area_conhecimento=area).count())
                        lista_qtd[edital.titulo]['valores'].append(projetos_por_edital_aprovados.filter(area_conhecimento=area).count())
                lista_qtd = collections.OrderedDict(sorted(lista_qtd.items()))
                percentual = 0
                projetos_aprovados = projetos_por_edital_aprovados.count()
                if projetos_aprovados:
                    percentual = ((Decimal(projetos_por_edital_concluidos.count()).quantize(10 ** 2) / Decimal(projetos_aprovados).quantize(10 ** 2)) * 100).quantize(10 ** 2)

                quantidade_projetos.append(
                    dict(
                        edital=edital,
                        total=projetos_por_edital_total.count(),
                        aprovados=projetos_aprovados,
                        concluidos=projetos_por_edital_concluidos.count(),
                        percentual=percentual,
                    )
                )
                # ----------------------------------------------------

                bolsistas = Participacao.objects.filter(vinculo="Bolsista", bolsa_concedida=True, projeto__in=projetos_por_edital_aprovados.values_list('id'))
                voluntarios = Participacao.objects.filter(bolsa_concedida=False, projeto__in=projetos_por_edital_aprovados.values_list('id'))
                alunos_bolsistas = bolsistas.filter(vinculo_pessoa__tipo_relacionamento__model='aluno').count()
                alunos_voluntarios = voluntarios.filter(vinculo_pessoa__tipo_relacionamento__model='aluno').count()
                docentes_bolsistas = bolsistas.filter(vinculo_pessoa__in=Servidor.objects.filter(eh_docente=True).values_list('vinculos', flat=True)).count()
                docentes_voluntarios = voluntarios.filter(vinculo_pessoa__in=Servidor.objects.filter(eh_docente=True).values_list('vinculos', flat=True)).count()
                tecnicos_adm_bolsistas = bolsistas.filter(vinculo_pessoa__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True)).count()
                tecnicos_adm_voluntarios = voluntarios.filter(vinculo_pessoa__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True)).count()
                # ----------------------------------------------------

                total_membros_edital = alunos_bolsistas + alunos_voluntarios + docentes_bolsistas + docentes_voluntarios + tecnicos_adm_bolsistas + tecnicos_adm_voluntarios

                total_membros_edital_geral = total_membros_edital_geral + total_membros_edital

                total_membros_edital_alunos_bolsistas = total_membros_edital_alunos_bolsistas + alunos_bolsistas
                total_membros_edital_alunos_voluntarios = total_membros_edital_alunos_voluntarios + alunos_voluntarios

                total_membros_edital_docentes_bolsistas = total_membros_edital_docentes_bolsistas + docentes_bolsistas
                total_membros_edital_docentes_voluntarios = total_membros_edital_docentes_voluntarios + docentes_voluntarios

                total_membros_edital_tecnicos_adm_bolsistas = total_membros_edital_tecnicos_adm_bolsistas + tecnicos_adm_bolsistas
                total_membros_edital_tecnicos_adm_voluntarios = total_membros_edital_tecnicos_adm_voluntarios + tecnicos_adm_voluntarios

                quantidade_participantes.append(
                    dict(
                        edital=edital,
                        alunos_bolsistas=alunos_bolsistas,
                        alunos_voluntarios=alunos_voluntarios,
                        docentes_bolsistas=docentes_bolsistas,
                        docentes_voluntarios=docentes_voluntarios,
                        tecnicos_adm_bolsistas=tecnicos_adm_bolsistas,
                        tecnicos_adm_voluntarios=tecnicos_adm_voluntarios,
                        total_membros_edital=total_membros_edital,
                    )
                )
            # ----------------------------------------------------
            ids = 0
            while ids < len(areas) * 2:
                total = 0
                idx = 0
                while idx < editais.count():
                    if len(list(lista_qtd.items())) > idx:
                        total = total + list(lista_qtd.items())[idx][1]['valores'][ids]
                    idx += 1
                lista_total.append(total)
                ids += 1

            area_tematica_total_geral = 0
            area_tematica_total_docente_bols = 0
            area_tematica_total_docente_vol = 0
            area_tematica_total_tec_adm_bols = 0
            area_tematica_total_tec_adm_vol = 0
            area_tematica_total_aluno_bols = 0
            area_tematica_total_aluno_vol = 0

            if campus_relatorio:
                projetos_area_conhecimento = Projeto.objects.filter(uo=campus_relatorio, edital__in=editais.values_list('id'), aprovado=True)
            else:
                projetos_area_conhecimento = Projeto.objects.filter(edital__in=editais.values_list('id'), aprovado=True)
            if ppg:
                projetos_area_conhecimento = projetos_area_conhecimento.filter(ppg=ppg)
            for area in AreaConhecimento.objects.filter(descricao__in=areas).order_by('descricao'):
                if projetos_area_conhecimento.filter(area_conhecimento=area).exists():
                    bolsistas = Participacao.objects.filter(
                        vinculo=TipoVinculo.BOLSISTA, projeto__in=projetos_area_conhecimento.values_list('id'), bolsa_concedida=True, projeto__area_conhecimento=area
                    ).distinct()
                    voluntarios = Participacao.objects.filter(
                        bolsa_concedida=False, projeto__in=projetos_area_conhecimento.values_list('id'), projeto__area_conhecimento=area
                    ).distinct()

                    total_alunos_bolsistas = bolsistas.filter(vinculo_pessoa__tipo_relacionamento__model='aluno').count()
                    total_alunos_voluntarios = voluntarios.filter(vinculo_pessoa__tipo_relacionamento__model='aluno').count()

                    total_docentes_voluntarios = voluntarios.filter(vinculo_pessoa__in=Servidor.objects.filter(eh_docente=True).values_list('vinculos', flat=True)).count()
                    total_docentes_bolsistas = bolsistas.filter(vinculo_pessoa__in=Servidor.objects.filter(eh_docente=True).values_list('vinculos', flat=True)).count()

                    total_tec_adm_voluntarios = voluntarios.filter(
                        vinculo_pessoa__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True)
                    ).count()
                    total_tec_adm_bolsistas = bolsistas.filter(
                        vinculo_pessoa__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True)
                    ).count()

                    total = (
                        total_alunos_bolsistas
                        + total_alunos_voluntarios
                        + total_docentes_bolsistas
                        + total_docentes_voluntarios
                        + total_tec_adm_bolsistas
                        + total_tec_adm_voluntarios
                    )

                    participantes_por_area_conhecimento.append(
                        dict(
                            area=area.descricao,
                            alunos_bolsistas=total_alunos_bolsistas,
                            alunos_voluntarios=total_alunos_voluntarios,
                            docentes_bolsistas=total_docentes_bolsistas,
                            docentes_voluntarios=total_docentes_voluntarios,
                            tec_adm_bolsistas=total_tec_adm_bolsistas,
                            tec_adm_voluntarios=total_tec_adm_voluntarios,
                            total=total,
                        )
                    )
                    area_tematica_total_geral = area_tematica_total_geral + total
                    area_tematica_total_docente_bols = area_tematica_total_docente_bols + total_docentes_bolsistas
                    area_tematica_total_docente_vol = area_tematica_total_docente_vol + total_docentes_voluntarios
                    area_tematica_total_tec_adm_bols = area_tematica_total_tec_adm_bols + total_tec_adm_bolsistas
                    area_tematica_total_tec_adm_vol = area_tematica_total_tec_adm_vol + total_tec_adm_voluntarios
                    area_tematica_total_aluno_bols = area_tematica_total_aluno_bols + total_alunos_bolsistas
                    area_tematica_total_aluno_vol = area_tematica_total_aluno_vol + total_alunos_voluntarios

            lista_grupos_pesquisa = list()
            ids_dos_grupos_pesquisa = projetos_area_conhecimento.values_list('grupo_pesquisa', flat=True)
            total_grupos_pesquisa = 0
            for grupo in GrupoPesquisa.objects.filter(id__in=ids_dos_grupos_pesquisa).order_by('descricao'):
                qtd = projetos_area_conhecimento.filter(grupo_pesquisa=grupo).count()
                lista_grupos_pesquisa.append([grupo.descricao, qtd])
                total_grupos_pesquisa = total_grupos_pesquisa + qtd

            if 'xls' in request.POST and escolheu_ano:
                return tasks.relatorio_dimensao_export_to_xls(
                    quantidade_projetos, areas, lista_qtd, quantidade_participantes, participantes_por_area_conhecimento, lista_grupos_pesquisa
                )

    if campus_relatorio:
        title = f'Relatório de Dimensão dos Projetos de Pesquisa - Campus {campus_relatorio}'
    else:
        title = 'Relatório de Dimensão dos Projetos de Pesquisa'

    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_projeto')
def rejeitar_indicacao(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=request.user.get_vinculo()).exists():
        AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=request.user.get_vinculo()).update(rejeitado=True, rejeitado_em=datetime.datetime.now())
        return httprr(f'/pesquisa/projetos_especial_pre_aprovados/{projeto.edital.id}/', 'Indicação rejeitada com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.view_laboratoriopesquisa')
def laboratorio_pesquisa(request, laboratorio_id):
    laboratorio = get_object_or_404(LaboratorioPesquisa, pk=laboratorio_id)
    title = f'{laboratorio}'
    equipamentos = EquipamentoLaboratorioPesquisa.objects.filter(laboratorio=laboratorio)
    servicos = ServicoLaboratorioPesquisa.objects.filter(laboratorio=laboratorio)
    fotos = FotoLaboratorioPesquisa.objects.filter(laboratorio=laboratorio)
    materiais = MaterialLaboratorioPesquisa.objects.filter(laboratorio=laboratorio)
    solicitacoes = SolicitacaoServicoLaboratorio.objects.filter(laboratorio=laboratorio)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == laboratorio.coordenador
    projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
    projetos_execucao = Projeto.objects.filter(pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, inativado=False).exclude(
        id__in=projetos_cancelados
    )
    eh_coordenador_projeto = projetos_execucao.filter(vinculo_coordenador=request.user.get_vinculo()).exists()
    return locals()


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def cadastrar_equipamento_laboratorio(request, laboratorio_id):
    laboratorio = get_object_or_404(LaboratorioPesquisa, pk=laboratorio_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == laboratorio.coordenador
    if pode_gerenciar:
        title = 'Cadastrar Equipamento'
        equipamento = EquipamentoLaboratorioPesquisa()
        equipamento.laboratorio = laboratorio
        form = EquipamentoLaboratorioForm(request.POST or None, request.FILES or None, instance=equipamento)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/cadastrar_equipamento_laboratorio/{laboratorio.id}/', 'Equipamento cadastrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def cadastrar_servico_laboratorio(request, laboratorio_id):
    laboratorio = get_object_or_404(LaboratorioPesquisa, pk=laboratorio_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == laboratorio.coordenador
    if pode_gerenciar:
        title = 'Cadastrar Serviço'
        servico = ServicoLaboratorioPesquisa()
        servico.laboratorio = laboratorio
        form = ServicoLaboratorioForm(request.POST or None, instance=servico)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=servicos', 'Serviço cadastrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def cadastrar_material_laboratorio(request, laboratorio_id):
    laboratorio = get_object_or_404(LaboratorioPesquisa, pk=laboratorio_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == laboratorio.coordenador
    if pode_gerenciar:
        title = 'Cadastrar Material'
        material = MaterialLaboratorioPesquisa()
        material.laboratorio = laboratorio
        form = MaterialLaboratorioPesquisaForm(request.POST or None, request.FILES or None, instance=material)
        if form.is_valid():
            o = form.save(False)
            if form.cleaned_data.get('adicionar_novo'):
                if MaterialConsumoPesquisa.objects.filter(descricao=form.cleaned_data.get('descricao')).exists():
                    novo_material = MaterialConsumoPesquisa.objects.filter(descricao=form.cleaned_data.get('descricao'))[0]
                else:
                    novo_material = MaterialConsumoPesquisa()
                    novo_material.descricao = form.cleaned_data.get('descricao')
                    novo_material.save()
                o.material = novo_material
            o.save()
            return httprr(f'/pesquisa/cadastrar_material_laboratorio/{laboratorio.id}/', 'Material cadastrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_anexo_diverso_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    title = 'Adicionar Anexo ao Projeto'
    if request.POST:
        form = AnexosDiversosProjetoForm(request.POST, request.FILES, projeto=projeto)
        if form.is_valid():
            o = form.save(False)
            o.projeto = projeto

            arquivo_up = request.FILES['arquivo_anexo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            o.arquivo = arquivo
            o.save()
            arquivo.store(request.user, content)

            return httprr(f'/pesquisa/projeto/{projeto.id}/?tab=anexos', 'Anexo cadastrado com sucesso.')
    else:
        participacao = None
        if 'termo_desligamento' in request.GET:
            participacao = get_object_or_404(Participacao, pk=request.GET.get('termo_desligamento'))
            title = 'Adicionar Termo de Desligamento do Participante'

        form = AnexosDiversosProjetoForm(request.POST or None, projeto=projeto, participacao=participacao)

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def excluir_outro_anexo(request, anexo_id):
    anexo = get_object_or_404(ProjetoAnexo, pk=anexo_id)
    tem_permissao(request, anexo.projeto)
    if not anexo.anexo_edital and not anexo.projeto.eh_somente_leitura():
        anexo.delete()
        return httprr(f'/pesquisa/projeto/{anexo.projeto.id}/?tab=anexos', 'Anexo removido com sucesso.')
    else:
        return httprr(f'/pesquisa/projeto/{anexo.projeto.id}/?tab=anexos', 'Anexo não pode ser removido.', tag='error')


@rtr()
@permission_required('pesquisa.view_edital')
def lista_mensal_bolsistas(request):
    title = 'Lista Mensal de Bolsistas'
    form = ListaMensalBolsistaForm(request.GET or None)
    if form.is_valid():
        ano = form.cleaned_data.get('ano')
        mes = form.cleaned_data.get('mes')
        edital = form.cleaned_data.get('edital')
        registros = ProjetoAnexo.objects.filter(vinculo_membro_equipe__isnull=False, ano=ano, mes=mes, desembolso__despesa__nome__unaccent__icontains='financeiro a estudantes').order_by(
            'projeto__edital', 'projeto'
        )
        if edital:
            registros = registros.filter(projeto__edital=edital)
        if 'xls' in request.GET and registros.count():
            return tasks.lista_mensal_bolsistas_to_xls(registros, ano, registros[0].get_mes())
    return locals()


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def classificar_obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    if obra.eh_ativa() and obra.situacao == obra.ACEITA:
        obra.situacao = obra.CLASSIFICADA
        obra.save()
        return httprr(f'/pesquisa/obra/{obra.id}/', 'Obra classificada com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def cadastrar_foto_laboratorio(request, laboratorio_id):
    title = 'Cadastrar Foto'
    laboratorio = get_object_or_404(LaboratorioPesquisa, pk=laboratorio_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == laboratorio.coordenador
    if pode_gerenciar:
        foto = FotoLaboratorioPesquisa()
        foto.laboratorio = laboratorio
        form = FotoLaboratorioForm(request.POST or None, request.FILES or None, instance=foto)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=fotos', 'Foto cadastrada com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def editar_servico(request, servico_id):
    servico = get_object_or_404(ServicoLaboratorioPesquisa, pk=servico_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == servico.laboratorio.coordenador
    if pode_gerenciar:
        title = 'Editar Serviço'
        form = ServicoLaboratorioForm(request.POST or None, request.FILES or None, instance=servico)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/laboratorio_pesquisa/{servico.laboratorio.id}/?tab=servicos', 'Serviço editado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def excluir_servico(request, servico_id):
    servico = get_object_or_404(ServicoLaboratorioPesquisa, pk=servico_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == servico.laboratorio.coordenador
    if pode_gerenciar:
        laboratorio = servico.laboratorio
        servico.delete()
        return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=servicos', 'Serviço excluído com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def editar_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(EquipamentoLaboratorioPesquisa, pk=equipamento_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == equipamento.laboratorio.coordenador
    if pode_gerenciar:
        title = 'Editar Equipamento'
        form = EquipamentoLaboratorioForm(request.POST or None, request.FILES or None, instance=equipamento)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/laboratorio_pesquisa/{equipamento.laboratorio.id}/?tab=equipamentos', 'Equipamento editado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def excluir_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(EquipamentoLaboratorioPesquisa, pk=equipamento_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == equipamento.laboratorio.coordenador
    if pode_gerenciar:
        laboratorio = equipamento.laboratorio
        equipamento.delete()
        return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=equipamentos', 'Equipamento excluído com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def editar_material(request, material_id):
    material = get_object_or_404(MaterialLaboratorioPesquisa, pk=material_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == material.laboratorio.coordenador
    if pode_gerenciar:
        title = 'Editar Equipamento'
        form = MaterialLaboratorioPesquisaForm(request.POST or None, request.FILES or None, instance=material)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/laboratorio_pesquisa/{material.laboratorio.id}/?tab=materiais', 'Material editado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def excluir_material(request, material_id):
    material = get_object_or_404(MaterialLaboratorioPesquisa, pk=material_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == material.laboratorio.coordenador
    if pode_gerenciar:
        laboratorio = material.laboratorio
        material.delete()
        return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=materiais', 'Material excluído com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def excluir_foto_laboratorio(request, foto_id):
    foto = get_object_or_404(FotoLaboratorioPesquisa, pk=foto_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == foto.laboratorio.coordenador
    if pode_gerenciar:
        laboratorio = foto.laboratorio
        foto.delete()
        return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=fotos', 'Foto excluída com sucesso.')


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def alterar_situacao_obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    title = 'Alterar Situação da Obra'
    if obra.eh_ativa():
        form = SituacaoObraForm(request.POST or None, instance=obra)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/obra/{obra.id}/', 'Situação da obra alterada com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def editar_parecer(request, parecerobra_id):
    parecer = get_object_or_404(ParecerObra, pk=parecerobra_id)
    title = 'Editar Parecer'
    obra = parecer.obra
    form = AvaliacaoPareceristaObraForm(request.POST or None, request.FILES or None, instance=parecer)
    if form.is_valid():
        o = form.save(False)
        o.parecer_realizado_em = datetime.datetime.now()
        o.save()
        titulo = '[SUAP] Pesquisa: Notificação sobre Submissão de Obra'
        texto = '''<h1>Pesquisa</h1>'
                    <h2>Submissão de Obra</h2>
                    <p>O pedido de publicação da obra <strong>{0}<strong> foi {1} pelo parecerista. Caso tenha sido aprovada com ressalvas, será necessário o reenvio da obra.</p>
                    <p>Para mais informações, acesse: <a href="{2}/pesquisa/obra/{3}/">{2}/pesquisa/obra/{3}/</a></p>'''.format(
            obra.titulo, form.instance.situacao, settings.SITE_URL, obra.id
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obra.submetido_por_vinculo])
        return httprr(f'/pesquisa/obra/{obra.id}/?tab=analise_parecerista', 'Parecer editado com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_pre_avaliar_projeto')
def validar_projeto_fluxo_simplificado(request, projeto_id, opcao):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if get_uo(request.user) == projeto.uo and not projeto.edital.tem_formato_completo() and not projeto.vinculo_supervisor:
        if opcao == '1':
            vinculo = request.user.get_vinculo()
            projeto.pre_aprovado = True
            projeto.aprovado = True
            projeto.data_pre_avaliacao = datetime.date.today()
            projeto.data_avaliacao = datetime.date.today()
            projeto.vinculo_autor_pre_avaliacao = vinculo
            projeto.vinculo_supervisor = vinculo
            projeto.save()
            return httprr(f'/pesquisa/projeto/{projeto.id}/', 'Projeto deferido com sucesso.')
        elif opcao == '2':
            projeto.pre_aprovado = False
            projeto.aprovado = False
            projeto.data_pre_avaliacao = datetime.date.today()
            projeto.data_avaliacao = datetime.date.today()
            projeto.vinculo_autor_pre_avaliacao = request.user.get_vinculo()

            projeto.save()
            return httprr(f'/pesquisa/projeto/{projeto.id}/', 'Projeto indeferido com sucesso.')

        else:
            raise PermissionDenied

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_avaliar_obra')
def rejeitar_indicacao_parecerista_obra(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    if ParecerObra.objects.filter(obra=obra, parecer_realizado_por_vinculo=request.user.get_vinculo()).exists():
        ParecerObra.objects.filter(obra=obra, parecer_realizado_por_vinculo=request.user.get_vinculo()).update(recusou_indicacao=True)

        return httprr('/', 'Recusa de indicação cadastrada com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_avaliar_obra')
def emitir_declaracao_parecerista_obra(request):
    title = 'Emitir Declaração de Parecerista'
    obras_avaliadas = (
        ParecerObra.objects.filter(parecer_realizado_em__isnull=False, recusou_indicacao=False, parecer_realizado_por_vinculo=request.user.get_vinculo())
        .values('obra__edital__titulo', 'obra__edital')
        .annotate(total=Count('obra'))
        .order_by('-obra__edital')
    )

    return locals()


@documento('Declaração de Parecerista', enumerar_paginas=False, validade=360, modelo='pesquisa.editalsubmissaoobra', forcar_recriacao=True)
@rtr()
@permission_required('pesquisa.pode_avaliar_obra')
def emitir_declaracao_parecerista_pdf(request, pk):
    edital = get_object_or_404(EditalSubmissaoObra, pk=pk)
    vinculo = request.user.get_vinculo()
    nome = vinculo.pessoa.nome

    hoje = datetime.datetime.now()
    nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao') or 'Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
    nome_pro_reitoria = Configuracao.get_valor_por_chave('pesquisa', 'nome_propi') or 'Pró-Reitoria de Pesquisa e Inovação'
    meses = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
    mes = meses[hoje.month - 1]
    ano = edital.data_inicio_submissao.year
    pareceres = ParecerObra.objects.filter(obra__edital=edital, parecer_realizado_em__isnull=False, recusou_indicacao=False, parecer_realizado_por_vinculo=vinculo).order_by(
        'obra__titulo'
    )

    cidade = 'Natal'
    if pareceres.exists():
        uo = get_uo(pareceres[0].obra.submetido_por_vinculo.user)
        cidade = uo.municipio.nome

    return locals()


@rtr()
@permission_required('pesquisa.pode_validar_obra, pesquisa.add_editalsubmissaoobra')
def listar_pareceristas_obras(request):
    title = 'Cadastro de Pareceristas'
    form = PareceristasObraForm(request.GET or None)
    if form.is_valid():
        area_conhecimento = form.cleaned_data['area_conhecimento']
        palavra_chave = form.cleaned_data['palavra_chave']
        uo = form.cleaned_data['uo']
        pareceristas = ParecerObra.objects.filter(parecer_realizado_em__isnull=False, recusou_indicacao=False).order_by(
            'parecer_realizado_por_vinculo__pessoa__nome')
        if area_conhecimento:
            area = AreaConhecimento.objects.filter(id=area_conhecimento.id)
            ids_servidores = Servidor.objects.filter(areas_de_conhecimento__in=area.values_list('id', flat=True)).values_list('id', flat=True)
            ids_pessoas_externas = AreaConhecimentoParecerista.objects.filter(areas_de_conhecimento__in=area.values_list('id', flat=True)).values_list('parecerista__id', flat=True)
            ids = set([int(x) for x in ids_servidores] + [int(x) for x in ids_pessoas_externas])
            pareceristas = pareceristas.filter(parecer_realizado_por_vinculo__pessoa__id__in=ids)
        if uo:
            pareceristas = pareceristas.filter(parecer_realizado_por_vinculo__setor__uo=uo)
        if palavra_chave:
            pareceristas = pareceristas.filter(parecer_realizado_por_vinculo__pessoa__nome__icontains=palavra_chave)
        pareceristas = pareceristas.distinct('parecer_realizado_por_vinculo__pessoa__nome')
    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_obra')
def indicar_areas_conhecimento_de_interesse(request):
    title = 'Cadastrar Áreas de Conhecimento do seu Interesse'
    if request.user.get_vinculo().eh_prestador():
        pessoa = request.user.get_relacionamento()
        if AreaConhecimentoParecerista.objects.filter(parecerista=pessoa).exists():
            registro = AreaConhecimentoParecerista.objects.filter(parecerista=pessoa)[0]
            areas_conhecimentos = registro.areas_de_conhecimento.all().order_by('superior')
        else:
            registro = AreaConhecimentoParecerista()
            registro.parecerista = pessoa
            areas_conhecimentos = None
        form = AreaConhecimentoPareceristaForm(data=request.POST or None, request=request, instance=registro)
        if form.is_valid():
            form.save()

            return httprr('.', 'Áreas de conhecimento cadastradas com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_editalsubmissaoobra')
def alterar_autor(request, obra_id):
    title = 'Alterar Autor/Organizador'
    obra = get_object_or_404(Obra, pk=obra_id)
    form = AlterarAutorForm(request.POST or None, instance=obra)
    if form.is_valid():
        form.save()
        return httprr(f'/pesquisa/obra/{obra.id}/', 'Autor/Organizador editado com sucesso.')

    return locals()


# View que se conecta a view rh.views.servidor
@receiver(rh_servidor_view_tab)
def servidor_view_tab_signal(sender, request, servidor, verificacao_propria, eh_chefe, **kwargs):
    participacoes_pesquisa = Participacao.objects.filter(vinculo_pessoa=servidor.get_vinculo(), ativo=True, projeto__aprovado=True)

    if participacoes_pesquisa.exists():
        return render_to_string(
            template_name='pesquisa/templates/servidor_view_tab.html',
            context={"lps_context": {"nome_modulo": "pesquisa"}, 'servidor': servidor, 'participacoes_pesquisa': participacoes_pesquisa}, request=request
        )

    return False


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def clonar_projeto(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    if not CurriculoVittaeLattes.objects.filter(vinculo=request.user.get_vinculo()).exists():
        raise PermissionDenied()

    if not request.user.get_relacionamento().areas_de_conhecimento.exists():
        return httprr(
            '/pesquisa/tornar_avaliador/',
            'Você precisa se cadastrar como avaliador interno para poder submeter um projeto de pesquisa. Entre em contato com a Pró-Reitoria de Pesquisa para mais detalhes.',
            tag='error',
        )

    hoje = datetime.datetime.now().date()
    curriculo = CurriculoVittaeLattes.objects.filter(vinculo=request.user.get_vinculo())[0]
    if curriculo.datahora_atualizacao and curriculo.datahora_atualizacao.date() < (hoje - relativedelta(months=+edital.tempo_maximo_meses_curriculo_desatualizado)):
        return httprr(
            '/pesquisa/editais_abertos/',
            'Seu currículo lattes não foi atualizado nos últimos {} meses. Acesse a Plataforma Lattes para '
            'atualizá-lo. Entre em contato com a Pró-Reitoria de Pesquisa para mais detalhes.'.format(edital.tempo_maximo_meses_curriculo_desatualizado),
            tag='error',
        )

    grupo_pesquisa_online = True

    setores = ()
    if request.user.get_relacionamento().setor_lotacao:
        setores += (request.user.get_relacionamento().setor_lotacao.uo.sigla,)
    if request.user.get_relacionamento().setor_exercicio:
        setores += (request.user.get_relacionamento().setor_exercicio.uo.sigla,)
    if request.user.get_relacionamento().servidor.setor:
        setores += (request.user.get_relacionamento().setor.uo.sigla,)

    if not BolsaDisponivel.objects.filter(edital=edital, uo__sigla__in=setores).exists():
        return httprr('/pesquisa/editais_abertos/', 'Este edital não possui oferta para o seu campus.', tag='error')

    instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    try:
        status = atualizar_grupos_pesquisa(curriculo.id)
        if status == 0 and edital.exige_grupo_pesquisa:
            return httprr(
                '/pesquisa/editais_abertos/',
                'O SUAP não encontrou nenhum Grupo de Pesquisa do {} ao qual você esteja vinculado. '
                'Solicitamos que atualize seu Currículo Lattes e aguarde a disponibilização pública na base '
                'CNPQ para então iniciar a submissão do seu projeto.'.format(instituicao_sigla),
                tag='error',
            )
        if status == 3:
            erro_grupo_pesquisa_offline = True
    except Exception:
        grupo_pesquisa_online = False
    title = f'Clonar Projeto no Edital: {edital}'
    form = ClonarProjetoForm(request.POST or None, request=request, edital=edital)
    if form.is_valid():
        projeto_clonado = form.processar()
        return httprr(f'/pesquisa/projeto/{projeto_clonado.id}/', 'Projeto clonado com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.add_comissaoeditalpesquisa')
def adicionar_comissao(request):
    title = 'Adicionar Comissão de Avaliação'
    form = ComissaoAvaliacaoForm(request.POST or None, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/pesquisa/adicionar_comissao_por_area/{form.instance.id}/', 'Adicione os membros da comissão.')

    return locals()


@rtr()
@permission_required('pesquisa.add_comissaoeditalpesquisa')
def adicionar_comissao_por_area(request, comissao_id):
    title = 'Adicionar Comissão de Avaliação - Por Área de Conhecimento'
    comissao = get_object_or_404(ComissaoEditalPesquisa, pk=comissao_id)
    form = ComissaoAvaliacaoPorAreaForm(request.POST or None, request=request)
    internos = Servidor.objects.ativos().filter(areas_de_conhecimento__isnull=False).values_list('id', flat=True)
    avaliadores_internos = Vinculo.objects.filter(id_relacionamento__in=internos, tipo_relacionamento__model='servidor')
    externos = AvaliadorExterno.objects.all().values_list('vinculo', flat=True)
    avaliadores_externos = Vinculo.objects.filter(id__in=externos, tipo_relacionamento__model='prestadorservico').filter(
        id_relacionamento__in=PrestadorServico.objects.filter(areas_de_conhecimento__isnull=False).values_list('id', flat=True)
    )
    avaliadores_cadastrados = avaliadores_internos | avaliadores_externos
    titulacoes = comissao.edital.titulacoes_avaliador.all().values_list('codigo', flat=True)
    for pessoa in avaliadores_cadastrados.prefetch_related('user', 'pessoa'):
        if pessoa.eh_servidor():
            servidor = pessoa.relacionamento
            if (not servidor.titulacao) or not (servidor.titulacao.codigo in titulacoes):
                avaliadores_cadastrados = avaliadores_cadastrados.exclude(id=pessoa.id)
        elif AvaliadorExterno.objects.filter(vinculo=pessoa).exists():
            avaliador_externo = AvaliadorExterno.objects.get(vinculo=pessoa)
            if not (avaliador_externo.titulacao.codigo in titulacoes):
                avaliadores_cadastrados = avaliadores_cadastrados.exclude(id=avaliador_externo.vinculo.id)

    area_escolhida = None
    lista_avaliadores = []

    if form.is_valid():
        area_escolhida = form.cleaned_data.get('area_conhecimento')
        if area_escolhida:
            sevidores_da_area = Servidor.objects.filter(areas_de_conhecimento=area_escolhida)
            externos_da_area = PrestadorServico.objects.filter(areas_de_conhecimento=area_escolhida)
            avaliadores_cadastrados = avaliadores_cadastrados.filter(
                id_relacionamento__in=sevidores_da_area.values_list('id', flat=True), tipo_relacionamento__model='servidor'
            ) | avaliadores_cadastrados.filter(id_relacionamento__in=externos_da_area.values_list('id', flat=True), tipo_relacionamento__model='prestadorservico')

    for pessoa in avaliadores_cadastrados.order_by('pessoa__nome'):
        if pessoa.id in comissao.vinculos_membros.all().values_list('id', flat=True):
            lista_avaliadores.append([pessoa, True])
        else:
            lista_avaliadores.append([pessoa, False])

    return locals()


@rtr()
@permission_required('pesquisa.add_comissaoeditalpesquisa')
def salvar_membros_da_comissao(request, comissao_id):
    comissao = get_object_or_404(ComissaoEditalPesquisa, pk=comissao_id)
    internos = Servidor.objects.ativos().filter(areas_de_conhecimento__isnull=False).values_list('id', flat=True)
    avaliadores_internos = Vinculo.objects.filter(id_relacionamento__in=internos, tipo_relacionamento__model='servidor')
    externos = AvaliadorExterno.objects.all().values_list('vinculo', flat=True)
    avaliadores_externos = Vinculo.objects.filter(id__in=externos, tipo_relacionamento__model='prestadorservico').filter(
        id_relacionamento__in=PrestadorServico.objects.filter(areas_de_conhecimento__isnull=False).values_list('id', flat=True)
    )

    avaliadores_cadastrados = avaliadores_internos | avaliadores_externos
    escolhidos = request.POST.getlist('registros')
    ids_escolhidos = list()
    if escolhidos:
        for item in escolhidos:
            ids_escolhidos.append(int(item))

    for avaliador in avaliadores_cadastrados.filter(id__in=ids_escolhidos):
        comissao.vinculos_membros.add(avaliador)

    return httprr(f'/pesquisa/adicionar_comissao_por_area/{comissao.id}/', 'Avaliadores cadastrados com sucesso.')


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def clonar_etapa(request, meta_id):
    title = 'Clonar Atividade'
    meta = get_object_or_404(Meta, pk=meta_id)
    tem_permissao(request, meta.projeto)
    form = ClonarEtapaForm(request.POST or None, projeto=meta.projeto)
    if form.is_valid():
        etapa_escolhida = get_object_or_404(Etapa, pk=form.cleaned_data.get('etapa').id)
        etapa_clonada = get_object_or_404(Etapa, pk=form.cleaned_data.get('etapa').id)
        etapa_clonada.id = None
        etapa_clonada.meta = meta
        ordem = 1
        if Etapa.objects.filter(meta=meta).order_by('-ordem').exists():
            ordem = Etapa.objects.filter(meta=meta).order_by('-ordem')[0].ordem + 1
        etapa_clonada.ordem = ordem
        etapa_clonada.data_cadastro = datetime.date.today()
        etapa_clonada.save()
        etapa_clonada.integrantes.set(etapa_escolhida.integrantes.all())
        etapa_clonada.save()
        return httprr('..', 'Atividade clonada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def projetos_pendentes_anuencia(request):
    title = 'Projetos Pendentes da Sua Anuência'
    servidor = vinculo = request.user.get_relacionamento()
    agora = datetime.datetime.now()
    projetos = Projeto.objects.filter(
        pre_aprovado=False,
        aprovado=False,
        responsavel_anuencia=servidor,
        projetocancelado__isnull=True,
        anuencia_registrada_em__isnull=True,
        edital__formato=Edital.FORMATO_COMPLETO
    ) | Projeto.objects.filter(
        pre_aprovado=False,
        aprovado=False,
        responsavel_anuencia=servidor,
        projetocancelado__isnull=True,
        edital__fim_inscricoes__gt=agora,
        edital__formato=Edital.FORMATO_SIMPLIFICADO
    )
    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def registrar_anuencia(request, projeto_id, opcao):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    agora = datetime.datetime.now()
    if request.user.get_relacionamento() == projeto.responsavel_anuencia and (projeto.edital.get_data_limite_anuencia() > agora):
        if opcao == '1':
            projeto.anuencia = True
            situacao = 'Anuência concedida'
        elif opcao == '2':
            projeto.anuencia = False
            situacao = 'Anuência negada'
        projeto.anuencia_registrada_em = agora
        projeto.save()
        historico = ProjetoHistoricoDeEnvio()
        historico.projeto = projeto
        historico.parecer_devolucao = situacao
        historico.data_operacao = datetime.datetime.now()
        historico.operador = request.user.get_relacionamento()
        historico.save()
        return httprr('/pesquisa/projetos_pendentes_anuencia/', 'Anuência registrada com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_edital')
def alterar_chefia_imediata(request, projeto_id):
    title = 'Alterar Responsável pela Anuência do Projeto'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if projeto.edital.get_data_limite_anuencia() > datetime.datetime.now():
        form = AlterarChefiaForm(request.POST or None, instance=projeto)
        if form.is_valid():
            o = form.save(False)
            o.anuencia = None
            o.anuencia_registrada_em = None
            o.save()
            titulo = '[SUAP] Pesquisa: Anuência de Projeto de Pesquisa'
            texto = f'<h1>Pesquisa</h1><h2>Anuência de Projeto de Pesquisa</h2><p>Foi solicitada sua anuência no projeto de pesquisa: {projeto.titulo}. Acesse o SUAP para mais detalhes.</p>'
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [form.cleaned_data.get('responsavel_anuencia').get_vinculo()])
            return httprr(f'/pesquisa/projeto/{projeto.id}/', 'Chefia imediata alterada com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_edital')
def inativar_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    usuario_logado = request.user
    if (usuario_logado.has_perm('pesquisa.pode_gerenciar_edital') and (get_uo(usuario_logado) == projeto.uo)) or projeto.is_gerente_sistemico(usuario_logado):
        title = f'Inativar Projeto - {projeto.titulo}'
        form = InativarProjetoForm(request.POST or None, instance=projeto)
        if form.is_valid():
            o = form.save(False)
            o.inativado = True
            o.inativado_em = datetime.datetime.now()
            o.inativado_por = request.user.get_relacionamento()
            o.save()
            historico = ProjetoHistoricoDeEnvio()
            historico.projeto = projeto
            historico.parecer_devolucao = 'Projeto inativado'
            historico.data_operacao = datetime.datetime.now()
            historico.operador = request.user.get_relacionamento()
            historico.save()
            return httprr(f'/pesquisa/projeto/{projeto.id}/', 'Projeto inativado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_ver_equipe_projeto')
def lista_email_coordenadores(request):
    title = 'Lista de Emails dos Coordenadores'
    form = EmailCoordenadoresForm(data=request.POST or None, request=request)
    if form.is_valid():
        hoje = datetime.datetime.now()
        emails = ''
        edital = form.cleaned_data["edital"]
        situacao = form.cleaned_data["situacao"]
        if situacao == EmailCoordenadoresForm.PROJETOS_EM_EDICAO:
            titulo_box = 'em Edição'
            title = 'Lista de Email dos Coordenadores - Projetos em Edição'
            projetos = Projeto.objects.filter(edital=edital)
            projetos = projetos.filter(data_conclusao_planejamento__isnull=True, edital__fim_inscricoes__gte=hoje)
        elif situacao == EmailCoordenadoresForm.PROJETOS_ENVIADOS:
            titulo_box = 'Enviados'
            title = 'Lista de Email dos Coordenadores - Projetos Inscritos'
            projetos = Projeto.objects.filter(edital=edital)
            projetos = projetos.filter(Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False))

        elif situacao == EmailCoordenadoresForm.PROJETOS_PRE_SELECIONADOS:
            titulo_box = 'Pré-Selecionados'
            title = 'Lista de Email dos Coordenadores - Projetos Pré-Selecionados'
            projetos = Projeto.objects.filter(edital=edital)
            projetos = projetos.filter(pre_aprovado=True, data_pre_avaliacao__isnull=False)

        elif situacao == EmailCoordenadoresForm.PROJETOS_EM_EXECUCAO:
            titulo_box = 'em Execução'
            title = 'Lista de Email dos Coordenadores - Projetos em Execução'
            projetos = Projeto.objects.filter(edital=edital, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True).distinct()

        elif situacao == EmailCoordenadoresForm.PROJETOS_EM_ATRASO:
            titulo_box = 'em Atraso'
            title = 'Lista de Email dos Coordenadores - Projetos em Atraso'
            projetos = Projeto.objects.filter(edital=edital, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, fim_execucao__lt=hoje.date()).distinct()

        elif situacao == EmailCoordenadoresForm.PROJETOS_CONCLUIDOS:
            titulo_box = 'Concluídos'
            title = 'Lista de Email dos Coordenadores - Concluídos'
            projetos = Projeto.objects.filter(edital=edital, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=False).distinct()

        if request.user.groups.filter(name__in=['Coordenador de Extensão', 'Visualizador de Projetos do Campus']):
            projetos = projetos.filter(uo=get_uo(request.user))

        for contador, projeto in enumerate(projetos, 1):
            emails = emails + projeto.vinculo_coordenador.pessoa.email + ';'
            if contador % 10:
                emails = emails + "\n"

    return locals()


@rtr()
@permission_required('pesquisa.add_linhaeditorial')
def desfazer_validacao_conselho(request, obra_id):
    obra = get_object_or_404(Obra, pk=obra_id)
    obra.situacao_conselho_editorial = None
    obra.obs_conselho_editorial = None
    obra.julgamento_conselho_realizado_em = None
    obra.situacao = Obra.CLASSIFICADA
    obra.cancelada_por_vinculo = None
    obra.cancelada_em = None
    obra.save()
    return httprr(f'/pesquisa/obra/{obra.id}/?tab=validacao_conselho', 'Validação do conselho desfeita com sucesso.')


@rtr()
@permission_required('pesquisa.add_edital')
def reativar_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    usuario_logado = request.user
    if (usuario_logado.has_perm('pesquisa.pode_gerenciar_edital') and (get_uo(usuario_logado) == projeto.uo)) or projeto.is_gerente_sistemico(usuario_logado):
        projeto.inativado = False
        projeto.inativado_em = None
        projeto.inativado_por = None
        projeto.save()
        historico = ProjetoHistoricoDeEnvio()
        historico.projeto = projeto
        historico.parecer_devolucao = 'Projeto reativado'
        historico.data_operacao = datetime.datetime.now()
        historico.operador = request.user.get_relacionamento()
        historico.save()
        return httprr(f'/pesquisa/projeto/{projeto.id}/', 'Projeto reativado com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def solicitar_alteracao_equipe(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    usuario_logado = request.user
    title = 'Solicitar Alteração da Equipe'
    if (
        projeto.pode_editar_inscricao_execucao()
        and not projeto.eh_somente_leitura()
        and (projeto.is_responsavel(usuario_logado) or projeto.is_coordenador_pesquisa_campus_projeto(request.user))
    ):
        is_coordenador = projeto.is_responsavel(usuario_logado)
        pode_avaliar_solicitacao = (
            request.user.has_perm('pesquisa.pode_gerenciar_edital') and (get_uo(request.user) == projeto.uo)
        ) or projeto.is_coordenador_pesquisa_campus_projeto(request.user)
        solicitacoes = SolicitacaoAlteracaoEquipe.objects.filter(projeto=projeto).order_by('-id')
        form = SolicitarAlteracaoEquipeForm(request.POST or None)
        if form.is_valid():
            o = form.save(False)
            o.projeto = projeto
            o.cadastrada_em = datetime.datetime.now()
            o.cadastrada_por = usuario_logado.get_vinculo()
            o.save()
            return httprr(f'/pesquisa/solicitar_alteracao_equipe/{projeto.id}/', 'Solicitação de alteração da equipe cadastrada com sucesso.')
        return locals()

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def avaliar_alteracao_equipe(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoAlteracaoEquipe, pk=solicitacao_id)
    projeto = solicitacao.projeto
    usuario_logado = request.user
    title = 'Avaliar Alteração da Equipe'
    pode_avaliar_solicitacao = projeto.is_coordenador_pesquisa_campus_projeto(request.user)
    if projeto.pode_editar_inscricao_execucao() and not projeto.eh_somente_leitura() and pode_avaliar_solicitacao:
        form = AvaliarAlteracaoEquipeForm(request.POST or None, instance=solicitacao)
        if form.is_valid():
            o = form.save(False)
            o.avaliada_em = datetime.datetime.now()
            o.avaliada_por = usuario_logado.get_vinculo()
            o.save()
            return httprr('..', 'Solicitação de alteração da equipe avaliada com sucesso.')
        return locals()

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def cadastrar_frequencia(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    eh_participante = projeto.eh_participante(request.user)
    title = 'Registrar Frequência/Atividade'
    if eh_participante and not projeto.eh_somente_leitura():
        form = RegistrarFrequenciaForm(request.POST or None)
        if form.is_valid():
            o = form.save(False)
            o.cadastrada_em = datetime.datetime.now()
            o.cadastrada_por = request.user.get_vinculo()
            o.projeto = projeto
            if projeto.is_responsavel(request.user):
                o.validada_em = datetime.datetime.now()
                o.validada_por = request.user.get_vinculo()
            o.save()
            data_fim = form.cleaned_data.get('data_fim')
            if data_fim:
                data_atual = form.cleaned_data.get('data') + relativedelta(days=1)
                while data_atual <= data_fim:
                    novo_registro = RegistroFrequencia()
                    novo_registro.descricao = o.descricao
                    novo_registro.carga_horaria = o.carga_horaria
                    novo_registro.data = data_atual
                    novo_registro.cadastrada_em = o.cadastrada_em
                    novo_registro.cadastrada_por = o.cadastrada_por
                    novo_registro.projeto = projeto
                    if projeto.is_responsavel(request.user):
                        novo_registro.validada_em = o.validada_em
                        novo_registro.validada_por = o.validada_por
                    novo_registro.save()
                    data_atual += relativedelta(days=1)

            return httprr(f'/pesquisa/projeto/{projeto.id}/?tab=registro_frequencia', 'Frequência/Atividade cadastrada com sucesso.')
        return locals()

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def validar_frequencia(request, registrofrequencia_id):
    registro = get_object_or_404(RegistroFrequencia, pk=registrofrequencia_id)
    if registro.projeto.is_responsavel(request.user):
        registro.validada_em = datetime.datetime.now()
        registro.validada_por = request.user.get_vinculo()
        registro.save()
        return httprr(f'/pesquisa/projeto/{registro.projeto.id}/?tab=registro_frequencia', 'Frequência/Atividade validada com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto, pesquisa.pode_acessar_lista_projetos')
def aceitar_termo_compromisso(request, participacao_id):
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    if participacao.vinculo_pessoa == request.user.get_vinculo():
        title = 'Aceitar Termo de Compromisso'
        form = AceiteTermoForm(request.POST or None, participacao=participacao, request=request)
        if form.is_valid():
            participacao.termo_aceito_em = datetime.datetime.now()
            participacao.save()
            return httprr(f'/pesquisa/projeto/{participacao.projeto.id}/?tab=equipe', 'Termo de compromisso aceito com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def excluir_desembolsos(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)

    if request.POST.getlist('action')[0] == 'Remover':
        deletar = request.POST.getlist('registros')
        if deletar:
            for item in deletar:
                desembolso = get_object_or_404(Desembolso, pk=int(item))
                if desembolso.projeto.id == projeto.id:
                    desembolso.delete()
            return httprr(f'/pesquisa/projeto/{projeto.id}/?tab=plano_desembolso', 'Desembolso(s) excluído(s) com sucesso.')
        else:
            return httprr(f'/pesquisa/projeto/{projeto.id}/?tab=plano_desembolso', 'Nenhum desembolso selecionado.', tag='error')


@rtr()
@permission_required('pesquisa.view_laboratoriopesquisa')
def solicitar_servico_laboratorio(request, laboratorio_id):
    laboratorio = get_object_or_404(LaboratorioPesquisa, pk=laboratorio_id)
    title = f'Solicitar Serviço - {laboratorio}'
    form = SolicitarServicoLaboratorioForm(request.POST or None, request.FILES or None, laboratorio=laboratorio)
    cal_meses = []
    qs_solicitacoes = SolicitacaoServicoLaboratorio.objects.filter(
        laboratorio=laboratorio, situacao__in=[SolicitacaoServicoLaboratorio.DEFERIDA, SolicitacaoServicoLaboratorio.EM_ESPERA]
    )

    data_agora = datetime.datetime.now()
    ano_corrente = data_agora.year
    mes_corrente = data_agora.month
    if qs_solicitacoes.exists():
        data_fim = qs_solicitacoes.latest('data').data
        if (data_fim.year == ano_corrente and data_fim.month >= mes_corrente) or (data_fim.year > ano_corrente):
            ultimo_ano = data_fim.year
            ultimo_mes = data_fim.month
            cal = CalendarioPlus()
            cal.mostrar_mes_e_ano = True
            mes = mes_corrente
            for ano in range(ano_corrente, ultimo_ano + 1):
                mes_final = 12
                if ano == ultimo_ano:
                    mes_final = ultimo_mes
                for mes in range(mes, mes_final + 1):
                    for solicitacao in qs_solicitacoes.order_by('hora_inicio'):
                        solicitacao_conflito = False
                        for [agenda_data_inicio, agenda_data_fim] in [[solicitacao.data, solicitacao.data]]:
                            if agenda_data_inicio.year == ano and agenda_data_inicio.month == mes:
                                if solicitacao.situacao == SolicitacaoServicoLaboratorio.DEFERIDA:
                                    css = 'success'
                                else:
                                    css = 'alert'

                                horario = f'{solicitacao.hora_inicio} - {solicitacao.hora_termino}'
                                descricao = f'<a href="" title="Serviço Agendado"><strong>{horario}</strong><br>{solicitacao.servico.descricao[:100]}</a>'

                                cal.adicionar_evento_calendario(agenda_data_inicio, agenda_data_fim, descricao, css)

                    cal_meses.append(cal.formato_mes(ano, mes))
                    # -------------------
                mes = 1

    if form.is_valid():
        o = form.save(False)
        o.laboratorio = laboratorio
        o.cadastrada_em = datetime.datetime.now()
        o.cadastrada_por = request.user.get_vinculo()
        o.save()
        titulo = '[SUAP] Laboratório: Solicitação de Serviço'
        texto = (
            '<h1>Pesquisa</h1>'
            '<h2>Laboratório - Solicitação de Serviço</h2>'
            '<p>Foi realizada uma nova solicitação de serviço para o laboratório \'{}\'. Acesse o SUAP para mais detalhes.</p>'.format(laboratorio.nome)
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [laboratorio.coordenador.get_vinculo()])
        return httprr(f'/pesquisa/laboratorio_pesquisa/{laboratorio.id}/?tab=servicos', 'Solicitação de serviço cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def avaliar_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoServicoLaboratorio, pk=solicitacao_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == solicitacao.laboratorio.coordenador
    if pode_gerenciar:
        opcao = request.GET.get('aprovar')
        title = 'Rejeitar Solicitação'
        if opcao:
            title = 'Aprovar Solicitação'

        form = AvaliarSolicitacaoLaboratorioForm(request.POST or None, request.FILES or None, instance=solicitacao, opcao=opcao)
        if form.is_valid():
            o = form.save(False)
            o.avaliada_em = datetime.datetime.now()
            if opcao:
                o.situacao = SolicitacaoServicoLaboratorio.DEFERIDA
            else:
                o.situacao = SolicitacaoServicoLaboratorio.INDEFERIDA
            o.save()
            titulo = '[SUAP] Avaliação: Solicitação de Serviço'
            texto = (
                '<h1>Pesquisa</h1>'
                '<h2>Avaliação - Solicitação de Serviço</h2>'
                '<p>Sua solicitação de serviço para o laboratório \'{}\' foi avaliada. Acesse o SUAP para mais detalhes.</p>'.format(solicitacao.laboratorio.nome)
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [solicitacao.cadastrada_por])
            return httprr('..', 'Solicitação avaliada com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.change_laboratoriopesquisa')
def concluir_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoServicoLaboratorio, pk=solicitacao_id)
    pode_gerenciar = request.user.has_perm('pesquisa.add_origemrecursoedital') or request.user.get_relacionamento() == solicitacao.laboratorio.coordenador
    if pode_gerenciar:
        solicitacao.situacao = SolicitacaoServicoLaboratorio.ATENDIDA
        solicitacao.save()
        titulo = '[SUAP] Conclusão do Serviço'
        texto = (
            '<h1>Pesquisa</h1>'
            '<h2>Conclusão do Serviço</h2>'
            '<p>O serviço solicitado ao laboratório \'{}\' foi concluído. Acesse o SUAP para mais detalhes.</p>'.format(solicitacao.laboratorio.nome)
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [solicitacao.cadastrada_por])
        return httprr(f'/pesquisa/laboratorio_pesquisa/{solicitacao.laboratorio.id}/?tab=solicitacoes', 'Solicitação concluída com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.view_laboratoriopesquisa')
def minhas_solicitacoes_servicos(request):
    title = 'Minhas Solicitações de Serviço'
    solicitacoes = SolicitacaoServicoLaboratorio.objects.filter(cadastrada_por=request.user.get_vinculo())
    form = MinhasSolicitacoesServicosForm(request.POST or None)
    if form.is_valid():
        laboratorio = form.cleaned_data.get('laboratorio')
        situacao = form.cleaned_data.get('situacao')
        if laboratorio:
            solicitacoes = solicitacoes.filter(laboratorio=laboratorio)
        if situacao:
            solicitacoes = solicitacoes.filter(situacao=situacao)

    return locals()


@rtr()
@permission_required('pesquisa.view_laboratoriopesquisa')
def laboratorios_pesquisa(request):
    title = 'Laboratórios de Pesquisa'
    laboratorios = LaboratorioPesquisa.objects.all()
    projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
    projetos_execucao = Projeto.objects.filter(pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, inativado=False).exclude(
        id__in=projetos_cancelados
    )
    eh_coordenador_projeto = projetos_execucao.filter(vinculo_coordenador=request.user.get_vinculo()).exists()
    form = FiltrarLaboratorioPesquisaForm(request.POST or None)
    if form.is_valid():
        uo = form.cleaned_data.get('uo')
        area_pesquisa = form.cleaned_data.get('area_pesquisa')
        if uo:
            laboratorios = laboratorios.filter(uo=uo)
        if area_pesquisa:
            laboratorios = laboratorios.filter(area_pesquisa=area_pesquisa)

    return locals()


@rtr()
@permission_required('pesquisa.view_laboratoriopesquisa')
def acompanhar_solicitacao_servico(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoServicoLaboratorio, pk=solicitacao_id)
    if solicitacao.cadastrada_por == request.user.get_vinculo() or request.user.get_relacionamento() == solicitacao.laboratorio.coordenador:
        title = 'Acompanhar Solicitação'
        qtd_comentarios = Comentario.objects.filter(
            content_type=ContentType.objects.get(app_label=solicitacao._meta.app_label, model=solicitacao._meta.model_name), object_id=solicitacao.pk, resposta=None
        ).count()
    else:
        raise PermissionDenied

    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto, pesquisa.pode_acessar_lista_projetos')
def gerar_lista_frequencia(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    is_gerente_sistemico = request.user.has_perm('pesquisa.tem_acesso_sistemico')
    is_coordenador = projeto.is_responsavel(request.user)
    is_avaliador = request.user.groups.filter(name='Avaliador Sistêmico de Projetos de Pesquisa')
    is_pre_avaliador = request.user.groups.filter(name__in=['Coordenador de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa'])
    eh_participante = projeto.eh_participante(request.user)
    is_coordenador_pesquisa = request.user.groups.filter(name__in=['Coordenador de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa', 'Diretor de Pesquisa'])
    vinculo = request.user.get_vinculo()
    is_coordenador_edu = request.user.has_perm('pesquisa.pode_acessar_lista_projetos')
    is_assessor_pesquisa = request.user.groups.filter(name='Assessor de Pesquisa')
    mesmo_campus = projeto.uo == get_uo(request.user)
    if not (
        is_coordenador_edu
        or is_coordenador_pesquisa.exists()
        or is_coordenador
        or is_gerente_sistemico
        or is_avaliador
        or is_assessor_pesquisa
        or (is_pre_avaliador and mesmo_campus)
        or eh_participante
        or projeto.vinculo_supervisor == vinculo
    ):
        raise PermissionDenied()

    if is_coordenador_edu and not request.user.has_perm('pesquisa.pode_visualizar_projeto') and get_uo(request.user) != projeto.uo:
        raise PermissionDenied()

    title = 'Lista de Frequência/Atividade'
    form = GerarListaFrequenciaForm(request.POST or None, projeto=projeto)
    if form.is_valid():
        registros = RegistroFrequencia.objects.filter(projeto=projeto).order_by('data')
        data_inicio = form.cleaned_data.get('data_inicio')
        data_termino = form.cleaned_data.get('data_termino')
        participante = form.cleaned_data.get('participante')
        if data_inicio:
            registros = registros.filter(data__gte=data_inicio)
        if data_termino:
            registros = registros.filter(data__lte=data_termino)
        if participante:
            registros = registros.filter(cadastrada_por=participante)
    return locals()


@rtr()
def autocadastro_parecerista(request):
    title = 'Seja um Parecerista'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = AutoCadastroPareceristaForm(request.POST or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Cadastro realizado com sucesso. Você receberá um email com instruções quando seu cadastro for validado.')
    return locals()


@permission_required('pesquisa.add_pessoaexternaobra')
def validar_parecerista(request, pessoaexternaobra_id, opcao):
    pessoa = get_object_or_404(PessoaExternaObra, pk=pessoaexternaobra_id)
    if not pessoa.validado_em:
        if opcao == '1':
            pessoa.ativo = True
        elif opcao == '2':
            pessoa.ativo = False

        pessoa.validado_por = request.user.get_vinculo()
        pessoa.validado_em = datetime.datetime.now()
        pessoa.save()

        if opcao == '1':
            grupo = Group.objects.get(name='Parecerista de Obra')
            pessoa.pessoa_fisica.user.groups.add(grupo)
            prestador = PrestadorServico.objects.filter(cpf=pessoa.cpf)[0]
            try:
                LdapConf = apps.get_model('ldap_backend', 'LdapConf')
                conf = LdapConf.get_active()
                conf.sync_user(prestador)
            except Exception:
                pass
            obj = TrocarSenha.objects.create(username=prestador.cpf.replace('.', '').replace('-', ''))
            url = f'{settings.SITE_URL}/comum/trocar_senha/{obj.username}/{obj.token}/'
            conteudo = '''
            <h1>Pesquisa</h1>
            <h2>Validação do Cadastro de Parecerista</h2>
            <p>Prezado usuário,</p>
            <br />
            <p>Seu cadastro como parecerista acaba de ser validado.</p>
            <p>Caso ainda não tenha definido uma senha de acesso, por favor, acesse: {}.</p>
            <br />
            <p>Caso o token seja inválido, informe o seu cpf nos campos 'usuário' e 'cpf' ('usuário' tem que ser sem pontuação).</p>
            <p>Em seguida será reenviado um email com as instruções para criação da senha de acesso.</p>
            '''.format(
                url
            )
            send_mail('[SUAP] Cadastro de Parecerista', conteudo, settings.DEFAULT_FROM_EMAIL, [prestador.email])
        return httprr('..', 'Cadastrado avaliado com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.add_pessoaexternaobra')
def ver_pessoa_externa(request, pessoaexternaobra_id):
    pessoa = get_object_or_404(PessoaExternaObra, pk=pessoaexternaobra_id)
    title = 'Visualizar Pessoa Externa'
    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_participante_colaborador(request, projeto_id):
    title = 'Adicionar Participante'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not projeto.edital.permite_colaborador_externo:
        raise PermissionDenied
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    if request.method == 'POST':
        form = ParticipacaoColaboradorForm(data=request.POST, projeto=projeto)
        form.projeto = projeto
        if form.is_valid():
            participacao = form.save(False)
            participacao.projeto = projeto
            participacao.vinculo = TipoVinculo.VOLUNTARIO
            participacao.bolsa_concedida = False
            participacao.pessoa = form.cleaned_data['prestador'].prestador
            participacao.vinculo_pessoa = form.cleaned_data['prestador'].prestador.get_vinculo()
            if Participacao.objects.filter(projeto=participacao.projeto, vinculo_pessoa=participacao.vinculo_pessoa).exists():
                return httprr('.', 'Este participante já pertence ao projeto.', tag='error')
            participacao.save()
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_ADICIONAR_COLABORADOR, data_evento=form.cleaned_data.get('data'))
            Participacao.gerar_anexos_do_participante(participacao)
            if projeto.edital.termo_compromisso_colaborador_externo:
                obj = TrocarSenha.objects.create(username=form.cleaned_data['prestador'].prestador.username)
                url = f'{settings.SITE_URL}/comum/trocar_senha/{obj.username}/{obj.token}/'
                titulo = '[SUAP] Pesquisa: Termo de Compromisso do Colaborador Externo'
                texto = (
                    '''
                    <h1>Pesquisa</h1>
                    <h2>Termo de Compromisso do Colaborador Externo</h2>
                    <p>Você foi cadastrado(a) como membro da equipe do projeto \'{}\'. Acesse o SUAP para aceitar o termo de compromisso.</p>
                    <p>Caso ainda não tenha definido uma senha de acesso, por favor, acesse o endereço: {}.</p>
                    <br />
                    <p>Caso o token seja inválido, informe o seu cpf nos campos 'usuário' e 'cpf' ('usuário' tem que ser sem pontuação).</p>
                    <p>Em seguida será reenviado um email com as instruções para criação da senha de acesso.</p>'
                    '''.format(projeto.titulo, url)
                )
            else:
                obj = TrocarSenha.objects.create(username=form.cleaned_data['prestador'].prestador.username)
                url = f'{settings.SITE_URL}/comum/trocar_senha/{obj.username}/{obj.token}/'
                titulo = '[SUAP] Pesquisa: Cadastro como Colaborador Externo'
                texto = (
                    '''
                    <h1>Pesquisa</h1>
                    <h2>Cadastro como Colaborador Externo</h2>
                    <p>Você foi cadastrado(a) como membro da equipe do projeto \'{}\'. Acesse o SUAP para mais detalhes.</p>
                    <p>Caso ainda não tenha definido uma senha de acesso, por favor, acesse o endereço: {}.</p>
                    <br />
                    <p>Caso o token seja inválido, informe o seu cpf nos campos 'usuário' e 'cpf/passaporte' ('usuário' tem que ser sem pontuação).</p>
                    <p>Em seguida será reenviado um email com as instruções para criação da senha de acesso.</p>'
                    '''.format(projeto.titulo, url)
                )

            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [form.cleaned_data.get('prestador').prestador.get_vinculo()])
            return httprr('..', 'Participante adicionado com sucesso.')
    else:
        form = ParticipacaoColaboradorForm(projeto=projeto)
        form.projeto = projeto

    return locals()


@rtr('adicionar.html')
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_participante_colaborador(request, projeto_id, participacao_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not request.user.groups.filter(name='Coordenador de Pesquisa'):
        tem_permissao(request, projeto)
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    title = f'Editar Participação: {participacao.get_nome()}'
    form = ParticipacaoColaboradorForm(request.POST or None, instance=participacao, projeto=projeto)
    alterou = False
    if form.is_valid():
        participacao = form.save(False)
        participacao_anterior = Participacao.objects.get(id=participacao.id)
        if form.cleaned_data.get('vinculo') != participacao_anterior.vinculo or form.cleaned_data.get('carga_horaria') != participacao_anterior.carga_horaria:
            alterou = True
        participacao.save()
        if alterou:
            participacao.adicionar_registro_historico_equipe(HistoricoEquipe.EVENTO_EDICAO_COLABORADOR, data_evento=form.cleaned_data.get('data'))
            Participacao.gerar_anexos_do_participante(participacao)
        else:
            historico = HistoricoEquipe.objects.filter(participante=participacao, projeto=projeto).order_by('id')
            if historico.exists():
                registro = historico[0]
                registro.data_movimentacao = form.cleaned_data.get('data')
                registro.save()
        return httprr('..', 'Participante editado com sucesso.')

    return locals()


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def validar_registros_frequencia(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    vinculo_usuario = request.user.get_vinculo()
    if request.method == 'POST' and projeto.eh_participante(request.user):
        url_origem = request.META.get('HTTP_REFERER', '.')
        if projeto.is_responsavel(request.user):
            if request.POST.getlist('action')[0] == 'Validar':
                registros = request.POST.getlist('registros')
                if registros:
                    for item in registros:
                        registro = get_object_or_404(RegistroFrequencia, pk=int(item))
                        if not registro.validada_em:
                            registro.validada_em = datetime.datetime.now()
                            registro.validada_por = vinculo_usuario
                            registro.save()
                    return httprr(url_origem, 'Registros de Frequência/Atividade diária validados com sucesso.')
                return httprr(url_origem, 'Nenhum registro selecionado.', tag='error')
            elif request.POST.getlist('action')[0] == 'Cancelar Validação':
                registros = request.POST.getlist('registros')
                if registros:
                    for item in registros:
                        registro = get_object_or_404(RegistroFrequencia, pk=int(item))
                        registro.validada_em = None
                        registro.validada_por = None
                        registro.save()
                    return httprr(url_origem, 'Validações dos Registros de Frequência/Atividade diária canceladas com sucesso.')
                return httprr(url_origem, 'Nenhum registro selecionado.', tag='error')
        if request.POST.getlist('action')[0] == 'Excluir Registros':
            registros = request.POST.getlist('registros')
            if registros:
                for item in registros:
                    registro = get_object_or_404(RegistroFrequencia, pk=int(item))
                    if not registro.validada_em and registro.cadastrada_por == vinculo_usuario:
                        registro.delete()
                return httprr(url_origem, 'Os Registros de Frequência/Atividade diária não validados foram excluídos com sucesso.')
            return httprr(url_origem, 'Nenhum registro selecionado.', tag='error')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def editar_frequencia(request, registrofrequencia_id):
    registro = get_object_or_404(RegistroFrequencia, pk=registrofrequencia_id)
    if not registro.validada_em and registro.cadastrada_por == request.user.get_vinculo():
        title = 'Editar Frequência/Atividade Diária'
        form = EditarFrequenciaForm(request.POST or None, instance=registro)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/projeto/{registro.projeto.id}/?tab=registro_frequencia', 'Frequência/Atividade diária editada com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_visualizar_projeto')
def excluir_frequencia(request, registrofrequencia_id):
    registro = get_object_or_404(RegistroFrequencia, pk=registrofrequencia_id)
    if not registro.validada_em and registro.cadastrada_por == request.user.get_vinculo():
        projeto = registro.projeto
        registro.delete()
        return httprr(f'/pesquisa/projeto/{projeto.id}/?tab=registro_frequencia', 'Frequência/Atividade diária excluída com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_foto(request, foto_id):
    foto = get_object_or_404(FotoProjeto, pk=foto_id)
    title = 'Editar Foto'
    tem_permissao(request, foto.projeto)
    form = EditarFotoProjetoForm(request.POST or None, request.FILES or None, instance=foto)
    if form.is_valid():
        form.save()
        return httprr(f'/pesquisa/projeto/{foto.projeto.id:d}/?tab=fotos', 'Foto editada com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_avaliar_projeto')
def aceitar_indicacao(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=request.user.get_vinculo()).exists():
        AvaliadorIndicado.objects.filter(projeto=projeto, vinculo=request.user.get_vinculo()).update(aceito_em=datetime.datetime.now())
        return httprr(f'/pesquisa/projetos_especial_pre_aprovados/{projeto.edital.id}/', 'Indicação aceita com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def adicionar_relatorio(request, projeto_id):
    title = 'Adicionar Relatório'
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    tem_permissao(request, projeto)
    form = RelatorioProjetoForm(data=request.POST or None, files=request.FILES or None, projeto=projeto)
    if form.is_valid():
        o = form.save(False)
        o.cadastrado_em = datetime.datetime.now()
        o.projeto = projeto
        o.save()
        return httprr(f'/pesquisa/projeto/{projeto.id}/?tab=relatorios', 'Relatório adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('pesquisa.pode_realizar_monitoramento_projeto')
def avaliar_relatorio(request, relatorio_id, situacao):
    title = 'Justificar da Não Aprovação do Relatório'
    relatorio = get_object_or_404(RelatorioProjeto, pk=relatorio_id)
    projeto = relatorio.projeto
    if not projeto.eh_somente_leitura() and projeto.vinculo_supervisor == request.user.get_vinculo() or request.user.has_perm('pesquisa.tem_acesso_sistemico'):
        if situacao == 1:
            relatorio.avaliado_em = datetime.datetime.now()
            relatorio.avaliado_por = request.user.get_vinculo()
            relatorio.aprovado = True
            relatorio.save()
            return httprr(f'/pesquisa/validar_execucao_etapa/{projeto.id}/', 'Relatório aprovado com sucesso.')
        elif situacao == 2:
            form = ReprovarExecucaoEtapaForm(request.POST or None)
            if form.is_valid():
                relatorio.avaliado_em = datetime.datetime.now()
                relatorio.avaliado_por = request.user.get_vinculo()
                relatorio.aprovado = False
                relatorio.justificativa_reprovacao = form.cleaned_data['obs']
                relatorio.save()
                return httprr('..', 'Justificativa de reprovação registrada com sucesso.')
    else:
        raise PermissionDenied

    return locals()


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def avaliar_conclusao_projeto_por_relatorio(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if projeto.vinculo_supervisor == request.user.get_vinculo() or request.user.has_perm('pesquisa.tem_acesso_sistemico'):
        title = 'Conclusão do Projeto'
        registro = projeto.get_registro_conclusao() or RegistroConclusaoProjeto()
        registro.projeto = projeto
        form = ValidacaoConclusaoProjetoForm(data=request.POST or None, registro=registro)
        if form.is_valid():
            aprovado = form.cleaned_data['aprovado']
            obs = form.cleaned_data['obs']
            registro.dt_avaliacao = datetime.date.today()
            registro.avaliador = request.user.get_relacionamento()
            registro.aprovado = aprovado
            registro.obs_avaliador = obs
            registro.save()
            return httprr('..', 'Conclusão do projeto registrada com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def excluir_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(RelatorioProjeto, pk=relatorio_id)
    tem_permissao(request, relatorio.projeto)
    if not relatorio.avaliado_em and relatorio.projeto.pode_editar_inscricao_execucao() and not relatorio.projeto.eh_somente_leitura():
        relatorio.delete()
        return httprr(f'/pesquisa/projeto/{relatorio.projeto.id}/?tab=relatorios', 'Relatório excluído com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('pesquisa.pode_interagir_com_projeto')
def editar_relatorio(request, relatorio_id):
    relatorio = get_object_or_404(RelatorioProjeto, pk=relatorio_id)
    title = 'Editar Relatório'
    tem_permissao(request, relatorio.projeto)
    if not relatorio.avaliado_em and relatorio.projeto.pode_editar_inscricao_execucao() and not relatorio.projeto.eh_somente_leitura():
        form = RelatorioProjetoForm(request.POST or None, request.FILES or None, instance=relatorio, projeto=relatorio.projeto)
        if form.is_valid():
            form.save()
            return httprr(f'/pesquisa/projeto/{relatorio.projeto.id:d}/?tab=relatorios', 'Relatório com sucesso.')
        return locals()
    else:
        raise PermissionDenied
