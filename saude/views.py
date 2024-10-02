import collections
import datetime
import uuid
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django_tables2.columns.base import Column

from ae.models import Participacao
from comum.models import PrestadorServico, Configuracao, Vinculo as VinculoPessoa
from comum.utils import get_table, get_uo, get_sigla_reitoria
from djtools import layout
from djtools.html.calendarios import CalendarioPlus
from djtools.html.graficos import PieChart, GroupedColumnChart, BarChart
from djtools.templatetags.filters import in_group, format_
from djtools.utils import rtr, httprr, group_required, permission_required, documento, send_notification
from edu.models import Aluno, CursoCampus, SituacaoMatricula, Modalidade
from rh.models import Servidor, PessoaFisica, UnidadeOrganizacional, PessoaExterna, Funcao
from saude import tasks
from saude.forms import (
    BuscaProntuarioForm,
    AdicionarVacinaForm,
    RegistrarVacinacaoForm,
    RegistrarPrevisaoVacinacaoForm,
    SinaisVitaisForm,
    AcuidadeVisualForm,
    AntropometriaForm,
    AntecedentesFamiliaresForm,
    ProcessoSaudeDoencaForm,
    HabitosDeVidaForm,
    DesenvolvimentoPessoalForm,
    ExameFisicoForm,
    PercepcaoSaudeBucalForm,
    MotivoForm,
    AnamneseForm,
    IntervencaoEnfermagemForm,
    HipoteseDiagnosticaForm,
    CondutaMedicaForm,
    FecharAtendimentoForm,
    CancelarAtendimentoForm,
    FiltroEstatisticaGeralForm,
    EstatisticasAtendimentosForm,
    OdontogramaForm,
    ProcedimentoOdontologicoForm,
    ExamePeriodontalForm,
    ExameEstomatologicoForm,
    IndicarProcedimentoForm,
    InformacaoAdicionalForm,
    PessoaExternaForm,
    AnotacaoInterdisciplinarForm,
    TipoConsultaForm,
    TipoVacinaForm,
    ExameImagemForm,
    ExameLaboratorialForm,
    ValoresExameLaboratorialForm,
    EditarExameLaboratorialForm,
    HipoteseDiagnosticaModelForm,
    CartaoVacinalForm,
    AtendimentoPsicologicoForm,
    AnamnesePsicologiaForm,
    AtendimentoMultidisciplinarForm,
    RelatorioOdontologicoForm,
    CartaoSUSAlunoForm,
    ObsRegistroExecucaoForm,
    RelatorioAtendimentoForm,
    DataHoraAtendimentoPsicologicoForm,
    AnexoPsicologiaForm,
    HorarioAtendimentoForm,
    FiltrarAtendimentosForm,
    JustificativaCancelamentoHorarioForm,
    MensagemVacinaAtrasadaForm,
    GetConfirmarHorarioAtendimentoForm,
    AtividadeGrupoForm,
    AtendimentoNutricaoMotivoForm,
    AtendimentoNutricaoAvalGastroForm,
    AtendimentoNutricaoDadosAlimentacaoForm,
    AtendimentoNutricaoRestricaoAlimentarForm,
    AtendimentoNutricaoConsumoForm,
    AtendimentoNutricaoDiagnosticoForm,
    AtendimentoNutricaoCategoriaTrabalhoForm,
    AtendimentoNutricaoCondutaForm,
    PlanoAlimentarForm,
    MarcadorConsumoAlimentarForm,
    ListaAlunosForm,
    PacienteAgendamentoForm,
    TipoDocumentoForm,
    PreencherDocumentoForm,
    AdicionarCartaoVacinalForm,
    JustificativaCancelamentoHorariosForm,
    AnamneseFisioterapiaForm,
    CondutaFisioterapiaForm,
    HipoteseFisioterapiaForm,
    IntervencaoFisioterapiaForm,
    RetornoFisioterapiaForm,
    EnviarMensagemForm, PassaporteVacinalCovidForm, RelatorioPassaporteCovidForm, JustificativaIndeferirPassaporteForm,
    CadastroResultadoTesteCovidForm,
    RelatorioPassaporteCovidChefiaForm,
    CadastroCartaoVacinalCovidForm, NotificarCovidForm, MonitorarNotificacaoForm, RelatorioNotificacaoCovidForm, VerificaPassaporteForm,
)
from saude.models import (
    Prontuario,
    Vacina,
    CartaoVacinal,
    SinaisVitais,
    AcuidadeVisual,
    Antropometria,
    AntecedentesFamiliares,
    ProcessoSaudeDoenca,
    HabitosDeVida,
    DesenvolvimentoPessoal,
    ExameFisico,
    PercepcaoSaudeBucal,
    Vinculo,
    Atendimento,
    TipoAtendimento,
    SituacaoAtendimento,
    Especialidades,
    Motivo,
    Anamnese,
    IntervencaoEnfermagem,
    HipoteseDiagnostica,
    CondutaMedica,
    AtendimentoEspecialidade,
    InformacaoAdicional,
    Odontograma,
    SituacaoClinica,
    ProcedimentoOdontologico,
    ExamePeriodontal,
    ExameEstomatologico,
    PlanoTratamento,
    ResultadoProcedimento,
    AnotacaoInterdisciplinar,
    AtividadeGrupo,
    ExameLaboratorial,
    ExameImagem,
    TipoExameLaboratorial,
    ValorExameLaboratorial,
    CategoriaExameLaboratorial,
    ProcedimentoOdontologia,
    AnamnesePsicologia,
    AtendimentoPsicologia,
    AtendimentoMultidisciplinar,
    DificuldadeOral,
    TipoConsultaOdontologia,
    AnexoPsicologia,
    HorarioAtendimento,
    BloqueioAtendimentoSaude,
    MetaAcaoEducativa,
    AtendimentoNutricao,
    ReceitaNutricional,
    ConsumoNutricao,
    PlanoAlimentar,
    FrequenciaPraticaAlimentar,
    FrequenciaAlimentarNutricao,
    PerguntaMarcadorNutricao,
    RespostaMarcadorNutricao,
    OpcaoRespostaMarcadorNutricao,
    DocumentoProntuario,
    AtendimentoFisioterapia,
    IntervencaoFisioterapia,
    HistoricoCartaoVacinal, PassaporteVacinalCovid, HistoricoValidacaoPassaporte, ResultadoTesteCovid, NotificacaoCovid,
    MonitoramentoCovid, ValidadorIntercampi,
)
from saude.management.commands import importar_dados_rnmaisvacina
from ponto.models import Frequencia


@layout.info()
def index_infos(request):
    infos = list()

    # Verificando se existem vacinas em atraso ou próximas (15 dias) do prazo
    hoje = datetime.datetime.now()
    vinculo = request.user.get_vinculo()
    prontuario = Prontuario.objects.filter(vinculo=vinculo).first()
    if prontuario:
        prontuario_id = prontuario.id

        qtd_vacina_atrasada = CartaoVacinal.objects.filter(prontuario=prontuario_id, data_prevista__isnull=False, data_vacinacao__isnull=True, data_prevista__lt=hoje).count()
        if qtd_vacina_atrasada:
            infos.append(dict(titulo='Você possui vacina{plural} atrasada{plural}. Procure o Setor de Saúde do seu campus.'.format(plural=pluralize(qtd_vacina_atrasada))))
        qtd_vacina_agendada = CartaoVacinal.objects.filter(
            prontuario=prontuario_id,
            data_prevista__isnull=False,
            data_vacinacao__isnull=True,
            data_prevista__gt=hoje,
            data_prevista__lte=hoje + datetime.timedelta(days=15)).count()
        if qtd_vacina_agendada:
            infos.append(dict(titulo='Você tem vacinaç{} agendada{} para os próximos 15 dias.'.format(pluralize(qtd_vacina_agendada, 'ão,ões'), pluralize(qtd_vacina_agendada))))

    return infos


@layout.quadro('Notificações de Síndromes Gripais e COVID-19', icone='heartbeat', pode_esconder=True)
def index_quadros_notificacoes_covid(quadro, request):
    utiliza_passaporte_vacinal = Configuracao.get_valor_por_chave('saude', 'utiliza_passaporte_vacinal')
    if utiliza_passaporte_vacinal:
        if request.user.has_perm('saude.view_notificacaocovid'):
            qtd_aguardando_monitoramento = NotificacaoCovid.objects.filter(uo=get_uo(request.user), monitoramento=NotificacaoCovid.SEM_MONITORAMENTO)
            if qtd_aguardando_monitoramento.exists():
                qtd = qtd_aguardando_monitoramento.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Notificaç{} de Síndromes Gripais e COVID-19'.format(pluralize(qtd, 'ão,ões')),
                        subtitulo=' aguardando monitoramento', qtd=qtd,
                        url='/admin/saude/notificacaocovid/?monitoramento__exact=Sem+monitoramento'
                    )
                )
        quadro.add_item(layout.ItemAcessoRapido(titulo='Notificar', url='/saude/notificar_caso_covid/', icone='plus', classe='success'))
        quadro.add_item(layout.ItemAcessoRapido(titulo='Monitoramento', url='/saude/relatorio_notificacao_covid/', icone='bars'))
    return quadro


@layout.quadro('Passaporte Vacinal', icone='heartbeat', pode_esconder=True)
def index_quadros_passaporte_vacinal(quadro, request):
    utiliza_passaporte_vacinal = Configuracao.get_valor_por_chave('saude', 'utiliza_passaporte_vacinal')
    if utiliza_passaporte_vacinal:
        if request.user.has_perm('saude.view_passaportevacinalcovid'):
            qtd_aguardando_avaliacao = PassaporteVacinalCovid.objects.filter(uo=get_uo(request.user), situacao_declaracao=PassaporteVacinalCovid.AGUARDANDO_VALIDACAO).filter(Q(possui_atestado_medico=True) | Q(termo_aceito_em__isnull=False))
            if qtd_aguardando_avaliacao.exists():
                qtd = qtd_aguardando_avaliacao.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Autodeclaraç{} para o Passaporte Vacinal da COVID'.format(pluralize(qtd, 'ão,ões')), subtitulo='aguardando avaliação', qtd=qtd, url='/admin/saude/passaportevacinalcovid/?situacao_declaracao__exact=Aguardando+validação'
                    )
                )

            qtd_teste_aguardando_avaliacao = ResultadoTesteCovid.objects.filter(passaporte__uo=get_uo(request.user), situacao=ResultadoTesteCovid.AGUARDANDO_VALIDACAO)
            if qtd_teste_aguardando_avaliacao.exists():
                qtd = qtd_teste_aguardando_avaliacao.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Resultado{pluralize(qtd)} de Testes Negativos contra COVID', subtitulo='aguardando avaliação', qtd=qtd, url='/admin/saude/passaportevacinalcovid/?teste_pendente=Sim'
                    )
                )

        if request.user.groups.filter(name='Chefe de Setor'):
            historico_funcao = request.user.get_relacionamento().historico_funcao().filter(
                funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False)
            if historico_funcao.exists():
                setor = historico_funcao.latest('id').setor_suap
                servidores_do_setor = Servidor.objects.ativos().filter(setor_exercicio__in=setor.descendentes)
                qtd_aguardando_avaliacao = PassaporteVacinalCovid.objects.filter(vinculo__in=servidores_do_setor.values_list('vinculos', flat=True), situacao_passaporte=PassaporteVacinalCovid.INVALIDO)
                if qtd_aguardando_avaliacao.exists():
                    qtd = qtd_aguardando_avaliacao.count()
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Servido{} sob a sua chefia'.format(pluralize(qtd, 'r,res')), subtitulo='com Passaporte Vacinal inválido', qtd=qtd, url='/saude/relatorio_passaporte_vacinal_chefia/?situacao=Inválido&situacao_declaracao=&categoria=&uo=&faixa_etaria=&relatoriopassaportecovidchefia_form=Aguarde...'
                        )
                    )
                data_inicio_checagem_ponto = Configuracao.get_valor_por_chave('saude', 'data_checagem_ponto')
                if data_inicio_checagem_ponto:
                    registros_frequencia = Frequencia.objects.filter(horario__gt=data_inicio_checagem_ponto, vinculo__in=qtd_aguardando_avaliacao.values_list('vinculo', flat=True)).distinct('vinculo')
                    if servidores_do_setor.exists() and registros_frequencia.exists():
                        qtd = registros_frequencia.count()
                        quadro.add_item(
                            layout.ItemContador(
                                titulo='Servido{} sob a sua chefia'.format(pluralize(qtd, 'r,res')), subtitulo='registraram frequência com Passaporte Vacinal inválido', qtd=qtd, url='/saude/relatorio_passaporte_vacinal_chefia/?situacao=&situacao_declaracao=&categoria=&uo=&faixa_etaria=&registrou_frequencia=on&relatoriopassaportecovidchefia_form=Aguarde...'
                            )
                        )

        if request.user.groups.filter(name='Coordenador de Curso'):
            cursos = CursoCampus.objects.filter(coordenador=request.user.get_relacionamento().funcionario) | CursoCampus.objects.filter(coordenador_2=request.user.get_relacionamento().funcionario)
            alunos = Aluno.ativos.filter(curso_campus__in=cursos.values_list('id', flat=True))
            qtd_aguardando_avaliacao = PassaporteVacinalCovid.objects.filter(vinculo__in=alunos.values_list('vinculos', flat=True), situacao_passaporte=PassaporteVacinalCovid.INVALIDO)
            if qtd_aguardando_avaliacao.exists():
                qtd = qtd_aguardando_avaliacao.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Aluno{pluralize(qtd)} de cursos sob sua coordenação', subtitulo='com Passaporte Vacinal inválido', qtd=qtd, url=f'/saude/relatorio_passaporte_vacinal/?situacao=Inválido&situacao_declaracao=&categoria=1&uo=14&curso={cursos[0].id}&turma=&faixa_etaria=&relatoriopassaportecovid_form=Aguarde...'
                    )
                )

        if request.user.groups.filter(name__in=['Fiscal de Contrato', 'Gerenciador de Prestador de Serviço']):
            prestadores = PrestadorServico.objects.filter(setor__uo=get_uo(request.user), ativo=True, cpf__isnull=False, ocupacaoprestador__isnull=False)
            qtd_aguardando_avaliacao = PassaporteVacinalCovid.objects.filter(vinculo__in=prestadores.values_list('vinculos', flat=True), situacao_passaporte=PassaporteVacinalCovid.INVALIDO)
            if qtd_aguardando_avaliacao.exists():
                qtd = qtd_aguardando_avaliacao.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Prestador{} de serviço'.format(pluralize(qtd, 'es')), subtitulo='com Passaporte Vacinal inválido', qtd=qtd, url=f'/saude/relatorio_passaporte_vacinal/?situacao=Inválido&situacao_declaracao=&categoria=3&uo={get_uo(request.user).id}&curso=&turma=&faixa_etaria=&relatoriopassaportecovid_form=Aguarde...'
                    )
                )

    return quadro


@layout.quadro('Saúde', icone='heartbeat')
def index_quadros(quadro, request):
    if request.user.groups.filter(name__in=['Médico'] + Especialidades.ENFERMAGEM):
        qtd_atendimentos_saude_abertos = Atendimento.objects.filter(
            tipo=TipoAtendimento.ENFERMAGEM_MEDICO, usuario_aberto__vinculo__setor__uo=get_uo(request.user), situacao=SituacaoAtendimento.ABERTO
        )
        if qtd_atendimentos_saude_abertos.exists():
            qtd = qtd_atendimentos_saude_abertos.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Atendimento{pluralize(qtd)}', subtitulo=f'Aberto{pluralize(qtd)}', qtd=qtd, url='/saude/prontuarios/?tab=atendimentos_abertos'
                )
            )

    if request.user.groups.filter(name__in=Especialidades.GRUPOS):
        hoje = datetime.datetime.now()
        prazo_vinte_dias = hoje + datetime.timedelta(days=20)
        acoes_educativas_em_aberto = AtividadeGrupo.objects.filter(
            meta__isnull=False, tema__isnull=True, uo=get_uo(request.user), data_inicio__gt=hoje, data_inicio__lte=prazo_vinte_dias
        )

        if acoes_educativas_em_aberto.exists():
            qtd = acoes_educativas_em_aberto.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Aç{} Educativa{}'.format(pluralize(qtd, 'ão,ões'), pluralize(qtd)),
                    subtitulo=f'Prevista{pluralize(qtd)} para os próximos 20 dias',
                    qtd=qtd,
                    url=f'/saude/visualizar_acoes_educativas/{acoes_educativas_em_aberto[0].meta_id}/',
                )
            )

        acoes_educativas_pendentes = AtividadeGrupo.objects.filter(meta__isnull=False, tema__isnull=True, uo=get_uo(request.user), data_termino__lt=hoje)
        acoes_educativas_pendentes = acoes_educativas_pendentes.filter(Q(cadastrado_por=request.user) | Q(cadastrado_por__isnull=True))

        if acoes_educativas_pendentes.exists():
            qtd = acoes_educativas_pendentes.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Aç{} Educativa{}'.format(pluralize(qtd, 'ão,ões'), pluralize(qtd)),
                    subtitulo=f'Pendente{pluralize(qtd)} de registro de execução',
                    qtd=qtd,
                    url=f'/saude/visualizar_acoes_educativas/{acoes_educativas_pendentes[0].meta_id}/',
                )
            )

    return quadro


@layout.alerta()
def index_alertas(request):
    alertas = list()
    vinculo = request.user.get_vinculo()
    utiliza_passaporte_vacinal = Configuracao.get_valor_por_chave('saude', 'utiliza_passaporte_vacinal')
    if utiliza_passaporte_vacinal:
        tem_passaporte = PassaporteVacinalCovid.objects.filter(vinculo=vinculo)
        if not tem_passaporte.exists() or tem_passaporte.filter(recebeu_alguma_dose=False, termo_aceito_em=None, possui_atestado_medico=None, cartao_vacinal=None).exists() or tem_passaporte.filter(situacao_declaracao=PassaporteVacinalCovid.INDEFERIDA).exists():
            alertas.append(
                dict(
                    url='/saude/passaporte_vacinacao_covid/',
                    titulo='Preencha a <strong>Autodeclaração para o Passaporte Vacinal da COVID</strong>.',
                )
            )
        if tem_passaporte.filter(termo_aceito_em__isnull=False, situacao_passaporte=PassaporteVacinalCovid.INVALIDO).exists():
            registro = tem_passaporte.filter(termo_aceito_em__isnull=False, situacao_passaporte=PassaporteVacinalCovid.INVALIDO)[0]
            if not registro.data_expiracao or registro.data_expiracao < datetime.datetime.now():
                alertas.append(
                    dict(
                        url=f'/saude/cadastrar_resultado_teste/{registro.id}',
                        titulo='Faça o envio do <strong>resultado negativo de teste contra COVID.</strong>',
                    )
                )

    return alertas


def tem_permissao_acesso_atendimento_medico(user):
    if not user.groups.filter(name__in=Especialidades.GRUPOS):
        raise PermissionDenied()


def tem_permissao(atendimento, request):
    if not (atendimento.usuario_aberto == request.user):
        raise PermissionDenied()


def eh_do_grupo_medico_enf(user):
    return user.groups.filter(name__in=Especialidades.GRUPOS_ATENDIMENTO_MEDICO_ENF)


def eh_do_grupo_enf(user):
    return user.groups.filter(name__in=Especialidades.GRUPOS_ATENDIMENTO_ENF)


def nao_possui_dados_estatisticos(lista):
    if len(lista) == 1 and lista[0]['qtd'] == 0:
        return True
    return False


def pode_alterar_atendimento(atendimento, request):
    pode_fechar = False
    if atendimento.tipo == TipoAtendimento.ODONTOLOGICO and request.user.groups.filter(name__in=[Especialidades.ODONTOLOGO, Especialidades.TECNICO_SAUDE_BUCAL]):
        pode_fechar = True
    elif atendimento.tipo == TipoAtendimento.ENFERMAGEM_MEDICO and request.user.groups.filter(name__in=Especialidades.GRUPOS_ATENDIMENTO_MEDICO_ENF):
        pode_fechar = True
    elif atendimento.tipo == TipoAtendimento.AVALIACAO_BIOMEDICA and request.user.groups.filter(name__in=Especialidades.GRUPOS):
        pode_fechar = True
    elif atendimento.tipo == TipoAtendimento.PSICOLOGICO and atendimento.usuario_aberto == request.user:
        pode_fechar = True
    elif atendimento.tipo == TipoAtendimento.NUTRICIONAL and atendimento.usuario_aberto == request.user:
        pode_fechar = True
    elif atendimento.tipo == TipoAtendimento.FISIOTERAPIA and atendimento.usuario_aberto == request.user:
        pode_fechar = True
    elif atendimento.tipo == TipoAtendimento.MULTIDISCIPLINAR and atendimento.usuario_aberto == request.user:
        pode_fechar = True
    return pode_fechar


def get_ids_uos(user):
    uo_ids = list()
    if user.eh_aluno:
        aluno = user.get_relacionamento()
        if aluno.curso_campus.diretoria.ead and aluno.polo and aluno.polo.campus_atendimento:
            uo_ids.append(aluno.polo.campus_atendimento_id)
    else:
        if user.eh_servidor:
            servidor = user.get_relacionamento()
            setores = ()
            if servidor.setor_lotacao:
                if servidor.setor_lotacao.uo.equivalente:
                    setores += (servidor.setor_lotacao.uo.equivalente.id, )
                else:
                    setores += (servidor.setor_lotacao.uo_id,)
            if servidor.setor_exercicio:
                setores += (servidor.setor_exercicio.uo_id,)
            if servidor.setor:
                setores += (servidor.setor.uo_id,)
            for setor in servidor.setores_adicionais.all():
                setores += (setor.uo_id,)
            uos_atendimento = UnidadeOrganizacional.objects.filter(id__in=setores)
        else:
            uos_atendimento = UnidadeOrganizacional.objects.filter(id__in=HorarioAtendimento.objects.filter(cadastrado_por_vinculo=user.get_vinculo()).values_list('campus', flat=True))
        for uo in uos_atendimento:
            uo_ids.append(uo.id)
    uo_ids.append(get_uo(user).id)
    return uo_ids


def pode_validar_passaporte(request, passaporte):
    eh_intercampi = ValidadorIntercampi.objects.filter(vinculo=request.user.get_vinculo(), ativo=True)
    return (passaporte.uo == get_uo(request.user)) or request.user.groups.filter(name='Validador de Passaporte Vacinal Sistêmico').exists() or (eh_intercampi.exists() and passaporte.uo.id in eh_intercampi.values_list('campi', flat=True))


@rtr()
@group_required(Especialidades.GRUPOS_PRONTUARIO)
def prontuarios(request):
    title = 'Prontuários'

    form = BuscaProntuarioForm(request.GET or None)

    pessoas = None
    vinculo = None
    uo_atual = get_uo(request.user)

    atendimentos_multidisciplinares_abertos = Atendimento.objects.filter(
        tipo=TipoAtendimento.MULTIDISCIPLINAR, usuario_aberto__vinculo__setor__uo=uo_atual, situacao=SituacaoAtendimento.ABERTO
    ).order_by('prontuario__vinculo__pessoa__nome')

    prontuarios_encaminhados = Atendimento.objects.filter(
        condutamedica__encaminhado_enfermagem=True, condutamedica__atendido=False, usuario_aberto__vinculo__setor__uo=uo_atual
    ).order_by('prontuario__vinculo__pessoa__nome')

    prontuarios_encaminhados_fisioterapia = Atendimento.objects.filter(
        condutamedica__encaminhado_fisioterapia=True, condutamedica__atendido_fisioterapia=False, usuario_aberto__vinculo__setor__uo=uo_atual
    ).order_by('prontuario__vinculo__pessoa__nome')

    pode_criar_atendimento = eh_do_grupo_medico_enf(request.user)
    eh_enfermagem = eh_do_grupo_enf(request.user)
    especialidade = Especialidades(request.user)
    eh_medico = especialidade.is_medico()
    eh_dentista = especialidade.is_odontologo()
    eh_psicologo = especialidade.is_psicologo()
    eh_medico = especialidade.is_medico()
    eh_nutricionista = especialidade.is_nutricionista()
    eh_enfermeiro = especialidade.is_enfermeiro()
    eh_fisioterapeuta = especialidade.is_fisioterapeuta()

    atendimento_odonto_encaminhado = False
    if pode_criar_atendimento:
        prontuarios_abertos = Atendimento.objects.filter(
            tipo=TipoAtendimento.ENFERMAGEM_MEDICO, usuario_aberto__vinculo__setor__uo=uo_atual, situacao=SituacaoAtendimento.ABERTO
        ).order_by('prontuario__vinculo__pessoa__nome')
        if eh_enfermagem:
            atendimento_odonto_encaminhado = Atendimento.objects.filter(
                tipo=TipoAtendimento.ODONTOLOGICO, odontograma__encaminhado_enfermagem=True, odontograma__atendido=False, usuario_aberto__vinculo__setor__uo=uo_atual
            ).order_by('prontuario__vinculo__pessoa__nome')
    elif eh_dentista:
        prontuarios_abertos = Atendimento.objects.filter(tipo=TipoAtendimento.ODONTOLOGICO, usuario_aberto=request.user, situacao=SituacaoAtendimento.ABERTO).order_by(
            'prontuario__vinculo__pessoa__nome'
        )
    elif eh_psicologo:
        prontuarios_abertos = Atendimento.objects.filter(tipo=TipoAtendimento.PSICOLOGICO, usuario_aberto=request.user, situacao=SituacaoAtendimento.ABERTO).order_by(
            'prontuario__vinculo__pessoa__nome'
        )
    elif eh_nutricionista:
        prontuarios_abertos = Atendimento.objects.filter(tipo=TipoAtendimento.NUTRICIONAL, usuario_aberto=request.user, situacao=SituacaoAtendimento.ABERTO).order_by(
            'prontuario__vinculo__pessoa__nome'
        )
    elif eh_fisioterapeuta:
        prontuarios_abertos = Atendimento.objects.filter(tipo=TipoAtendimento.FISIOTERAPIA, usuario_aberto=request.user, situacao=SituacaoAtendimento.ABERTO).order_by(
            'prontuario__vinculo__pessoa__nome'
        )

    avaliacoes_biomedicas_abertas = Atendimento.objects.filter(
        tipo=TipoAtendimento.AVALIACAO_BIOMEDICA, situacao=SituacaoAtendimento.ABERTO, usuario_aberto__vinculo__setor__uo=uo_atual
    )
    avaliacoes_biomedicas_preenchidas_abertas = avaliacoes_biomedicas_abertas.filter(examefisico__isnull=False, sinaisvitais__isnull=False, odontograma__salvo=True)

    avaliacoes_biomedicas_pendentes = avaliacoes_biomedicas_preenchidas_abertas

    if eh_dentista:
        avaliacoes_biomedicas_pendentes = avaliacoes_biomedicas_pendentes | avaliacoes_biomedicas_abertas.filter(odontograma__salvo=False)
    if eh_medico:
        avaliacoes_biomedicas_pendentes = avaliacoes_biomedicas_pendentes | avaliacoes_biomedicas_abertas.filter(examefisico__isnull=True)

    if eh_enfermeiro:
        avaliacoes_biomedicas_pendentes = avaliacoes_biomedicas_pendentes | avaliacoes_biomedicas_abertas.filter(sinaisvitais__isnull=True)

    if avaliacoes_biomedicas_pendentes.exists():
        avaliacoes_biomedicas_pendentes = avaliacoes_biomedicas_pendentes.distinct()

    if form.is_valid():
        # Busca feita em Aluno para ser o Aluno selecionado ser usado futuramente nos atendimentos de cada especialidade
        if int(form.cleaned_data['vinculo']) == Vinculo.ALUNO:
            vinculo = Vinculo.ALUNO
            pessoas = (
                Aluno.objects.exclude(pessoa_fisica__cpf='	. . -')
                .filter(
                    Q(pessoa_fisica__nome__icontains=form.cleaned_data['paciente'])
                    | Q(pessoa_fisica__cpf__icontains=form.cleaned_data['paciente'])
                    | Q(matricula=form.cleaned_data['paciente'])
                )
                .order_by('pessoa_fisica__nome')
            )
        elif int(form.cleaned_data['vinculo']) == Vinculo.SERVIDOR:
            vinculo = Vinculo.SERVIDOR
            pessoas = Servidor.objects.filter(Q(nome__unaccent__icontains=form.cleaned_data['paciente']) | Q(matricula=form.cleaned_data['paciente'])).order_by('nome')
        elif int(form.cleaned_data['vinculo']) == Vinculo.PRESTADOR_SERVICO:
            vinculo = Vinculo.PRESTADOR_SERVICO
            pessoas = PrestadorServico.objects.filter(Q(excluido=False), Q(nome__icontains=form.cleaned_data['paciente']) | Q(cpf=form.cleaned_data['paciente'])).order_by('nome')
        elif int(form.cleaned_data['vinculo']) == Vinculo.COMUNIDADE_EXTERNA:
            vinculo = Vinculo.COMUNIDADE_EXTERNA
            pessoas = (
                PessoaExterna.objects.exclude(cpf='	. . -')
                .filter(Q(nome__icontains=form.cleaned_data['paciente']) | Q(pessoa_fisica__cpf__icontains=form.cleaned_data['paciente']))
                .order_by('nome')
            )

    vinculos = Vinculo
    pode_ver_prontuarios = True
    if request.user.groups.filter(name='Atendente'):
        pode_ver_prontuarios = False

    pode_gerenciar_atend_multidisciplinar = eh_dentista or eh_medico or eh_nutricionista

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def prontuario(request, id_vinculo):
    vinculo = get_object_or_404(VinculoPessoa, id=id_vinculo)
    vinculo_do_paciente = vinculo
    pessoa_fisica = vinculo.pessoa.pessoafisica
    if not pessoa_fisica.cpf_ou_cnpj_valido():
        return httprr("/saude/prontuarios/", 'O usuário não possui CPF válido.', tag='error')

    eh_grupo_medico_enf = eh_do_grupo_medico_enf(request.user)
    eh_dentista = request.user.groups.filter(name=Especialidades.ODONTOLOGO).exists()
    eh_tecnico_bucal = request.user.groups.filter(name=Especialidades.TECNICO_SAUDE_BUCAL).exists()

    situacao_atendimento = SituacaoAtendimento()
    vinculo_aluno = None
    vinculo_servidor = None
    tem_caracterizacao = None

    # Busca o prontuario da pessoa fisica
    prontuario = Prontuario.get_prontuario(vinculo)

    # Lista os vinculos ativos de uma pessoa fisica
    vinculos = Vinculo.get_vinculos(pessoa_fisica)
    tem_vinculo_externo = False
    tem_outros_vinculos_ativos = False
    for vinculo in vinculos:
        if vinculo.vinculo == Vinculo.COMUNIDADE_EXTERNA:
            tem_vinculo_externo = True
        else:
            tem_outros_vinculos_ativos = True

        if vinculo.vinculo == Vinculo.ALUNO:
            vinculo_aluno = vinculo
        elif vinculo.vinculo == Vinculo.SERVIDOR:
            vinculo_servidor = vinculo
    telefone = None
    if vinculo_aluno:
        telefone = vinculo_aluno.telefone_principal
        endereco = vinculo_aluno.get_endereco()
        email_do_aluno = vinculo_aluno.pessoa_fisica.email_secundario or vinculo_aluno.email_academico
        nome_responsavel = vinculo_aluno.responsavel
        email_responsavel = vinculo_aluno.email_responsavel
        tel_responsavel = vinculo_aluno.telefone_adicional_1
        from ae.models import Caracterizacao

        caracterizacao = Caracterizacao.objects.filter(aluno=vinculo_aluno)

        horario_atual = f'{datetime.datetime.now().hour}:{datetime.datetime.now().minute}'
        estah_em_horario_de_aula = vinculo_aluno.em_horario_de_aula(datetime.datetime.now().date(), horario_atual)
        if caracterizacao.exists():
            tem_caracterizacao = True
            renda_familiar = caracterizacao[0].renda_bruta_familiar
            moradia = caracterizacao[0].tipo_imovel_residencial
            escolaridade_mae = caracterizacao[0].mae_nivel_escolaridade.descricao
            escolaridade_pai = caracterizacao[0].pai_nivel_escolaridade.descricao
            qtd_pessoas_domicilio = caracterizacao[0].qtd_pessoas_domicilio
    elif vinculo_servidor:
        telefone = vinculo_servidor.telefones_pessoais
        endereco = vinculo_servidor.endereco
    eh_externo = tem_vinculo_externo and not tem_outros_vinculos_ativos
    tem_vinculos_anteriores = False
    if not tem_outros_vinculos_ativos:
        tem_vinculos_anteriores = (
            Aluno.objects.filter(pessoa_fisica__cpf=pessoa_fisica.cpf).exists()
            or Servidor.objects.filter(cpf=pessoa_fisica.cpf).exists()
            or PrestadorServico.objects.filter(cpf=pessoa_fisica.cpf).exists()
        )
    mostra_abas = tem_outros_vinculos_ativos or tem_vinculos_anteriores or not eh_externo

    title = f'Prontuário #{prontuario.id}'

    todos_atendimentos = Atendimento.objects.filter(prontuario__vinculo__pessoa__pessoafisica__cpf=pessoa_fisica.cpf).order_by('-data_aberto')

    # Lista as avaliacoes biomedicas
    atendimentos_avaliacao_biomedica = todos_atendimentos.filter(tipo=TipoAtendimento.AVALIACAO_BIOMEDICA).order_by('-data_aberto')

    # Lista os atendimentos Enfermagem/Medicina
    atendimentos_medico_enfermagem = todos_atendimentos.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO).order_by('-data_aberto')

    exames_laboratoriais = ExameLaboratorial.objects.filter(prontuario=prontuario).order_by('-data_realizado', 'categoria')
    exames_imagem = ExameImagem.objects.filter(prontuario=prontuario).order_by('-data_realizado', 'nome')

    # Lista os atendimentos Odontológicos
    atendimentos_odontologicos = todos_atendimentos.filter(tipo=TipoAtendimento.ODONTOLOGICO).order_by('-data_aberto')

    atendimentos_psicologicos = todos_atendimentos.filter(tipo=TipoAtendimento.PSICOLOGICO).order_by('-data_aberto')

    atendimentos_nutricionais = todos_atendimentos.filter(tipo=TipoAtendimento.NUTRICIONAL).order_by('-data_aberto')

    atendimentos_fisioterapia = todos_atendimentos.filter(tipo=TipoAtendimento.FISIOTERAPIA).order_by('-data_aberto')

    atendimentos_multidisciplinares = todos_atendimentos.filter(tipo=TipoAtendimento.MULTIDISCIPLINAR).order_by('-data_aberto')

    tem_alergia_alimentos = False
    tem_alergia_medicamentos = False
    tem_doenca_cronica = False
    tem_plano_odontologico = False
    eh_gestante = False
    processos_saude_doenca = ProcessoSaudeDoenca.objects.filter(atendimento__in=todos_atendimentos.values_list('id', flat=True))
    if processos_saude_doenca.exists():
        mais_recente = processos_saude_doenca.latest('id')
        tem_plano_odontologico = mais_recente.tem_plano_odontologico
        tem_alergia_alimentos = mais_recente.alergia_alimentos
        if tem_alergia_alimentos:
            quais_alergias_alimentos = mais_recente.que_alimentos
        tem_alergia_medicamentos = mais_recente.alergia_medicamentos
        if tem_alergia_medicamentos:
            quais_alergias_medicamentos = mais_recente.que_medicamentos
        tem_doenca_cronica = mais_recente.doencas_cronicas.all()
        if tem_doenca_cronica.exists():
            quais_doencas_cronicas = ''
            for doenca in tem_doenca_cronica:
                quais_doencas_cronicas += doenca.nome + ', '
            quais_doencas_cronicas = quais_doencas_cronicas[:-2]
        eh_gestante = mais_recente.gestante

    # Agrupamento dos registros de Vacina
    vacinas = CartaoVacinal.objects.filter(prontuario=prontuario).order_by('id')
    grupo_vacina = Vacina.objects.filter(id__in=prontuario.vacinas.all().distinct()).order_by('-id')
    grupos = []
    for grupo in grupo_vacina:
        lista = []
        for registro_vacina in vacinas:
            if registro_vacina.vacina_id == grupo.id:
                lista.append(registro_vacina)
        grupos.append(lista)

    # Verificando se existem vacinas em atraso ou próximas do prazo
    vacinas_atrasadas = False
    vacinas_proximas = False
    for registro_vacina in vacinas:
        if registro_vacina.data_prevista and not registro_vacina.data_vacinacao and not registro_vacina.sem_data and datetime.date.today() > registro_vacina.data_prevista:
            vacinas_atrasadas = True
        elif (
            registro_vacina.data_prevista
            and not registro_vacina.data_vacinacao
            and not registro_vacina.sem_data
            and datetime.date.today() + datetime.timedelta(days=15) >= registro_vacina.data_prevista
        ):
            vacinas_proximas = True

    anotacoes_disciplinares = AnotacaoInterdisciplinar.objects.filter(prontuario=prontuario).order_by('-data')
    eh_psicologo = request.user.groups.filter(name=Especialidades.PSICOLOGO)
    tem_anamnese_psicologica = False
    anamnese_psicologia_responsavel = False

    if eh_psicologo:
        anamnese_psicologia = AnamnesePsicologia.objects.filter(prontuario=prontuario, profissional=request.user)
        if anamnese_psicologia.exists():
            anamnese_psicologia = anamnese_psicologia[0]
            anamnese_psicologia_responsavel = anamnese_psicologia.get_responsavel()

    dados_exames = dict()

    categorias = CategoriaExameLaboratorial.objects.filter(
        tipoexamelaboratorial__isnull=False, id__in=ExameLaboratorial.objects.filter(prontuario=prontuario).values_list('categoria', flat=True)
    )

    for categoria in categorias:
        registros = dict()
        for item in ValorExameLaboratorial.objects.filter(exame__prontuario=prontuario, tipo__categoria=categoria).order_by('tipo__nome'):
            if not item.exame.sigiloso or (item.exame.sigiloso and item.exame.profissional == request.user.get_relacionamento()):
                chave = f'{item.tipo.nome} ({item.tipo.unidade})'
                registros[chave] = dict()
        meses = dict()

        for idx, exame in enumerate(ExameLaboratorial.objects.filter(prontuario=prontuario, categoria=categoria).order_by('data_realizado'), 1):
            if not exame.sigiloso or (exame.sigiloso and exame.profissional == request.user.get_relacionamento()):
                if str(format_(exame.data_realizado)) in meses.keys():
                    index = 1
                    for indice in list(meses.keys()):
                        if str(format_(exame.data_realizado)) in indice:
                            index += 1
                    chave_exame = '{} ({})'.format(exame.data_realizado.strftime("%d/%m/%Y"), index)
                else:
                    chave_exame = '{}'.format(exame.data_realizado.strftime("%d/%m/%Y"))
                meses[chave_exame] = dict()

            for item in ValorExameLaboratorial.objects.filter(exame=exame).order_by('tipo__nome'):
                if not item.exame.sigiloso or (item.exame.sigiloso and item.exame.profissional == request.user.get_relacionamento()):
                    chave = f'{item.tipo.nome} ({item.tipo.unidade})'
                    registros[chave][chave_exame] = f'{item.valor} {item.tipo.unidade}'

        meses_ordenados = collections.OrderedDict(sorted(list(meses.items()), reverse=True))
        registros_ordenados = collections.OrderedDict(sorted(list(registros.items()), key=lambda x: x[0]))
        dados_exames[categoria.nome] = dict(meses=meses_ordenados, registros=registros_ordenados)
    anotacoes_disciplinares = AnotacaoInterdisciplinar.objects.filter(prontuario=prontuario).order_by('-data')
    especialidade = Especialidades(request.user)

    eh_nutricionista = especialidade.is_nutricionista()
    eh_fisioterapeuta = especialidade.is_fisioterapeuta()
    pode_gerenciar_atend_multidisciplinar = eh_dentista or especialidade.is_medico() or eh_nutricionista

    documentos = DocumentoProntuario.objects.filter(prontuario=prontuario).order_by('-data')
    notificacao_covid = NotificacaoCovid.objects.filter(vinculo=vinculo_do_paciente).order_by('-id')
    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def abrir_atendimento(request, tipo_atendimento, prontuario_id, vinculo, vinculo_id):
    try:
        vinculo_obj = Vinculo.get_vinculo(vinculo, vinculo_id)
    except Exception:
        return HttpResponse(status=404)
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)

    try:
        if (isinstance(vinculo_obj, Aluno) and not vinculo_obj.situacao.ativo) or (isinstance(vinculo_obj, PrestadorServico) and not vinculo_obj.ativo):
            return httprr("/saude/prontuarios/", 'O perfil deste usuário está inativo.', tag="error")

        eh_grupo_medico_enf = eh_do_grupo_medico_enf(request.user)
        eh_dentista = request.user.groups.filter(name=Especialidades.ODONTOLOGO).exists()
        eh_tecnico_bucal = request.user.groups.filter(name=Especialidades.TECNICO_SAUDE_BUCAL).exists()
        eh_psicologo = request.user.groups.filter(name=Especialidades.PSICOLOGO).exists()
        eh_nutricionista = request.user.groups.filter(name=Especialidades.NUTRICIONISTA).exists()
        eh_medico = request.user.groups.filter(name=Especialidades.MEDICO).exists()
        eh_fisioterapeuta = request.user.groups.filter(name=Especialidades.FISIOTERAPEUTA).exists()
        pode_gerenciar_atend_multidisciplinar = eh_dentista or eh_medico or eh_nutricionista

        tipo_atendimento = TipoAtendimento.TIPO_ATENDIMENTO.get(int(tipo_atendimento))

        pode_abrir_atendimento = True
        if tipo_atendimento == TipoAtendimento.ENFERMAGEM_MEDICO and not eh_grupo_medico_enf:
            pode_abrir_atendimento = False
        elif tipo_atendimento == TipoAtendimento.ODONTOLOGICO and not (eh_dentista or eh_tecnico_bucal):
            pode_abrir_atendimento = False
        elif tipo_atendimento == TipoAtendimento.PSICOLOGICO and not eh_psicologo:
            pode_abrir_atendimento = False
        elif tipo_atendimento == TipoAtendimento.NUTRICIONAL and not eh_nutricionista:
            pode_abrir_atendimento = False
        elif tipo_atendimento == TipoAtendimento.FISIOTERAPIA and not eh_fisioterapeuta:
            pode_abrir_atendimento = False
        elif tipo_atendimento == TipoAtendimento.MULTIDISCIPLINAR and not pode_gerenciar_atend_multidisciplinar:
            pode_abrir_atendimento = False

        if not pode_abrir_atendimento:
            return httprr("/saude/prontuarios/", 'Você não pode abrir este tipo de atendimento.', tag='error')

        atendimento = Atendimento.abrir(TipoAtendimento.TIPO_ATENDIMENTO.get(int(tipo_atendimento)), prontuario, vinculo_obj, request.user)

        if atendimento.is_atendimento_avaliacao_biomedica():
            return httprr(f"/saude/avaliacao_biomedica/{atendimento.id}/", 'Avaliação biomédica gerada com sucesso.')
        elif atendimento.is_atendimento_enfermagem_medico():
            return httprr(f"/saude/atendimento_medico_enfermagem/{atendimento.id}/", 'Atendimento Médico/Enfermagem gerado com sucesso.')
        elif atendimento.is_atendimento_odontologico():
            return httprr(f"/saude/atendimento_odontologico/{atendimento.id}/", 'Atendimento Odontológico gerado com sucesso.')
        elif atendimento.is_atendimento_psicologico():
            return httprr(f"/saude/atendimento_psicologico/{atendimento.id}/", 'Atendimento Psicológico gerado com sucesso.')
        elif atendimento.is_atendimento_nutricional():
            return httprr(f"/saude/atendimento_nutricional/{atendimento.id}/", 'Atendimento Nutricional gerado com sucesso.')
        elif atendimento.is_atendimento_fisioterapia():
            return httprr(f"/saude/atendimento_fisioterapia/{atendimento.id}/", 'Atendimento de Fisioterapia gerado com sucesso.')

        elif atendimento.is_atendimento_multidisciplinar():
            return httprr(f"/saude/atendimento_multidisciplinar/{atendimento.id}/", 'Atendimento Multidisciplinar gerado com sucesso.')

    except ValidationError as e:
        return httprr(f"/saude/prontuario/{prontuario.vinculo_id}/", ''.join(e.messages), tag="error")


@rtr()
@group_required(Especialidades.GRUPOS)
def fechar_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Fechar Atendimento - {atendimento.get_vinculo()}'
    pode_fechar = pode_alterar_atendimento(atendimento, request)

    if not pode_fechar:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/", 'Você não tem permissão para fechar este atendimento.', tag='error')
    msgs_erro = atendimento.tem_pendencia(request)
    if msgs_erro:
        for msg in msgs_erro:
            messages.add_message(request, messages.ERROR, msg)

    if msgs_erro:
        if atendimento.tipo == TipoAtendimento.AVALIACAO_BIOMEDICA:
            return httprr(f"/saude/avaliacao_biomedica/{atendimento.id}/")
        elif atendimento.tipo == TipoAtendimento.ENFERMAGEM_MEDICO:
            return httprr(f"/saude/atendimento_medico_enfermagem/{atendimento.id}/")
        elif atendimento.tipo == TipoAtendimento.ODONTOLOGICO:
            return httprr(f"/saude/atendimento_odontologico/{atendimento.id}/")
        elif atendimento.tipo == TipoAtendimento.PSICOLOGICO:
            return httprr(f"/saude/atendimento_psicologico/{atendimento.id}/")
        elif atendimento.tipo == TipoAtendimento.NUTRICIONAL:
            return httprr(f"/saude/atendimento_nutricional/{atendimento.id}/")
        elif atendimento.tipo == TipoAtendimento.FISIOTERAPIA:
            return httprr(f"/saude/atendimento_fisioterapia/{atendimento.id}/")
        elif atendimento.tipo == TipoAtendimento.MULTIDISCIPLINAR:
            return httprr(f"/saude/atendimento_multidisciplinar/{atendimento.id}/")

    encerra_plano_tratamento = False
    if atendimento.tipo == TipoAtendimento.ODONTOLOGICO:
        if ProcedimentoOdontologico.objects.filter(tipo_consulta=ProcedimentoOdontologico.CONCLUSAO_TRATAMENTO, atendimento=atendimento).exists():
            encerra_plano_tratamento = True

    nao_informou_tipo_consulta = Odontograma.objects.filter(atendimento=atendimento, tipo_consulta__isnull=True).exists()

    form = FecharAtendimentoForm(request.POST or None, instance=atendimento, request=request)
    if form.is_valid():
        atendimento.fechar(request)
        msg_sucesso = 'Atendimento fechado com sucesso.'
        if atendimento.tipo == TipoAtendimento.AVALIACAO_BIOMEDICA:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_avaliacao_biomedica", msg_sucesso)
        elif atendimento.tipo == TipoAtendimento.ENFERMAGEM_MEDICO:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_medico_enfermagem", msg_sucesso)
        elif atendimento.tipo == TipoAtendimento.ODONTOLOGICO:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_odontologico", msg_sucesso)
        elif atendimento.tipo == TipoAtendimento.PSICOLOGICO:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_psicologico", msg_sucesso)
        elif atendimento.tipo == TipoAtendimento.NUTRICIONAL:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_nutricional", msg_sucesso)
        elif atendimento.tipo == TipoAtendimento.FISIOTERAPIA:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_fisioterapia", msg_sucesso)
        elif atendimento.tipo == TipoAtendimento.MULTIDISCIPLINAR:
            return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_multidisciplinar", msg_sucesso)

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def cancelar_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    pode_fechar = pode_alterar_atendimento(atendimento, request)

    if not pode_fechar:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/", 'Você não tem permissão para cancelar este atendimento.', tag='error')

    title = f'Fechar Atendimento - {atendimento.get_vinculo()}'

    form = CancelarAtendimentoForm(request.POST or None, instance=atendimento, request=request)
    if form.is_valid():
        atendimento.cancelar(request)
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/", 'Atendimento cancelado com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def historico_ficha(request, atendimento_id, ficha):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    if atendimento.tipo == TipoAtendimento.ENFERMAGEM_MEDICO and not eh_do_grupo_medico_enf(request.user):
        raise PermissionDenied()

    default_exclude = ('id', 'data_cadastro', 'atendimento_id', 'profissional_id')
    if ficha == '1':
        default_exclude = ('id', 'data_cadastro', 'atendimento_id', 'profissional_id', 'temperatura', 'respiracao')
    elif ficha == '4':
        default_exclude = ('id', 'data_cadastro', 'atendimento_id', 'profissional_id', 'outras_drogas')

    MODEL_LIST = (
        SinaisVitais,
        Antropometria,
        AcuidadeVisual,
        HabitosDeVida,
        DesenvolvimentoPessoal,
        ExameFisico,
        PercepcaoSaudeBucal,
        Motivo,
        Anamnese,
        HipoteseDiagnostica,
        CondutaMedica,
    )

    MODEL_X = {
        1: {'modelo': SinaisVitais, 'fields': [f.get_attname() for f in SinaisVitais._meta.get_fields() if f.get_attname() not in default_exclude], 'titulo': 'Sinais Vitais'},
        2: {'modelo': Antropometria, 'fields': [f.get_attname() for f in Antropometria._meta.get_fields() if f.get_attname() not in default_exclude], 'titulo': 'Antropometria'},
        3: {
            'modelo': AcuidadeVisual,
            'fields': [f.get_attname() for f in AcuidadeVisual._meta.get_fields() if f.get_attname() not in default_exclude],
            'titulo': 'Acuidade Visual',
        },
        4: {
            'modelo': HabitosDeVida,
            'fields': [f.get_attname() for f in HabitosDeVida._meta.get_fields() if f.get_attname() not in default_exclude],
            'titulo': 'Hábitos de Vida',
        },
        5: {
            'modelo': DesenvolvimentoPessoal,
            'fields': [f.get_attname() for f in DesenvolvimentoPessoal._meta.get_fields() if f.get_attname() not in default_exclude],
            'titulo': 'Desenvolvimento Pessoal',
        },
        6: {'modelo': ExameFisico, 'fields': [f.get_attname() for f in ExameFisico._meta.get_fields() if f.get_attname() not in default_exclude], 'titulo': 'Exame Pessoal'},
        7: {
            'modelo': PercepcaoSaudeBucal,
            'fields': [f.get_attname() for f in PercepcaoSaudeBucal._meta.get_fields() if f.get_attname() not in default_exclude],
            'titulo': 'Percepção de Saúde Bucal',
        },
        8: {'modelo': Motivo, 'fields': [f.get_attname() for f in Motivo._meta.get_fields() if f.get_attname() not in default_exclude], 'titulo': 'Motivo do Atendimento'},
        9: {'modelo': Anamnese, 'fields': [f.get_attname() for f in Anamnese._meta.get_fields() if f.get_attname() not in default_exclude], 'titulo': 'Anamnese'},
        10: {
            'modelo': HipoteseDiagnostica,
            'fields': [f.get_attname() for f in HipoteseDiagnostica._meta.get_fields() if f.get_attname() not in default_exclude],
            'titulo': 'Hipótese Diagnóstica',
        },
    }

    # Seleciona o modelo de acordo com os parametros
    model_dict = MODEL_X.get(ficha)

    title = 'Histórico - {}'.format(model_dict.pop('titulo'))
    Klass = model_dict.pop('modelo')

    historico = Klass.objects.filter(atendimento=atendimento.pk).order_by('-id')

    # Campos básicos do histórico
    if not 'custom_fields' in model_dict:
        model_dict['custom_fields'] = dict(get_cadastro_display=Column('Cadastrado por', accessor="get_cadastro_display"))
    if not 'sequence' in model_dict:
        model_dict['sequence'] = model_dict['fields'] + ['get_cadastro_display']

    # Monta a tabela
    table_historico = get_table(queryset=historico, **model_dict)

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def avaliacao_biomedica(request, atendimento_id):
    title = 'Avaliação Biomédica'

    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.AVALIACAO_BIOMEDICA)
    situacoes_atendimento = SituacaoAtendimento()

    if atendimento.aluno:
        programas = Participacao.objects.filter(aluno=atendimento.get_vinculo(), data_termino__isnull=True)

    # Avaliação Biomedica
    sinaisvitais = SinaisVitais.objects.filter(atendimento=atendimento)
    sinaisvitais_titulo = 'Sinais Vitais'
    sinaisvitais_count = sinaisvitais.count()
    sinaisvitais_responsavel = None
    if sinaisvitais.exists():
        sinaisvitais = sinaisvitais.latest('id')
        sinaisvitais_responsavel = sinaisvitais.get_responsavel()

    antropometria = Antropometria.objects.filter(atendimento=atendimento)
    antropometria_titulo = 'Antropometria'
    antropometria_count = antropometria.count()
    if antropometria.exists():
        antropometria = antropometria.latest('id')
        antropometria_responsavel = antropometria.get_responsavel()

    acuidadevisual = AcuidadeVisual.objects.filter(atendimento=atendimento)
    acuidadevisual_titulo = 'Acuidade Visual'
    acuidadevisual_count = acuidadevisual.count()
    if acuidadevisual.exists():
        acuidadevisual = acuidadevisual.latest('id')
        acuidadevisual_responsavel = acuidadevisual.get_responsavel()

    cadastrou_antecedentes = False
    cadastrou_processosaudedoenca = False
    antecedentesfamiliares = AntecedentesFamiliares.objects.filter(atendimento=atendimento)
    antecedentesfamiliares_titulo = 'Antecedentes'
    antecedentesfamiliares_count = antecedentesfamiliares.count()
    if antecedentesfamiliares.exists():
        cadastrou_antecedentes = True
        antecedentesfamiliares = antecedentesfamiliares.latest('id')
        antecedentesfamiliares_responsavel = antecedentesfamiliares.get_responsavel()

    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento)
    processosaudedoenca_titulo = 'Processo Saúde-Doença'
    processosaudedoenca_count = processosaudedoenca.count()
    if processosaudedoenca.exists():
        cadastrou_processosaudedoenca = True
        processosaudedoenca = processosaudedoenca.latest('id')
        processosaudedoenca_responsavel = processosaudedoenca.get_responsavel()

    aba_antecedentes_preenchida = cadastrou_antecedentes and cadastrou_processosaudedoenca

    habitosdevida = HabitosDeVida.objects.filter(atendimento=atendimento)
    habitosdevida_titulo = 'Hábitos de Vida'
    habitosdevida_count = habitosdevida.count()
    if habitosdevida.exists():
        habitosdevida = habitosdevida.latest('id')
        habitosdevida_responsavel = habitosdevida.get_responsavel()

    desenvolvimentopessoal = DesenvolvimentoPessoal.objects.filter(atendimento=atendimento)
    desenvolvimentopessoal_titulo = 'Desenvolvimento Pessoal'
    desenvolvimentopessoal_count = desenvolvimentopessoal.count()
    if desenvolvimentopessoal.exists():
        desenvolvimentopessoal = desenvolvimentopessoal.latest('id')
        desenvolvimentopessoal_responsavel = desenvolvimentopessoal.get_responsavel()

    examefisico = ExameFisico.objects.filter(atendimento=atendimento)
    examefisico_titulo = 'Exame Físico'
    examefisico_count = examefisico.count()
    if examefisico.exists():
        examefisico = examefisico.latest('id')
        examefisico_responsavel = examefisico.get_responsavel()

    percepcaosaudebucal = PercepcaoSaudeBucal.objects.filter(atendimento=atendimento)
    percepcaosaudebucal_titulo = 'Percepção da Saúde Bucal'
    percepcaosaudebucal_count = percepcaosaudebucal.count()
    if percepcaosaudebucal.exists():
        percepcaosaudebucal = percepcaosaudebucal.latest('id')
        percepcaosaudebucal_responsavel = percepcaosaudebucal.get_responsavel()

    odontograma = Odontograma.objects.filter(atendimento=atendimento)
    odontograma_titulo = 'Odontograma'
    odontograma_count = odontograma.count()
    if odontograma.exists():
        odontograma = odontograma.latest('id')
        odontograma_responsavel = odontograma.get_responsavel()
        situacoes = SituacaoClinica.objects.all()
        alteracoes = list()
        controla_itens = list()

        for item in odontograma.dentes_alterados_lista():
            id_situacao = item[7:]

            if int(id_situacao) in [
                SituacaoClinica.EXODONTIA_POR_OUTROS_MOTIVOS,
                SituacaoClinica.EXODONTIA_POR_CARIE,
                SituacaoClinica.DENTE_AUSENTE_EXTRAIDO_OUTRAS_RAZOES,
                SituacaoClinica.DENTE_EXTRAIDO_CARIE,
            ]:
                dente = item[4:6]

                if item[4:8] not in controla_itens:
                    if '_V_' in item[:-3]:
                        face = 'Vestibular'

                    elif '_P_' in item[:-3]:
                        face = 'Palatal/Lingual'

                    elif '_M_' in item[:-3]:
                        face = 'Mesial'

                    elif '_D_' in item[:-3]:
                        face = 'Distal'

                    elif '_O_' in item[:-3]:
                        face = 'Oclusal/Incisal'

                    elif '_C_' in item[:-3]:
                        face = 'Cervical'

                    elif '_R_' in item[:-3]:
                        face = 'Raiz'

                    for outro in odontograma.dentes_alterados_lista():
                        if outro[:-3] != item[:-3] and outro[4:8] == item[4:8]:
                            if '_V_' in outro[:-3]:
                                face += ', Vestibular'

                            elif '_P_' in outro[:-3]:
                                face += ', Palatal/Lingual'

                            elif '_M_' in outro[:-3]:
                                face += ', Mesial'

                            elif '_D_' in outro[:-3]:
                                face += ', Distal'

                            elif '_O_' in outro[:-3]:
                                face += ', Oclusal/Incisal'

                            elif '_C_' in outro[:-3]:
                                face += ', Cervical'

                            elif '_R_' in outro[:-3]:
                                face += ', Raiz'

                    controla_itens.append(item[4:8])
                    situacao = SituacaoClinica.objects.get(id=id_situacao)
                    alteracoes.append({'dente': dente, 'situacao': situacao, 'face': face})
            else:
                dente = item[4:6]
                if '_V_' in item[:-3]:
                    face = 'Vestibular'
                if '_P_' in item[:-3]:
                    face = 'Palatal/Lingual'
                if '_M_' in item[:-3]:
                    face = 'Mesial'
                if '_D_' in item[:-3]:
                    face = 'Distal'
                if '_O_' in item[:-3]:
                    face = 'Oclusal/Incisal'
                if '_C_' in item[:-3]:
                    face = 'Cervical'
                if '_R_' in item[:-3]:
                    face = 'Raiz'

                situacao = SituacaoClinica.objects.get(id=id_situacao)
                alteracoes.append({'dente': dente, 'situacao': situacao, 'face': face})

    informacoes_adicionais = InformacaoAdicional.objects.filter(atendimento=atendimento)
    informacoesadicionais_count = informacoes_adicionais.count()
    exames_periodontais = ExamePeriodontal.objects.filter(atendimento=atendimento).order_by('sextante')
    if exames_periodontais.exists():
        exames_periodontais_responsavel = exames_periodontais.latest('id').get_responsavel()
    avaliacoes_tecidos = ExameEstomatologico.objects.filter(atendimento=atendimento)
    if avaliacoes_tecidos.exists():
        avaliacoes_tecidos = avaliacoes_tecidos.latest('id')
        avaliacoes_tecidos_responsavel = avaliacoes_tecidos.get_responsavel()
    is_coordenador_sistemico = in_group(request.user, 'Coordenador de Saúde Sistêmico')
    especialidade = Especialidades(request.user)

    return locals()


@rtr()
@group_required(['Médico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Odontólogo'])
def adicionar_sinaisvitais(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    title = f'Adicionar Sinais Vitais - {atendimento.get_vinculo()}'

    sinaisvitais = SinaisVitais()
    sinaisvitais.profissional = request.user
    sinaisvitais.data_cadastro = datetime.datetime.now()
    sinaisvitais.atendimento = atendimento

    form = SinaisVitaisForm(request.POST or None, instance=sinaisvitais, request=request, initial={'temperatura_categoria': '2'})

    if form.is_valid():
        form.save()
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_sinais_vitais', 'Sinais Vitais registrados com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Nutricionista'])
def adicionar_antropometria(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Antropometria - {atendimento.get_vinculo()}'
    antropometria = Antropometria.objects.filter(atendimento=atendimento.pk)

    if antropometria.exists():
        antropometria = antropometria.latest('id')
        antropometria.id = None
    else:
        antropometria = Antropometria()

    antropometria.profissional = request.user
    antropometria.data_cadastro = datetime.datetime.now()
    antropometria.atendimento = atendimento

    form = AntropometriaForm(request.POST or None, instance=antropometria, request=request)

    if form.is_valid():
        form.save()
        if atendimento.is_atendimento_avaliacao_biomedica():
            return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_antropometria', 'Antropometria registrada com sucesso.')
        elif atendimento.is_atendimento_nutricional():
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Antropometria registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem'])
def adicionar_acuidadevisual(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Acuidade Visual - {atendimento.get_vinculo()}'
    acuidadevisual = AcuidadeVisual.objects.filter(atendimento=atendimento.pk)

    if acuidadevisual.exists():
        acuidadevisual = acuidadevisual.latest('id')
        acuidadevisual.id = None
    else:
        acuidadevisual = AcuidadeVisual()

    acuidadevisual.profissional = request.user
    acuidadevisual.data_cadastro = datetime.datetime.now()
    acuidadevisual.atendimento = atendimento

    form = AcuidadeVisualForm(request.POST or None, instance=acuidadevisual, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_acuidade_visual', 'Acuidade visual registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def adicionar_antecedentesfamiliares(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    especialidade = Especialidades(request.user)
    is_acesso_avaliacao_biomedica = atendimento.is_atendimento_avaliacao_biomedica() and (
        especialidade.is_medico()
        or especialidade.is_enfermeiro()
        or especialidade.is_tecnico_enfermagem()
        or especialidade.is_odontologo()
        or especialidade.is_fisioterapeuta()
        or especialidade.is_nutricionista()
        or especialidade.is_auxiliar_enfermagem()
    )
    is_acesso_atendimento_enfermagem_medico = atendimento.is_atendimento_enfermagem_medico() and especialidade.is_medico()
    is_acesso_atendimento_odontologico = atendimento.is_atendimento_odontologico() and especialidade.is_odontologo()
    is_acesso_atendimento_nutricional = atendimento.is_atendimento_nutricional() and especialidade.is_nutricionista()
    is_acesso_atendimento_fisioterapia = atendimento.is_atendimento_fisioterapia() and especialidade.is_fisioterapeuta()
    if (
        not is_acesso_avaliacao_biomedica
        and not is_acesso_atendimento_enfermagem_medico
        and not is_acesso_atendimento_odontologico
        and not is_acesso_atendimento_nutricional
        and not is_acesso_atendimento_fisioterapia
        and not atendimento.is_atendimento_multidisciplinar()
    ):
        return HttpResponseForbidden()

    title = f'Adicionar Antecedentes Familiares - {atendimento.get_vinculo()}'
    antecedentesfamiliares = AntecedentesFamiliares.objects.filter(atendimento=atendimento.pk)

    if antecedentesfamiliares.exists():
        antecedentesfamiliares = antecedentesfamiliares.latest('id')
    else:
        antecedentesfamiliares = AntecedentesFamiliares()

    antecedentesfamiliares.atendimento = atendimento
    antecedentesfamiliares.profissional = request.user
    antecedentesfamiliares.data_cadastro = datetime.datetime.now()

    form = AntecedentesFamiliaresForm(request.POST or None, instance=antecedentesfamiliares, request=request)

    if form.is_valid():
        form.save()
        if atendimento.is_atendimento_avaliacao_biomedica():
            return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_antecedentes', 'Antecedentes familiares registrados com sucesso.')
        elif atendimento.is_atendimento_enfermagem_medico():
            return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_antecedentes', 'Antecedentes familiares registrados com sucesso.')
        elif atendimento.is_atendimento_odontologico():
            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_antecedentes', 'Antecedentes familiares registrados com sucesso.')
        elif atendimento.is_atendimento_nutricional():
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_dados_clinicos', 'Antecedentes familiares registrados com sucesso.')
        elif atendimento.is_atendimento_fisioterapia():
            return httprr(f'/saude/atendimento_fisioterapia/{atendimento.id}/?tab=aba_antecedentes', 'Antecedentes familiares registrados com sucesso.')
        elif atendimento.is_atendimento_multidisciplinar():
            return httprr(f'/saude/atendimento_multidisciplinar/{atendimento.id}/?tab=aba_antecedentes', 'Antecedentes familiares registrados com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def adicionar_processosaudedoenca(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    especialidade = Especialidades(request.user)
    is_acesso_avaliacao_biomedica = atendimento.is_atendimento_avaliacao_biomedica() and (
        especialidade.is_medico()
        or especialidade.is_enfermeiro()
        or especialidade.is_tecnico_enfermagem()
        or especialidade.is_odontologo()
        or especialidade.is_fisioterapeuta()
        or especialidade.is_nutricionista()
    )
    is_acesso_atendimento_enfermagem_medico = atendimento.is_atendimento_enfermagem_medico() and (
        especialidade.is_medico() or especialidade.is_enfermeiro() or especialidade.is_tecnico_enfermagem() or especialidade.is_auxiliar_enfermagem()
    )
    is_acesso_atendimento_odontologico = atendimento.is_atendimento_odontologico() and especialidade.is_odontologo()
    is_acesso_atendimento_nutricional = atendimento.is_atendimento_nutricional() and especialidade.is_nutricionista()
    is_acesso_atendimento_fisioterapia = atendimento.is_atendimento_fisioterapia() and especialidade.is_fisioterapeuta()
    if (
        not is_acesso_avaliacao_biomedica
        and not is_acesso_atendimento_enfermagem_medico
        and not is_acesso_atendimento_odontologico
        and not is_acesso_atendimento_nutricional
        and not is_acesso_atendimento_fisioterapia
        and not atendimento.is_atendimento_multidisciplinar()
    ):
        return HttpResponseForbidden()

    title = f'Processo Saúde-Doença - {atendimento.get_vinculo()}'
    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento.pk)

    if processosaudedoenca.exists():
        processosaudedoenca = processosaudedoenca.latest('id')

    elif is_acesso_avaliacao_biomedica:
        atendimento_mais_recente = Atendimento.objects.filter(processosaudedoenca__isnull=False, prontuario=atendimento.prontuario, situacao=SituacaoAtendimento.FECHADO).order_by(
            '-data_fechado'
        )
        if atendimento_mais_recente.exists():
            processosaudedoenca = atendimento_mais_recente[0].processosaudedoenca_set.all()[0]
        else:
            processosaudedoenca = ProcessoSaudeDoenca()

    else:
        processosaudedoenca = ProcessoSaudeDoenca()

    processosaudedoenca.profissional = request.user
    processosaudedoenca.data_cadastro = datetime.datetime.now()
    processosaudedoenca.atendimento = atendimento

    form = ProcessoSaudeDoencaForm(request.POST or None, instance=processosaudedoenca, sexo=atendimento.get_pessoa_fisica_vinculo().sexo, request=request)

    if form.is_valid():
        form.save()
        if atendimento.is_atendimento_avaliacao_biomedica():
            return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_antecedentes', 'Processo Saúde-Doença registrado com sucesso.')
        elif atendimento.is_atendimento_enfermagem_medico():
            return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_antecedentes', 'Processo Saúde-Doença registrado com sucesso.')
        elif atendimento.is_atendimento_odontologico():
            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_antecedentes', 'Processo Saúde-Doença registrado com sucesso.')
        elif atendimento.is_atendimento_nutricional():
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_dados_clinicos', 'Processo Saúde-Doença registrado com sucesso.')
        elif atendimento.is_atendimento_fisioterapia():
            return httprr(f'/saude/atendimento_fisioterapia/{atendimento.id}/?tab=aba_antecedentes', 'Antecedentes familiares registrados com sucesso.')
        elif atendimento.is_atendimento_multidisciplinar():
            return httprr(f'/saude/atendimento_multidisciplinar/{atendimento.id}/?tab=aba_antecedentes', 'Processo Saúde-Doença registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def adicionar_habitosdevida(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Hábitos de Vida - {atendimento.get_vinculo()}'
    habitosdevida = HabitosDeVida.objects.filter(atendimento=atendimento.pk)

    if habitosdevida.exists():
        habitosdevida = habitosdevida.latest('id')
    else:
        habitosdevida = HabitosDeVida()

    habitosdevida.profissional = request.user
    habitosdevida.data_cadastro = datetime.datetime.now()
    habitosdevida.atendimento = atendimento

    form = HabitosDeVidaForm(request.POST or None, instance=habitosdevida, request=request)

    if form.is_valid():
        form.save()
        if atendimento.is_atendimento_avaliacao_biomedica():

            return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_habitosdevida', 'Hábitos de Vida registrados com sucesso.')
        elif atendimento.is_atendimento_nutricional():
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Hábitos de Vida registrados com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Técnico em Saúde Bucal'])
def adicionar_percepcaosaudebucal(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Percepção Bucal - {atendimento.get_vinculo()}'
    percepcaosaudebucal = PercepcaoSaudeBucal.objects.filter(atendimento=atendimento.pk)

    if percepcaosaudebucal.exists():
        percepcaosaudebucal = percepcaosaudebucal.latest('id')
        percepcaosaudebucal.id = None
    else:
        percepcaosaudebucal = PercepcaoSaudeBucal()

    percepcaosaudebucal.profissional = request.user
    percepcaosaudebucal.data_cadastro = datetime.datetime.now()
    percepcaosaudebucal.atendimento = atendimento

    form = PercepcaoSaudeBucalForm(request.POST or None, instance=percepcaosaudebucal, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_percepcaosaudebucal', 'Percepção de Saúde Bucal registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Psicólogo'])
def adicionar_desenvolvimentopessoal(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Desenvolvimento Pessoal - {atendimento.get_vinculo()}'
    desenvolvimentopessoal = DesenvolvimentoPessoal.objects.filter(atendimento=atendimento.pk)

    if desenvolvimentopessoal.exists():
        desenvolvimentopessoal = desenvolvimentopessoal.latest('id')
        desenvolvimentopessoal.id = None
    else:
        desenvolvimentopessoal = DesenvolvimentoPessoal()

    desenvolvimentopessoal.profissional = request.user
    desenvolvimentopessoal.data_cadastro = datetime.datetime.now()
    desenvolvimentopessoal.atendimento = atendimento

    form = DesenvolvimentoPessoalForm(request.POST or None, instance=desenvolvimentopessoal, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_desenvolvimentopessoal', 'Desenvolvimento Pessoal registrado com sucesso.')

    return locals()


@rtr()
@group_required('Médico')
def adicionar_examefisico(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Exame Físico - {atendimento.get_vinculo()}'
    examefisico = ExameFisico.objects.filter(atendimento=atendimento.pk)

    if examefisico.exists():
        examefisico = examefisico.latest('id')
        examefisico.id = None
    else:
        examefisico = ExameFisico()

    examefisico.profissional = request.user
    examefisico.data_cadastro = datetime.datetime.now()
    examefisico.atendimento = atendimento

    especialidade = Especialidades(request.user)
    form = ExameFisicoForm(request.POST or None, instance=examefisico, medico=especialidade.is_medico(), request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_examefisico', 'Exame Físico registrado com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def antropometria_valores_referencia(request):
    title = "Valores de Referência"

    return locals()


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def registrar_vacinacao(request, vacinacao_id):
    vacinacao = get_object_or_404(CartaoVacinal, pk=vacinacao_id)

    title = 'Registro de Vacinação'

    form = RegistrarVacinacaoForm(request.POST or None, instance=vacinacao)
    if form.is_valid():
        if not vacinacao.profissional:
            vacinacao.profissional = Servidor.objects.get(pk=request.user.get_profile().id)
        else:
            # Valida se a pessoa que está alterando a vacina foi a mesma pessoa que a registrou originalmente
            if not vacinacao.pode_alterar_registro_vacina(request.user):
                return httprr('.', 'Esse registro de vacina só pode ser alterado pelo usuário que o registrou.', tag='error')

        vacinacao.externo = form.cleaned_data['externo']
        vacinacao.sem_data = form.cleaned_data['sem_data']
        data_vacinacao = form.cleaned_data['data']
        obs = form.cleaned_data['obs']

        vacinacao_anterior = CartaoVacinal.objects.filter(vacina=vacinacao.vacina, prontuario=vacinacao.prontuario, data_vacinacao__isnull=False, id__lt=vacinacao.id).exclude(
            pk=vacinacao.pk
        )
        if vacinacao_anterior:
            vacinacao_anterior = vacinacao_anterior.order_by('-data_vacinacao')[0]
            if data_vacinacao:
                if vacinacao_anterior.data_vacinacao and vacinacao_anterior.data_vacinacao > data_vacinacao:
                    return httprr('.', 'A data de aplicação deve ser maior ou igual a {}.'.format(vacinacao_anterior.data_vacinacao.strftime("%d/%m/%Y")), tag='error')

        if not vacinacao.sem_data and not data_vacinacao:
            return httprr('.', 'Você deve informar uma data de vacinação.', tag='error')
        elif not vacinacao.sem_data and data_vacinacao:
            vacinacao.data_vacinacao = form.cleaned_data['data']

        vacinacao.obs = obs
        vacinacao.save()
        return httprr('..', 'Registro de vacinação adicionado com sucesso.')

    return locals()


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem'])
def registrar_previsao(request, vacinacao_id):
    title = 'Registro de Previsão de Vacinação'
    vacinacao = get_object_or_404(CartaoVacinal, pk=vacinacao_id)

    form = RegistrarPrevisaoVacinacaoForm(request.POST or None, instance=vacinacao)
    if form.is_valid():
        previsao = form.cleaned_data['previsao']
        vacinacao.data_prevista = previsao

        vacinacao_anterior = CartaoVacinal.objects.filter(vacina=vacinacao.vacina, prontuario=vacinacao.prontuario, data_prevista__isnull=False, id__lt=vacinacao.id).exclude(
            pk=vacinacao.pk
        )
        if vacinacao_anterior:
            vacinacao_anterior = vacinacao_anterior.order_by('-data_prevista')[0]
            if vacinacao_anterior.data_prevista and vacinacao_anterior.data_prevista > previsao:
                return httprr('.', 'O aprazamento deve ter data maior ou igual a {}.'.format(vacinacao_anterior.data_prevista.strftime("%d/%m/%Y")), tag='error')
            else:
                vacinacao.save()
        else:
            vacinacao.save()

        return httprr('..', 'Aprazamento adicionado com sucesso.')

    return locals()


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def adicionar_vacina(request, prontuario_id):
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)

    title = f'Adicionar Vacina - {prontuario.vinculo}'

    form = AdicionarVacinaForm(request.POST or None, prontuario=prontuario)
    if form.is_valid():
        if form.cleaned_data['vacina']:
            vacina = get_object_or_404(Vacina, pk=form.cleaned_data['vacina'].id)

            if vacina not in prontuario.vacinas.all():
                cartaovacinal = CartaoVacinal()
                cartaovacinal.prontuario = prontuario
                cartaovacinal.vacina = vacina
                cartaovacinal.externo = False
                cartaovacinal.numero_dose = 1
                cartaovacinal.save()
            else:
                cartaovacinal = CartaoVacinal()
                cartaovacinal.prontuario = prontuario
                cartaovacinal.vacina = vacina
                cartaovacinal.externo = False
                cartaovacinal.numero_dose = 0  # -1 indica que se trata de um reforço
                cartaovacinal.save()

            return httprr(f'/saude/adicionar_vacina/{prontuario.id}/?tab=aba_cartao_vacinal', 'Vacina adicionada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def atendimento_medico_enfermagem(request, atendimento_id):
    title = 'Atendimento Médico/Enfermagem'
    tem_permissao_acesso_atendimento_medico(request.user)

    # Carrega dados do atendimento, cabecalho e do vinculo do usuario
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.ENFERMAGEM_MEDICO)
    atendimento_aberto = atendimento.is_aberto()
    if atendimento.aluno:
        programas = Participacao.objects.filter(aluno=atendimento.get_vinculo(), data_termino__isnull=True)
    is_coordenador_sistemico = in_group(request.user, 'Coordenador de Saúde Sistêmico')
    especialidade = Especialidades(request.user)
    is_medico = especialidade.is_medico()
    is_enfermagem = especialidade.is_enfermeiro() or especialidade.is_tecnico_enfermagem() or especialidade.is_auxiliar_enfermagem()
    is_fisioterapeuta = especialidade.is_fisioterapeuta()
    # Carrega as fichas do atendimento
    motivo = Motivo.objects.filter(atendimento=atendimento)
    motivo_titulo = motivo.model._meta.verbose_name
    motivo_count = motivo.count()
    motivo_responsavel = None
    if motivo.exists():
        motivo = motivo.latest('id')
        motivo_responsavel = motivo.get_responsavel()

    anamnese = Anamnese.objects.filter(atendimento=atendimento)
    anamnese_titulo = anamnese.model._meta.verbose_name
    anamnese_count = anamnese.count()
    anamnese_responsavel = None
    if anamnese.exists():
        anamnese = anamnese.latest('id')
        anamnese_responsavel = anamnese.get_responsavel()

    cadastrou_antecedentes = False
    cadastrou_processosaudedoenca = False

    antecedentesfamiliares = AntecedentesFamiliares.objects.filter(atendimento=atendimento)
    antecedentesfamiliares_titulo = 'Antecedentes'
    antecedentesfamiliares_count = antecedentesfamiliares.count()
    if antecedentesfamiliares.exists():
        cadastrou_antecedentes = True
        antecedentesfamiliares = antecedentesfamiliares.latest('id')
        antecedentesfamiliares_responsavel = antecedentesfamiliares.get_responsavel()

    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento)
    processosaudedoenca_titulo = 'Processo Saúde-Doença'
    processosaudedoenca_count = processosaudedoenca.count()
    if processosaudedoenca.exists():
        cadastrou_processosaudedoenca = True
        processosaudedoenca = processosaudedoenca.latest('id')
        processosaudedoenca_responsavel = processosaudedoenca.get_responsavel()

    aba_antecedentes_preenchida = cadastrou_antecedentes and cadastrou_processosaudedoenca

    hipotesediagnostica = HipoteseDiagnostica.objects.filter(atendimento=atendimento)
    hipotesediagnostica_titulo = 'Hipótese Diagnóstica'
    hipotesediagnostica_count = hipotesediagnostica.count()

    condutamedica = CondutaMedica.objects.filter(atendimento=atendimento)
    condutamedica_titulo = 'Conduta Médica'
    condutamedica_count = condutamedica.count()

    aba_hipotese_preenchida = hipotesediagnostica.exists() and condutamedica.exists()

    encaminhados_odonto = Atendimento.objects.filter(tipo=TipoAtendimento.ODONTOLOGICO, prontuario=atendimento.prontuario, odontograma__encaminhado_enfermagem=True)

    intervencaoenfermagem = IntervencaoEnfermagem.objects.filter(atendimento=atendimento).order_by('-id')
    intervencaoenfermagem_titulo = 'Intervenção de Enfermagem'
    intervencaoenfermagem_count = intervencaoenfermagem.count()

    intervencaofisioterapia = IntervencaoFisioterapia.objects.filter(atendimento=atendimento).order_by('-id')
    intervencaofisioterapia_count = intervencaofisioterapia.count()

    tem_registro_intervencao = encaminhados_odonto.exists() or intervencaoenfermagem.exists()

    exclude_fields = ('id', 'data_cadastro', 'atendimento', 'profissional')
    custom_fields = dict(get_cadastro_display=Column('Cadastrado por', accessor="get_cadastro_display"))
    campos = ('procedimento_enfermagem', 'descricao')
    sequence = ['procedimento_enfermagem', 'descricao', 'get_cadastro_display']
    table_intervencaoenfermagem = get_table(queryset=intervencaoenfermagem, sequence=sequence, custom_fields=custom_fields, fields=campos, exclude_fields=exclude_fields)

    return locals()


@rtr()
@group_required(Especialidades.ENFERMAGEM)
def adicionar_motivo_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Motivo do Atendimento - {atendimento.get_vinculo()}'
    obj = Motivo.objects.filter(atendimento=atendimento.pk)

    if obj.exists():
        obj = obj.latest('id')
        obj.id = None
    else:
        obj = Motivo()

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    obj.escala_dor = obj.escala_dor or 0

    form = MotivoForm(request.POST or None, instance=obj, request=request, initial={'escala_dor': '0', 'temperatura_categoria': '2'})

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_motivo', 'Motivo do Atendimento registrado com sucesso.')

    return locals()


@rtr()
@group_required(['Médico'])
def adicionar_anamnese(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Anamnese - {atendimento.get_vinculo()}'
    obj = Anamnese.objects.filter(atendimento=atendimento.pk)

    if obj.exists():
        obj = obj.latest('id')
        obj.id = None
    else:
        obj = Anamnese()

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = AnamneseForm(request.POST or None, instance=obj, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_anamnese', 'Anamnese registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Médico'])
def adicionar_hipotese_diagnostica(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Hipótese Diagnóstica - {atendimento.get_vinculo()}'

    form = HipoteseDiagnosticaForm(request.POST or None)

    if form.is_valid():
        cids = form.cleaned_data['cids']
        for cid in cids:
            novo_cid = HipoteseDiagnostica()
            novo_cid.cid = cid
            novo_cid.sigilo = form.cleaned_data.get('sigilo')
            novo_cid.atendimento = atendimento
            novo_cid.profissional = request.user
            novo_cid.data_cadastro = datetime.datetime.now()
            novo_cid.save()

        AtendimentoEspecialidade.cadastrar(atendimento, request)
        return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_hipotesediagnostica', 'Hipótese Diagnóstica registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Médico'])
def adicionar_conduta_medica(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Conduta Médica - {atendimento.get_vinculo()}'
    obj = CondutaMedica.objects.filter(atendimento=atendimento.pk)

    if obj.exists():
        obj = obj.latest('id')
        obj.id = None
        obj.atendido = False
    else:
        obj = CondutaMedica()

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = CondutaMedicaForm(request.POST or None, instance=obj, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_hipotesediagnostica', 'Conduta Médica registrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.ENFERMAGEM)
def adicionar_intervencao_enfermagem(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Intervenção de Enfermagem - {atendimento.get_vinculo()}'

    condutas_medicas = CondutaMedica.objects.filter(atendimento=atendimento, encaminhado_enfermagem=True, atendido=False)

    form = IntervencaoEnfermagemForm(request.POST or None, request=request, atendimento=atendimento)

    if form.is_valid():
        for item in form.cleaned_data.get('procedimento_enfermagem'):
            obj = IntervencaoEnfermagem()
            obj.profissional = request.user
            obj.data_cadastro = datetime.datetime.now()
            obj.atendimento = atendimento
            obj.procedimento_enfermagem = item
            obj.conduta_medica = form.cleaned_data.get('conduta_medica')
            obj.descricao = form.cleaned_data.get('descricao')
            obj.save()

        if form.cleaned_data.get('conduta_medica'):
            CondutaMedica.objects.filter(id=form.cleaned_data.get('conduta_medica').id).update(atendido=True)

        AtendimentoEspecialidade.cadastrar(atendimento, request)
        return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_intervencaoenfermagem', 'Intervenção de enfermagem registrada com sucesso.')

    return locals()


@rtr()
@group_required(
    [
        'Coordenador de Saúde Sistêmico',
        Especialidades.MEDICO,
        Especialidades.ODONTOLOGO,
        Especialidades.ENFERMEIRO,
        Especialidades.TECNICO_ENFERMAGEM,
        Especialidades.FISIOTERAPEUTA,
        Especialidades.PSICOLOGO,
        Especialidades.NUTRICIONISTA,
        Especialidades.AUXILIAR_DE_ENFERMAGEM,
        'Auditor',
        'Coordenador de Atividades Estudantis Sistêmico',
    ]
)
def estatisticas_atendimentos(request):
    title = 'Estatísticas de Atendimentos'

    atendimentos = Atendimento.objects.all()
    if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
        atendimento = atendimentos.filter(usuario_aberto__vinculo__setor__uo=get_uo(request.user))

    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        atendimentos = atendimentos.filter(data_aberto__gte=form.cleaned_data['data_inicio'], data_aberto__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            atendimento = atendimentos.filter(usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))
    dados = list()

    tipo = atendimentos.values('tipo').annotate(qtd=Count('tipo')).order_by('tipo')
    total = 0
    for registro in tipo:
        if registro['tipo'] == TipoAtendimento.AVALIACAO_BIOMEDICA:
            tipo = 'Avaliação Biomédica'
        elif registro['tipo'] == TipoAtendimento.ENFERMAGEM_MEDICO:
            tipo = 'Atendimento Médico/Enfermagem'
        else:
            tipo = 'Outros'
        dados.append([tipo, registro['qtd']])
        total = total + registro['qtd']

    grafico1 = PieChart('grafico1', title='Atendimentos por Tipo', subtitle='Atendimentos contabilizados pelo tipo do atendimento', minPointLength=0, data=dados)
    setattr(grafico1, 'id', 'grafico1')

    dados2 = list()
    alunos = atendimentos.filter(aluno__isnull=False).count()
    servidor = atendimentos.filter(servidor__isnull=False).count()
    prestador_servico = atendimentos.filter(prestador_servico__isnull=False).count()
    comunidade_externa = atendimentos.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    if alunos > 0:
        dados2.append(['Alunos', alunos])
    if servidor > 0:
        dados2.append(['Servidores', servidor])
    if prestador_servico > 0:
        dados2.append(['Prestadores de Serviço', prestador_servico])
    if comunidade_externa > 0:
        dados2.append(['Comunidade Externa', comunidade_externa])

    grafico2 = PieChart('grafico2', title='Atendimentos por Categoria', subtitle='Atendimentos contabilizados pela categoria do paciente', minPointLength=0, data=dados2)
    setattr(grafico2, 'id', 'grafico2')

    dados3 = list()
    alunos_atendidos = atendimentos.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_atendidos = atendimentos.filter(servidor__isnull=False).distinct('servidor').count()
    prestador_servico_atendidos = atendimentos.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comunidade_externa_atendidos = (
        atendimentos.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).distinct('prontuario__vinculo__pessoa__nome').count()
    )

    if alunos_atendidos > 0:
        dados3.append(['Alunos', alunos_atendidos])
    if servidor_atendidos > 0:
        dados3.append(['Servidores', servidor_atendidos])
    if prestador_servico_atendidos > 0:
        dados3.append(['Prestadores de Serviço', prestador_servico_atendidos])
    if comunidade_externa_atendidos > 0:
        dados3.append(['Comunidade Externa', comunidade_externa_atendidos])

    grafico3 = PieChart('grafico3', title='Atendidos por Categoria', subtitle='Pacientes únicos atendidos', minPointLength=0, data=dados3)
    setattr(grafico3, 'id', 'grafico3')

    pie_chart_lists = [grafico2, grafico3, grafico1]

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def atendimento_odontologico(request, atendimento_id):
    title = 'Atendimento'

    # Carrega dados do atendimento, cabecalho e do vinculo do usuario
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.ODONTOLOGICO)

    eh_externo = False
    if atendimento.aluno:
        programas = Participacao.objects.filter(aluno=atendimento.get_vinculo(), data_termino__isnull=True)

    elif not atendimento.servidor and not atendimento.prestador_servico:
        eh_externo = True
    is_coordenador_sistemico = in_group(request.user, 'Coordenador de Saúde Sistêmico')

    especialidade = Especialidades(request.user)
    is_odontologo = especialidade.is_odontologo()
    eh_responsavel = atendimento.usuario_aberto == request.user
    pode_salvar_odontograma = atendimento.is_aberto() and eh_responsavel and is_odontologo
    pode_adicionar_procedimento = is_odontologo or especialidade.is_tecnico_saude_bucal()
    aba_antecedentes_preenchida = False
    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento)
    processosaudedoenca_titulo = 'Processo Saúde-Doença'
    processosaudedoenca_count = processosaudedoenca.count()
    if processosaudedoenca.exists():
        aba_antecedentes_preenchida = True
        processosaudedoenca = processosaudedoenca.latest('id')
        processosaudedoenca_responsavel = processosaudedoenca.get_responsavel()

    # Carrega as fichas do atendimento
    procedimentos = ProcedimentoOdontologico.objects.filter(atendimento=atendimento).order_by('procedimento')
    if procedimentos.exists():
        tipo_consulta = procedimentos.latest('id')
    procedimento_titulo = procedimentos.model._meta.verbose_name_plural
    procedimento_count = procedimentos.count()

    if Odontograma.objects.filter(atendimento=atendimento).exists():
        odontograma = Odontograma.objects.filter(atendimento=atendimento).latest('id')
        odontograma_responsavel = odontograma.get_responsavel()
    else:
        odontograma = Odontograma()

    indice_cpod, indice_c, indice_p, indice_o = odontograma.get_indice_cpod()

    situacoes = SituacaoClinica.objects.exclude(id__in=[SituacaoClinica.CALCULO, SituacaoClinica.SANGRAMENTO])

    exames_periodontais = ExamePeriodontal.objects.filter(atendimento=atendimento).order_by('sextante')
    if exames_periodontais.exists():
        exames_periodontais_responsavel = exames_periodontais.latest('id').get_responsavel()
    avaliacoes_tecidos = ExameEstomatologico.objects.filter(atendimento=atendimento)
    if avaliacoes_tecidos.exists():
        avaliacoes_tecidos = avaliacoes_tecidos.latest('id')
        avaliacoes_tecidos_responsavel = avaliacoes_tecidos.get_responsavel()

    tem_plano_tratamento = False
    plano_tratamento = PlanoTratamento.objects.filter(atendimento=atendimento).order_by('ordem')
    if plano_tratamento.exists():
        tem_plano_tratamento = True
    form = OdontogramaForm(mostra_queixa=True, queixa_principal=odontograma.queixa_principal)
    if request.POST:
        form = OdontogramaForm(request.POST, mostra_queixa=True)
        if form.is_valid():
            if form.cleaned_data['faces']:
                odontograma.dentes_alterados = form.cleaned_data['faces']
                odontograma.atendimento = atendimento
                odontograma.profissional = request.user
                odontograma.data_cadastro = datetime.datetime.now()
            odontograma.queixa_principal = form.cleaned_data.get('queixa_principal')
            odontograma.salvo = True
            odontograma.save()

            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/', 'Odontograma atualizado com sucesso.')

    return locals()


@rtr()
@group_required(['Odontólogo', 'Técnico em Saúde Bucal'])
def adicionar_procedimento_odontologico(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    title = f'Adicionar Procedimento Odontológico - {atendimento.get_vinculo()}'
    procedimentos = ProcedimentoOdontologico.objects.filter(atendimento=atendimento).order_by('procedimento')
    id_situacao_clinica = None
    odontograma = Odontograma.objects.filter(atendimento=atendimento)
    if odontograma:
        odontograma = odontograma.latest('id')
    else:
        return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_procedimento', 'Este paciente não possui um odontograma cadastrado.', tag='error')

    especialidade = Especialidades(request.user)

    form = ProcedimentoOdontologicoForm(request.POST or None, eh_dentista=especialidade.is_odontologo())
    if form.is_valid():
        string_alteracoes = form.cleaned_data['faces_marcadas']
        lista_alteracoes = string_alteracoes.split('-')
        lista_alteracoes.remove('')
        for procedimento_escolhido in form.cleaned_data['procedimento']:
            registro_procedimento = ProcedimentoOdontologico()
            registro_procedimento.profissional = request.user
            registro_procedimento.data_cadastro = datetime.datetime.now()
            registro_procedimento.atendimento = atendimento
            registro_procedimento.faces_marcadas = string_alteracoes
            registro_procedimento.regiao_bucal = form.cleaned_data['regiao_bucal']
            registro_procedimento.observacao = form.cleaned_data['observacao']
            registro_procedimento.procedimento = procedimento_escolhido
            registro_procedimento.save()
            if ResultadoProcedimento.objects.filter(procedimento=procedimento_escolhido).exists():
                id_situacao_clinica = f'{ResultadoProcedimento.objects.filter(procedimento=procedimento_escolhido)[0].situacao_clinica_id}'

            for item in lista_alteracoes:
                dente = item[4:6]
                todas_as_faces = False
                if (
                    '_V_' + dente in string_alteracoes
                    and '_P_' + dente in string_alteracoes
                    and '_M_' + dente in string_alteracoes
                    and '_D_' + dente in string_alteracoes
                    and '_O_' + dente in string_alteracoes
                ):
                    todas_as_faces = True
                    if PlanoTratamento.objects.filter(dente=dente, face__icontains='_T_', procedimento=procedimento_escolhido, atendimento=atendimento).exists():
                        plano_realizado = PlanoTratamento.objects.filter(dente=dente, face__icontains='_T_', procedimento=procedimento_escolhido, atendimento=atendimento)[0]
                        plano_realizado.realizado = True
                        plano_realizado.save()
                if PlanoTratamento.objects.filter(face=item, procedimento=procedimento_escolhido, atendimento=atendimento).exists():
                    plano_realizado = PlanoTratamento.objects.filter(face=item, procedimento=procedimento_escolhido, atendimento=atendimento)[0]
                    plano_realizado.realizado = True
                    plano_realizado.save()

                elif PlanoTratamento.objects.filter(dente=dente, procedimento=procedimento_escolhido, atendimento=atendimento).exists():
                    plano_realizado = PlanoTratamento.objects.filter(dente=dente, procedimento=procedimento_escolhido, atendimento=atendimento)[0]
                    plano_realizado.realizado = True
                    plano_realizado.save()

                if id_situacao_clinica:
                    novo_odontograma = odontograma.dentes_alterados
                    indice = novo_odontograma.find(item)
                    if indice != -1:
                        novo_odontograma = novo_odontograma[: indice + 7] + id_situacao_clinica + novo_odontograma[indice + 9:]
                    else:
                        modificacao_odontograma = item + f'_{id_situacao_clinica}-'
                        novo_odontograma = novo_odontograma + modificacao_odontograma

                    odontograma.dentes_alterados = novo_odontograma
                    odontograma.save()

        return httprr(f'/saude/adicionar_procedimento_odontologico/{atendimento.id}/', 'Procedimento registrado com sucesso.')

    return locals()


@rtr()
@group_required(['Odontólogo'])
def adicionar_odontograma(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    title = f'Adicionar Odontograma - {atendimento.get_vinculo()}'
    situacoes = SituacaoClinica.objects.all()
    odontograma = Odontograma.objects.filter(atendimento=atendimento.pk)
    if odontograma.exists():
        odontograma = odontograma.latest('id')
    else:
        odontograma = Odontograma()
    odontograma.profissional = request.user
    odontograma.data_cadastro = datetime.datetime.now()
    odontograma.atendimento = atendimento

    form = OdontogramaForm(request.POST or None, mostra_queixa=False)

    if form.is_valid():
        if form.cleaned_data['faces']:
            odontograma.dentes_alterados = form.cleaned_data['faces']
        odontograma.salvo = True
        odontograma.save()
        AtendimentoEspecialidade.cadastrar(atendimento, request)
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_odontograma', 'Odontograma registrado com sucesso.')

    return locals()


@rtr()
@group_required(['Odontólogo'])
def adicionar_exame_periodontal(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    if atendimento.tipo == TipoAtendimento.ODONTOLOGICO:
        tem_permissao(atendimento, request)
    else:
        especialidade = Especialidades(request.user)
        if not especialidade.is_odontologo():
            raise PermissionDenied()

    title = f'Adicionar Ocorrência - {atendimento.get_vinculo()}'
    eh_avaliacao_biomedica = request.GET.get('origem')
    exame = ExamePeriodontal()
    exame.profissional = request.user
    exame.data_cadastro = datetime.datetime.now()
    exame.atendimento = atendimento
    exames_cadastrados = ExamePeriodontal.objects.filter(atendimento=atendimento)

    form = ExamePeriodontalForm(request.POST or None, instance=exame, atendimento=atendimento)

    if form.is_valid():
        o = form.save(False)
        texto = ''
        for item in form.cleaned_data.get('sextante'):
            texto = texto + item + '; '
        o.sextante = texto[:-2]
        o.save()
        if eh_avaliacao_biomedica:
            return httprr(f'/saude/adicionar_exame_periodontal/{atendimento.id}/?origem=1', 'Exame periodontal registrado com sucesso.')
        else:
            return httprr(f'/saude/adicionar_exame_periodontal/{atendimento.id}/', 'Exame periodontal registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def deletar_vacina(request, prontuario_id, vacina_id):
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)
    vacina = get_object_or_404(Vacina, pk=vacina_id)
    vacinas = CartaoVacinal.objects.filter(vacina=vacina, prontuario=prontuario)
    vacinas.delete()
    return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_cartao_vacinal', 'Vacina removida com sucesso.')


@rtr()
@group_required(['Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def adicionar_dose(request, prontuario_id, vacina_id):
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)
    vacina = get_object_or_404(Vacina, pk=vacina_id)
    nova_dose = CartaoVacinal()
    nova_dose.vacina = vacina
    nova_dose.prontuario = prontuario
    nova_dose.externo = False
    ultima_dose = CartaoVacinal.objects.filter(vacina=vacina, prontuario=prontuario).order_by('-numero_dose')
    if ultima_dose.exists():
        nova_dose.numero_dose = ultima_dose[0].numero_dose + 1
    else:
        nova_dose.numero_dose = 1
    nova_dose.save()

    return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_cartao_vacinal', 'Dose de Vacina adicionada com sucesso.')


@rtr()
@group_required(Especialidades.GRUPOS)
def adicionar_informacao_adicional(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Informação Adicional - {atendimento.get_vinculo()}'

    obj = InformacaoAdicional()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = InformacaoAdicionalForm(request.POST or None, request=request, instance=obj)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/avaliacao_biomedica/{atendimento.id}/?tab=aba_informacaoadicional', 'Informação adicional registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Odontólogo'])
def adicionar_exame_estomatologico(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    if atendimento.tipo == TipoAtendimento.ODONTOLOGICO:
        tem_permissao(atendimento, request)
    else:
        especialidade = Especialidades(request.user)
        if not especialidade.is_odontologo():
            raise PermissionDenied()
    title = f'Adicionar Exame Estomatológico - {atendimento.get_vinculo()}'
    avaliacao = ExameEstomatologico.objects.filter(atendimento=atendimento.pk)
    if avaliacao.exists():
        avaliacao = avaliacao.latest('id')
        nova_avaliacao = avaliacao
        nova_avaliacao.pk = None
    else:
        nova_avaliacao = ExameEstomatologico()
    nova_avaliacao.profissional = request.user
    nova_avaliacao.data_cadastro = datetime.datetime.now()
    nova_avaliacao.atendimento = atendimento

    form = ExameEstomatologicoForm(request.POST or None, instance=nova_avaliacao)
    if form.is_valid():
        form.save()
        return httprr('..', 'Exame Estomatológico registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Odontólogo'])
def indicar_procedimento(request, plano_tratamento_id):
    plano = get_object_or_404(PlanoTratamento, pk=plano_tratamento_id)
    atendimento = plano.atendimento
    tem_permissao(atendimento, request)
    title = 'Indicar Procedimento'
    form = IndicarProcedimentoForm(request.POST or None, instance=plano, situacao_clinica=plano.situacao_clinica, edicao=True)
    if form.is_valid():
        form.save()
        return httprr('..', 'Procedimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def remover_dose(request, registro_id):
    dose = get_object_or_404(CartaoVacinal, pk=registro_id)
    id_retorno = dose.prontuario.vinculo_id
    if dose.pode_remover_dose(request.user):
        dose.delete()
        return httprr(f'/saude/prontuario/{id_retorno}/?tab=aba_cartao_vacinal', 'Dose de Vacina adicionada com sucesso.')
    else:
        return httprr(f'/saude/prontuario/{id_retorno}/?tab=aba_cartao_vacinal', 'Esta dose não pode ser excluída.', tag='error')


@rtr()
@permission_required('saude.view_atividadegrupo')
def estatistica_geral_atendimento(request):
    title = 'Estatísticas de Atendimentos por Curso'

    form = FiltroEstatisticaGeralForm(request.GET or None, request=request)

    titulo_qtd_aluno = 'Total de Alunos Ativos'

    if form.is_valid():
        lista = []
        cursos = CursoCampus.objects.filter(ativo=True, diretoria__setor__uo__sigla=form.cleaned_data['campus']).order_by('diretoria__setor__uo__sigla', 'descricao')

        totais = dict(
            total_alunos_ativos=0,
            total_atendimentos_abertos=0,
            total_atendimentos_fechados=0,
            total_atendimentos_cancelados=0,
            total_avaliacao_biomedica_em_aberto=0,
            total_avaliacao_biomedica_fechado=0,
            total_avaliacao_biomedica_cancelado=0,
            total_medico_enfermagem_em_aberto=0,
            total_medico_enfermagem_fechado=0,
            total_medico_enfermagem_cancelado=0,
            total_odonto_em_aberto=0,
            total_odonto_fechado=0,
            total_odonto_cancelado=0,
            total_psicologia_em_aberto=0,
            total_psicologia_fechado=0,
            total_psicologia_cancelado=0,
            total_nutricao_em_aberto=0,
            total_nutricao_fechado=0,
            total_nutricao_cancelado=0,
            total_fisio_em_aberto=0,
            total_fisio_fechado=0,
            total_fisio_cancelado=0,
            total_multi_em_aberto=0,
            total_multi_fechado=0,
            total_multi_cancelado=0,
        )

        titulo_qtd_aluno = 'Total de Alunos Ingressantes' if form.cleaned_data['ano_ingresso'] and int(form.cleaned_data['periodo_ingresso']) > 0 else 'Total de Alunos Ativos'
        if form.cleaned_data.get('modalidade'):
            cursos = cursos.filter(modalidade=form.cleaned_data.get('modalidade'))

        aluno = Aluno.ativos.filter(curso_campus__in=cursos)

        if form.cleaned_data['ano_ingresso'] and int(form.cleaned_data['periodo_ingresso']) > 0:
            aluno = aluno.filter(ano_letivo=form.cleaned_data['ano_ingresso'], periodo_letivo=form.cleaned_data['periodo_ingresso'])
        if form.cleaned_data.get('modalidade'):
            aluno = aluno.filter(curso_campus__modalidade=form.cleaned_data.get('modalidade'))

        if aluno.exists():
            for curso in cursos:
                alunos_ativos_curso = aluno.filter(curso_campus=curso)

                atendimentos = Atendimento.objects.filter(aluno__in=alunos_ativos_curso)
                atendimentos_avaliacao_biomedica = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.AVALIACAO_BIOMEDICA)
                atendimentos_medico_enfermagem = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.ENFERMAGEM_MEDICO)
                atendimentos_odonto = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.ODONTOLOGICO)
                atendimentos_psicologia = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.PSICOLOGICO)
                atendimentos_nutricao = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.NUTRICIONAL)
                atendimentos_fisio = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.FISIOTERAPIA)
                atendimentos_multi = Atendimento.objects.filter(aluno__in=alunos_ativos_curso, tipo=TipoAtendimento.MULTIDISCIPLINAR)

                linha = dict()
                linha['curso'] = curso
                linha['qtd_alunos_ativos'] = alunos_ativos_curso.count()
                linha['qtd_atendimentos_abertos'] = atendimentos.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['qtd_atendimentos_fechados'] = atendimentos.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['qtd_atendimentos_cancelados'] = atendimentos.filter(situacao=SituacaoAtendimento.CANCELADO).count()
                linha['avaliacao_biomedica_em_aberto'] = atendimentos_avaliacao_biomedica.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['avaliacao_biomedica_fechado'] = atendimentos_avaliacao_biomedica.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['avaliacao_biomedica_cancelado'] = atendimentos_avaliacao_biomedica.filter(situacao=SituacaoAtendimento.CANCELADO).count()
                linha['medico_enfermagem_em_aberto'] = atendimentos_medico_enfermagem.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['medico_enfermagem_fechado'] = atendimentos_medico_enfermagem.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['medico_enfermagem_cancelado'] = atendimentos_medico_enfermagem.filter(situacao=SituacaoAtendimento.CANCELADO).count()
                linha['odonto_em_aberto'] = atendimentos_odonto.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['odonto_fechado'] = atendimentos_odonto.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['odonto_cancelado'] = atendimentos_odonto.filter(situacao=SituacaoAtendimento.CANCELADO).count()
                linha['psicologia_em_aberto'] = atendimentos_psicologia.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['psicologia_fechado'] = atendimentos_psicologia.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['psicologia_cancelado'] = atendimentos_psicologia.filter(situacao=SituacaoAtendimento.CANCELADO).count()
                linha['nutricao_em_aberto'] = atendimentos_nutricao.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['nutricao_fechado'] = atendimentos_nutricao.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['nutricao_cancelado'] = atendimentos_nutricao.filter(situacao=SituacaoAtendimento.CANCELADO).count()

                linha['fisio_em_aberto'] = atendimentos_fisio.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['fisio_fechado'] = atendimentos_fisio.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['fisio_cancelado'] = atendimentos_fisio.filter(situacao=SituacaoAtendimento.CANCELADO).count()

                linha['multi_em_aberto'] = atendimentos_multi.filter(situacao=SituacaoAtendimento.ABERTO).count()
                linha['multi_fechado'] = atendimentos_multi.filter(situacao=SituacaoAtendimento.FECHADO).count()
                linha['multi_cancelado'] = atendimentos_multi.filter(situacao=SituacaoAtendimento.CANCELADO).count()

                totais['total_alunos_ativos'] += linha.get('qtd_alunos_ativos')
                totais['total_atendimentos_abertos'] += linha.get('qtd_atendimentos_abertos')
                totais['total_atendimentos_fechados'] += linha.get('qtd_atendimentos_fechados')
                totais['total_atendimentos_cancelados'] += linha.get('qtd_atendimentos_cancelados')
                totais['total_avaliacao_biomedica_em_aberto'] += linha.get('avaliacao_biomedica_em_aberto')
                totais['total_avaliacao_biomedica_fechado'] += linha.get('avaliacao_biomedica_fechado')
                totais['total_avaliacao_biomedica_cancelado'] += linha.get('avaliacao_biomedica_cancelado')
                totais['total_medico_enfermagem_em_aberto'] += linha.get('medico_enfermagem_em_aberto')
                totais['total_medico_enfermagem_fechado'] += linha.get('medico_enfermagem_fechado')
                totais['total_medico_enfermagem_cancelado'] += linha.get('medico_enfermagem_cancelado')
                totais['total_odonto_em_aberto'] += linha.get('odonto_em_aberto')
                totais['total_odonto_fechado'] += linha.get('odonto_fechado')
                totais['total_odonto_cancelado'] += linha.get('odonto_cancelado')
                totais['total_psicologia_em_aberto'] += linha.get('psicologia_em_aberto')
                totais['total_psicologia_fechado'] += linha.get('psicologia_fechado')
                totais['total_psicologia_cancelado'] += linha.get('psicologia_cancelado')
                totais['total_nutricao_em_aberto'] += linha.get('nutricao_em_aberto')
                totais['total_nutricao_fechado'] += linha.get('nutricao_fechado')
                totais['total_nutricao_cancelado'] += linha.get('nutricao_cancelado')
                totais['total_fisio_em_aberto'] += linha.get('fisio_em_aberto')
                totais['total_fisio_fechado'] += linha.get('fisio_fechado')
                totais['total_fisio_cancelado'] += linha.get('fisio_cancelado')
                totais['total_multi_em_aberto'] += linha.get('multi_em_aberto')
                totais['total_multi_fechado'] += linha.get('multi_fechado')
                totais['total_multi_cancelado'] += linha.get('multi_cancelado')

                lista.append(linha)

    return locals()


@rtr()
@group_required(['Odontólogo'])
def registrar_execucao_plano(request, plano_tratamento_id):
    plano = get_object_or_404(PlanoTratamento, pk=plano_tratamento_id)
    atendimento = plano.atendimento
    tem_permissao(atendimento, request)
    plano.realizado = True
    plano.save()

    face = plano.face
    procedimento = ProcedimentoOdontologico()
    procedimento.profissional = request.user
    procedimento.data_cadastro = datetime.datetime.now()
    procedimento.atendimento = atendimento
    procedimento.procedimento = plano.procedimento
    if request.GET.get('obs'):
        procedimento.observacao = request.GET.get('obs')

    if plano.dente:
        if face:
            if '_T_' in face:
                texto_face = f'{face[0]}_V_{plano.dente}-'
                texto_face = texto_face + f'{face[0]}_P_{plano.dente}-'
                texto_face = texto_face + f'{face[0]}_M_{plano.dente}-'
                texto_face = texto_face + f'{face[0]}_D_{plano.dente}-'
                texto_face = texto_face + f'{face[0]}_O_{plano.dente}-'
                procedimento.faces_marcadas = texto_face
            else:
                procedimento.faces_marcadas = face + '-'
    else:
        procedimento.regiao_bucal = plano.sextante
    procedimento.save()
    odontograma = Odontograma.objects.filter(atendimento=atendimento)
    if odontograma:
        odontograma = odontograma.latest('id')

        if ResultadoProcedimento.objects.filter(procedimento=plano.procedimento).exists():
            id_situacao_clinica = f'{ResultadoProcedimento.objects.filter(procedimento=plano.procedimento)[0].situacao_clinica_id}'

            if id_situacao_clinica and face:
                novo_odontograma = odontograma.dentes_alterados

                string_alteracoes = procedimento.faces_marcadas
                lista_alteracoes = string_alteracoes.split('-')

                for item in lista_alteracoes:
                    if item != '':
                        indice = novo_odontograma.find(item)
                        if indice != -1:
                            novo_odontograma = novo_odontograma[: indice + 7] + id_situacao_clinica + novo_odontograma[indice + 9:]
                        else:
                            modificacao_odontograma = item + f'_{id_situacao_clinica}-'
                            novo_odontograma = novo_odontograma + modificacao_odontograma

                        odontograma.dentes_alterados = novo_odontograma
                        odontograma.save()

    return httprr(f'/saude/atendimento_odontologico/{plano.atendimento_id}/?tab=aba_plano_tratamento', 'Execução registrada com sucesso.')


@rtr()
@group_required(['Odontólogo'])
def excluir_intervencao(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    tem_permissao(atendimento, request)

    if request.POST.getlist('action')[0] == 'Remover':
        deletar = request.POST.getlist('registros')
        if deletar:
            for item in deletar:
                plano = get_object_or_404(PlanoTratamento, pk=int(item))
                plano.delete()
            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_plano_tratamento', 'Intervenção excluída com sucesso.')
        else:
            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_plano_tratamento', 'Nenhuma intervenção selecionada.', tag='error')

    elif request.POST.getlist('action')[0] == 'Ordenar':
        ordenar = request.POST.getlist('ordens')
        if ordenar:
            lista = list()
            for item in PlanoTratamento.objects.filter(atendimento=atendimento).order_by('ordem').values_list('id', flat=True):
                lista.append(item)
            for idx, item in enumerate(ordenar, 0):
                if item:
                    plano = PlanoTratamento.objects.get(id=lista[idx])
                    plano.ordem = int(item)
                    plano.save()
            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_plano_tratamento', 'Ordenação alterada com sucesso.')

    elif request.POST.getlist('action')[0] == 'Agregar':
        registros = request.POST.getlist('registros')
        faces = None
        dente = None
        situacao = False
        procedimento = False
        descricao_sextante = list()

        for registro in registros:
            plano = get_object_or_404(PlanoTratamento, pk=int(registro))
            if not dente:
                if plano.dente:
                    dente = plano.dente
                elif plano.sextante:
                    if (situacao and situacao == plano.situacao_clinica) or (not situacao and not descricao_sextante):
                        descricao_sextante.append(plano.sextante)
                situacao = plano.situacao_clinica
                procedimento = plano.procedimento
            if plano.dente == dente:
                if (situacao and situacao == plano.situacao_clinica) or not situacao:
                    if faces:
                        faces = faces + '-' + plano.face
                    else:
                        faces = plano.face

        if descricao_sextante or dente:
            registro_agregado = PlanoTratamento()
            if descricao_sextante:
                registro_agregado.sextante = ', '.join(descricao_sextante)
            elif dente:
                registro_agregado.dente = dente
            registro_agregado.atendimento = atendimento
            if situacao:
                registro_agregado.situacao_clinica = situacao
            if faces:
                registro_agregado.face = faces
            if procedimento:
                registro_agregado.procedimento = procedimento

            for registro in registros:
                plano = get_object_or_404(PlanoTratamento, pk=int(registro))
                if not descricao_sextante or plano.sextante in descricao_sextante:
                    plano.delete()

            registro_agregado.ordem = registro_agregado.get_ordem()
            registro_agregado.save()

            return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_plano_tratamento', 'Agregação realizada com sucesso.')

        else:
            return httprr(
                f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_plano_tratamento',
                'Não é possível agregar registros de dentes ou sextantes distintos.',
                tag='error',
            )


@rtr()
@group_required(['Odontólogo'])
def adicionar_intervencao(request, atendimento_id):
    title = 'Adicionar Intervenção'
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    tem_permissao(atendimento, request)
    nova_intervencao = PlanoTratamento()
    nova_intervencao.profissional = request.user
    nova_intervencao.data_cadastro = datetime.datetime.now()
    nova_intervencao.atendimento = atendimento
    id_ultimo_procedimento = None
    if PlanoTratamento.objects.filter(atendimento=atendimento, procedimento__isnull=False).exclude(id=nova_intervencao.id).exists():
        id_ultimo_procedimento = (
            PlanoTratamento.objects.filter(atendimento=atendimento, procedimento__isnull=False).exclude(id=nova_intervencao.id).order_by('-id')[0].procedimento.id
        )
    form = IndicarProcedimentoForm(request.POST or None, instance=nova_intervencao, edicao=False, initial={'procedimento': id_ultimo_procedimento})
    if form.is_valid():
        if form.cleaned_data.get('dente') != '0':
            if form.cleaned_data['dente'] in PlanoTratamento.ARCADA_INFANTIL:
                texto_face = 'I_'
            else:
                texto_face = 'A_'

            if form.cleaned_data['face'] != PlanoTratamento.TODAS_FACES:
                if form.cleaned_data['face'] == PlanoTratamento.VESTIBULAR:
                    texto_face = texto_face + 'V_'
                elif form.cleaned_data['face'] == PlanoTratamento.PALATAL:
                    texto_face = texto_face + 'P_'
                elif form.cleaned_data['face'] == PlanoTratamento.MESSIAL:
                    texto_face = texto_face + 'M_'
                elif form.cleaned_data['face'] == PlanoTratamento.DISTAL:
                    texto_face = texto_face + 'D_'
                elif form.cleaned_data['face'] == PlanoTratamento.OCLUSAL:
                    texto_face = texto_face + 'O_'
                elif form.cleaned_data['face'] == PlanoTratamento.CERVICAL:
                    texto_face = texto_face + 'C_'
                elif form.cleaned_data['face'] == PlanoTratamento.RAIZ:
                    texto_face = texto_face + 'R_'

                texto_face = texto_face + '{}'.format(form.cleaned_data['dente'])

                o = form.save(False)
                o.face = texto_face
                o.ordem = o.get_ordem()
                o.sextante = None
                o.save()
            else:
                v = form.save(False)
                v.face = texto_face + 'T_{}'.format(form.cleaned_data['dente'])
                v.id = None
                v.ordem = v.get_ordem()
                v.sextante = None
                v.save()
        else:
            o = form.save(False)
            o.dente = None
            o.ordem = o.get_ordem()
            o.face = None
            o.save()
        return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_plano_tratamento', 'Intervenção cadastrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def cadastrar_pessoa_externa(request):
    title = 'Cadastrar Pessoa Externa'
    form = PessoaExternaForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        return httprr(f'/saude/prontuario/{registro.get_vinculo().id}/')

    return locals()


@rtr()
@group_required(['Odontólogo'])
def gerar_plano_tratamento(request, odontograma_id):
    odontograma = get_object_or_404(Odontograma, pk=odontograma_id)
    atendimento = odontograma.atendimento
    tem_permissao(atendimento, request)
    crior_plano = False
    exame_clinico = get_object_or_404(ProcedimentoOdontologia, pk=ProcedimentoOdontologia.EXAME_CLINICO)
    if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, sextante=ExamePeriodontal.S1_S6, procedimento=exame_clinico).exists():
        novo_plano = PlanoTratamento()
        novo_plano.atendimento = odontograma.atendimento
        novo_plano.profissional = request.user
        novo_plano.data_cadastro = datetime.datetime.now()
        novo_plano.sextante = ExamePeriodontal.S1_S6
        novo_plano.procedimento = exame_clinico
        novo_plano.ordem = novo_plano.get_ordem()
        novo_plano.save()
        crior_plano = True

    orientacao_exame_bucal = get_object_or_404(ProcedimentoOdontologia, pk=ProcedimentoOdontologia.ORIENTACAO_HIGIENE_BUCAL)
    if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, sextante=ExamePeriodontal.S1_S6, procedimento=orientacao_exame_bucal).exists():
        novo_plano = PlanoTratamento()
        novo_plano.atendimento = odontograma.atendimento
        novo_plano.profissional = request.user
        novo_plano.data_cadastro = datetime.datetime.now()
        novo_plano.sextante = ExamePeriodontal.S1_S6
        novo_plano.procedimento = orientacao_exame_bucal
        novo_plano.ordem = novo_plano.get_ordem()
        novo_plano.save()
        crior_plano = True

    for item in odontograma.dentes_alterados_lista():
        dente = item[4:6]
        id_situacao = item[7:]
        situacao = SituacaoClinica.objects.get(id=id_situacao)
        if situacao.id not in [
            SituacaoClinica.DENTE_AUSENTE_EXTRAIDO_OUTRAS_RAZOES,
            SituacaoClinica.DENTE_EXTRAIDO_CARIE,
            SituacaoClinica.RESTAURACAO_COROA_SATISFATORIA,
            SituacaoClinica.TRAT_ENDODONTICO_CONCLUIDO,
        ]:
            if situacao.id in [SituacaoClinica.TRAT_ENDODONTICO_INDICADO, SituacaoClinica.EXODONTIA_POR_CARIE, SituacaoClinica.EXODONTIA_POR_OUTROS_MOTIVOS]:

                face_marcada = item[0:1] + '_T_' + item[4:6]
                if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, dente=dente, face=face_marcada, situacao_clinica=situacao).exists():
                    novo_plano = PlanoTratamento()
                    novo_plano.atendimento = odontograma.atendimento
                    novo_plano.profissional = request.user
                    novo_plano.data_cadastro = datetime.datetime.now()
                    novo_plano.dente = dente
                    novo_plano.face = face_marcada
                    novo_plano.situacao_clinica = situacao
                    novo_plano.ordem = novo_plano.get_ordem()
                    novo_plano.save()
                    crior_plano = True
            else:
                if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, dente=dente, face=item[:-3], situacao_clinica=situacao).exists():
                    novo_plano = PlanoTratamento()
                    novo_plano.atendimento = odontograma.atendimento
                    novo_plano.profissional = request.user
                    novo_plano.data_cadastro = datetime.datetime.now()
                    novo_plano.dente = dente
                    novo_plano.face = item[:-3]
                    novo_plano.situacao_clinica = situacao
                    novo_plano.ordem = novo_plano.get_ordem()
                    novo_plano.save()
                    crior_plano = True

    for item in ExamePeriodontal.objects.filter(atendimento=odontograma.atendimento, resolvido=False):
        if item.ocorrencia == ExamePeriodontal.CALCULO:
            sextantes = item.sextante.split(';')
            for sextante in sextantes:
                situacao = get_object_or_404(SituacaoClinica, pk=SituacaoClinica.CALCULO)
                if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, sextante=sextante, situacao_clinica=situacao).exists():
                    novo_plano = PlanoTratamento()
                    novo_plano.atendimento = odontograma.atendimento
                    novo_plano.profissional = request.user
                    novo_plano.data_cadastro = datetime.datetime.now()
                    novo_plano.sextante = f'{sextante}'
                    novo_plano.situacao_clinica = situacao
                    novo_plano.ordem = novo_plano.get_ordem()
                    novo_plano.save()
                    crior_plano = True
        elif item.ocorrencia == ExamePeriodontal.SANGRAMENTO:
            sextantes = item.sextante.split(';')
            for sextante in sextantes:
                situacao = get_object_or_404(SituacaoClinica, pk=SituacaoClinica.SANGRAMENTO)
                if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, sextante=sextante, situacao_clinica=situacao).exists():
                    novo_plano = PlanoTratamento()
                    novo_plano.atendimento = odontograma.atendimento
                    novo_plano.profissional = request.user
                    novo_plano.data_cadastro = datetime.datetime.now()
                    novo_plano.sextante = f'{sextante}'
                    novo_plano.situacao_clinica = situacao
                    novo_plano.ordem = novo_plano.get_ordem()
                    novo_plano.save()
                    crior_plano = True

    aplicacao_topica_fluor = get_object_or_404(ProcedimentoOdontologia, pk=ProcedimentoOdontologia.APLICACAO_TOPICA_FLUOR)
    if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, sextante=ExamePeriodontal.S1_S6, procedimento=aplicacao_topica_fluor).exists():
        novo_plano = PlanoTratamento()
        novo_plano.atendimento = odontograma.atendimento
        novo_plano.profissional = request.user
        novo_plano.data_cadastro = datetime.datetime.now()
        novo_plano.sextante = ExamePeriodontal.S1_S6
        novo_plano.procedimento = aplicacao_topica_fluor
        novo_plano.ordem = novo_plano.get_ordem()
        novo_plano.save()
        crior_plano = True

    profilaxia = get_object_or_404(ProcedimentoOdontologia, pk=ProcedimentoOdontologia.PROFILAXIA)
    if not PlanoTratamento.objects.filter(atendimento=odontograma.atendimento, sextante=ExamePeriodontal.S1_S6, procedimento=profilaxia).exists():
        novo_plano = PlanoTratamento()
        novo_plano.atendimento = odontograma.atendimento
        novo_plano.profissional = request.user
        novo_plano.data_cadastro = datetime.datetime.now()
        novo_plano.sextante = ExamePeriodontal.S1_S6
        novo_plano.procedimento = profilaxia
        novo_plano.ordem = novo_plano.get_ordem()
        novo_plano.save()
        crior_plano = True

    if crior_plano:
        return httprr(f'/saude/atendimento_odontologico/{odontograma.atendimento_id}/?tab=aba_plano_tratamento', 'Plano de Tratamento criado com sucesso.')
    else:
        return httprr(
            f'/saude/atendimento_odontologico/{odontograma.atendimento_id}/?tab=aba_plano_tratamento',
            'Não há nenhuma alteração no odontograma para gerar um plano de tratamento.',
            tag='error',
        )


@rtr()
@permission_required('saude.view_prontuario')
def indicadores(request):
    title = 'Indicadores'

    atendimentos = Atendimento.objects.all()

    if not request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
        atendimentos = atendimentos.filter(usuario_aberto__vinculo__setor__uo=get_uo(request.user))

    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            atendimentos = atendimentos.filter(data_aberto__gte=form.cleaned_data['data_inicio'], data_aberto__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            atendimentos = atendimentos.filter(usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))

    avaliacao_biomedica = atendimentos.filter(tipo=TipoAtendimento.AVALIACAO_BIOMEDICA)
    atendimentos_medicos = atendimentos.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO, condutamedica__isnull=False).distinct()
    atendimentos_enfermagem = atendimentos.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO, intervencaoenfermagem__isnull=False).distinct()
    atendimentos_odontologico = atendimentos.filter(tipo=TipoAtendimento.ODONTOLOGICO).distinct()
    atendimentos_psicologico = atendimentos.filter(tipo=TipoAtendimento.PSICOLOGICO).distinct()
    atendimentos_nutricional = atendimentos.filter(tipo=TipoAtendimento.NUTRICIONAL).distinct()
    atendimentos_fisioterapia = atendimentos.filter(tipo=TipoAtendimento.FISIOTERAPIA).distinct()
    atendimentos_multidisciplinares = atendimentos.filter(tipo=TipoAtendimento.MULTIDISCIPLINAR).distinct()

    dados2 = list()
    aluno_tipo_aval_bio = avaliacao_biomedica.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_aval_bio = avaliacao_biomedica.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_aval_bio = avaliacao_biomedica.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_aval_bio = avaliacao_biomedica.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_medico = atendimentos_medicos.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_medico = atendimentos_medicos.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_medico = atendimentos_medicos.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_medico = atendimentos_medicos.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_enf = atendimentos_enfermagem.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_enf = atendimentos_enfermagem.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_enf = atendimentos_enfermagem.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_enf = atendimentos_enfermagem.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_odonto = atendimentos_odontologico.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_odonto = atendimentos_odontologico.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_odonto = atendimentos_odontologico.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_odonto = atendimentos_odontologico.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_psicologia = atendimentos_psicologico.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_psicologia = atendimentos_psicologico.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_psicologia = atendimentos_psicologico.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_psicologia = atendimentos_psicologico.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_nutricao = atendimentos_nutricional.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_nutricao = atendimentos_nutricional.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_nutricao = atendimentos_nutricional.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_nutricao = atendimentos_nutricional.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_fisio = atendimentos_fisioterapia.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_fisio = atendimentos_fisioterapia.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_fisio = atendimentos_fisioterapia.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_fisio = atendimentos_fisioterapia.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    aluno_tipo_multi = atendimentos_multidisciplinares.filter(aluno__isnull=False).distinct('aluno').count()
    servidor_tipo_multi = atendimentos_multidisciplinares.filter(servidor__isnull=False).distinct('servidor').count()
    prest_serv_tipo_multi = atendimentos_multidisciplinares.filter(prestador_servico__isnull=False).distinct('prestador_servico').count()
    comun_ext_tipo_multi = atendimentos_multidisciplinares.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True).count()

    series2 = []

    serie = ['Alunos']
    serie.append(aluno_tipo_aval_bio)
    serie.append(aluno_tipo_medico)
    serie.append(aluno_tipo_enf)
    serie.append(aluno_tipo_odonto)
    serie.append(aluno_tipo_psicologia)
    serie.append(aluno_tipo_nutricao)
    serie.append(aluno_tipo_fisio)
    serie.append(aluno_tipo_multi)
    series2.append(serie)

    serie = ['Servidores']
    serie.append(servidor_tipo_aval_bio)
    serie.append(servidor_tipo_medico)
    serie.append(servidor_tipo_enf)
    serie.append(servidor_tipo_odonto)
    serie.append(servidor_tipo_psicologia)
    serie.append(servidor_tipo_nutricao)
    serie.append(servidor_tipo_fisio)
    serie.append(servidor_tipo_multi)
    series2.append(serie)

    serie = ['Prestadores de Serviço']
    serie.append(prest_serv_tipo_aval_bio)
    serie.append(prest_serv_tipo_medico)
    serie.append(prest_serv_tipo_enf)
    serie.append(prest_serv_tipo_odonto)
    serie.append(prest_serv_tipo_psicologia)
    serie.append(prest_serv_tipo_nutricao)
    serie.append(prest_serv_tipo_fisio)
    serie.append(prest_serv_tipo_multi)
    series2.append(serie)

    serie = ['Comunidade Externa']
    serie.append(comun_ext_tipo_aval_bio)
    serie.append(comun_ext_tipo_medico)
    serie.append(comun_ext_tipo_enf)
    serie.append(comun_ext_tipo_odonto)
    serie.append(comun_ext_tipo_psicologia)
    serie.append(comun_ext_tipo_nutricao)
    serie.append(comun_ext_tipo_fisio)
    serie.append(comun_ext_tipo_multi)
    series2.append(serie)

    groups = []
    for tipo in ['Avaliação Biomédica', 'Médico', 'Enfermagem', 'Odontologia', 'Psicologia', 'Nutrição', 'Fisioterapia', 'Multidisciplinar']:
        groups.append(tipo)

    grafico2 = GroupedColumnChart(
        'grafico2',
        title='Atendidos por Vínculo e Tipo de Atendimento',
        subtitle='Quantidade de pacientes únicos atendidos',
        data=series2,
        groups=groups,
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
    )
    setattr(grafico2, 'id', 'grafico2')

    dados3 = list()
    alunos = atendimentos.filter(aluno__isnull=False)
    servidor = atendimentos.filter(servidor__isnull=False)
    prestador_servico = atendimentos.filter(prestador_servico__isnull=False)
    comunidade_externa = atendimentos.filter(aluno__isnull=True, servidor__isnull=True, prestador_servico__isnull=True)

    if alunos.count() > 0:
        dados3.append(['Alunos', alunos.count()])
    if servidor.count() > 0:
        dados3.append(['Servidores', servidor.count()])
    if prestador_servico.count() > 0:
        dados3.append(['Prestadores de Serviço', prestador_servico.count()])
    if comunidade_externa.count() > 0:
        dados3.append(['Comunidade Externa', comunidade_externa.count()])

    grafico3 = PieChart('grafico3', title='Atendimentos por Vínculo', subtitle='Quantidade de atendimentos por vínculo do paciente', minPointLength=0, data=dados3)
    setattr(grafico3, 'id', 'grafico3')

    dados4 = list()
    alunos_atendidos = alunos.distinct('aluno').count()
    servidor_atendidos = servidor.distinct('servidor').count()
    prestador_servico_atendidos = prestador_servico.distinct('prestador_servico').count()
    comunidade_externa_atendidos = comunidade_externa.distinct('prontuario__vinculo').count()

    if alunos_atendidos > 0:
        dados4.append(['Alunos', alunos_atendidos])
    if servidor_atendidos > 0:
        dados4.append(['Servidores', servidor_atendidos])
    if prestador_servico_atendidos > 0:
        dados4.append(['Prestadores de Serviço', prestador_servico_atendidos])
    if comunidade_externa_atendidos > 0:
        dados4.append(['Comunidade Externa', comunidade_externa_atendidos])

    grafico4 = PieChart('grafico4', title='Atendidos por Vínculo', subtitle='Quantidade de pacientes únicos atendidos por vínculo do paciente', minPointLength=0, data=dados4)
    setattr(grafico4, 'id', 'grafico4')

    dados5 = list()

    alunos_aval_bio = avaliacao_biomedica.filter(aluno__isnull=False).distinct('aluno')
    alunos_tipo_medico = atendimentos_medicos.filter(aluno__isnull=False).distinct('aluno')
    alunos_tipo_enf = atendimentos_enfermagem.filter(aluno__isnull=False).distinct('aluno')
    alunos_tipo_odonto = atendimentos_odontologico.filter(aluno__isnull=False).distinct('aluno')
    alunos_tipo_psicologia = atendimentos_psicologico.filter(aluno__isnull=False).distinct('aluno')
    alunos_tipo_fisio = atendimentos_fisioterapia.filter(aluno__isnull=False).distinct('aluno')

    participantes = Participacao.abertas.all()
    alunos_aval_bio_part = alunos_aval_bio.filter(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_aval_bio_nao_part = alunos_aval_bio.exclude(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_medico_part = alunos_tipo_medico.filter(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_medico_nao_part = alunos_tipo_medico.exclude(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_enf_part = alunos_tipo_enf.filter(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_enf_nao_part = alunos_tipo_enf.exclude(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_odonto_part = alunos_tipo_odonto.filter(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_odonto_nao_part = alunos_tipo_odonto.exclude(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_psicologia_part = alunos_tipo_psicologia.filter(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_psicologia_nao_part = alunos_tipo_psicologia.exclude(aluno__in=participantes.values_list('aluno', flat=True)).count()

    alunos_tipo_fisio_part = alunos_tipo_fisio.filter(aluno__in=participantes.values_list('aluno', flat=True)).count()
    alunos_tipo_fisio_nao_part = alunos_tipo_fisio.exclude(aluno__in=participantes.values_list('aluno', flat=True)).count()
    series2 = []

    serie = ['Avaliação Biomédica']
    serie.append(alunos_aval_bio_part)
    serie.append(alunos_aval_bio_nao_part)
    series2.append(serie)

    serie = ['Médicos']
    serie.append(alunos_tipo_medico_part)
    serie.append(alunos_tipo_medico_nao_part)
    series2.append(serie)

    serie = ['Enfermagem']
    serie.append(alunos_tipo_enf_part)
    serie.append(alunos_tipo_enf_nao_part)
    series2.append(serie)

    serie = ['Odontologia']
    serie.append(alunos_tipo_odonto_part)
    serie.append(alunos_tipo_odonto_nao_part)
    series2.append(serie)

    serie = ['Psicologia']
    serie.append(alunos_tipo_psicologia_part)
    serie.append(alunos_tipo_psicologia_nao_part)
    series2.append(serie)

    serie = ['Fisioterapia']
    serie.append(alunos_tipo_fisio_part)
    serie.append(alunos_tipo_fisio_nao_part)
    series2.append(serie)

    groups = []
    for tipo in ['Participantes', 'Não Participantes']:
        groups.append(tipo)

    grafico5 = GroupedColumnChart(
        'grafico5',
        title='Atendidos por Categoria Profissional e Participação em Programa',
        subtitle='Quantidade de alunos únicos atendidos por categoria profissional, participantes ou não de programas',
        data=series2,
        groups=groups,
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
    )

    setattr(grafico5, 'id', 'grafico5')

    alunos_ensino_medio_integrado = alunos.filter(aluno__curso_campus__modalidade=Modalidade.INTEGRADO)
    total_alunos = Aluno.objects.filter(curso_campus__modalidade=Modalidade.INTEGRADO)
    if not request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
        total_alunos = total_alunos.filter(curso_campus__diretoria__setor__uo=get_uo(request.user))

    if form.is_valid() and form.cleaned_data.get('uo'):
        total_alunos = total_alunos.filter(curso_campus__diretoria__setor__uo=form.cleaned_data.get('uo'))

    if form.is_valid() and form.cleaned_data.get('data_inicio'):
        alunos_ensino_medio_integrado = alunos_ensino_medio_integrado.filter(
            aluno__data_matricula__gte=form.cleaned_data['data_inicio'], aluno__data_matricula__lte=form.cleaned_data['data_termino']
        )
        total_alunos = total_alunos.filter(data_matricula__gte=form.cleaned_data['data_inicio'], data_matricula__lte=form.cleaned_data['data_termino'])
    else:
        alunos_ensino_medio_integrado = alunos_ensino_medio_integrado.filter(aluno__data_matricula__year=datetime.datetime.now().year)
        total_alunos = total_alunos.filter(data_matricula__year=datetime.datetime.now().year)

    groups = []
    for tipo in ['Alunos Ingressantes com Avaliação Biomédica', 'Total de Alunos Ingressantes']:
        groups.append(tipo)

    series2 = []
    serie = ['Alunos']
    serie.append(alunos_ensino_medio_integrado.distinct('aluno').count())
    serie.append(total_alunos.count())
    series2.append(serie)

    grafico6 = GroupedColumnChart(
        'grafico6',
        title='Percentual de alunos Ingressantes do Integrado com Avaliação Biomédica',
        subtitle='Percentual de alunos ingressantes do Integrado com Avaliação Biomédica em relação ao total de alunos ingressantes',
        minPointLength=0,
        data=series2,
        groups=groups,
    )
    setattr(grafico6, 'id', 'grafico6')

    pie_chart_lists = [grafico2, grafico3, grafico4, grafico5, grafico6]

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS_ATENDIMENTO_MEDICO_ENF)
def remover_previsao(request, vacinacao_id):
    vacinacao = get_object_or_404(CartaoVacinal, pk=vacinacao_id)
    vacinacao.data_prevista = None
    vacinacao.save()
    return httprr(f'/saude/prontuario/{vacinacao.prontuario.vinculo_id}/?tab=aba_cartao_vacinal', 'Aprazamento removido com sucesso.')


@rtr()
@permission_required('saude.view_atividadegrupo')
def atividade_em_grupo(request, atividade_id):
    atividade = get_object_or_404(AtividadeGrupo, pk=atividade_id)
    title = f'Atividade em Grupo - {atividade.tipo} ({atividade.uo})'

    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_antropometria(request):
    title = 'Gráficos - Antropometria'

    registros = Antropometria.objects.filter(atendimento__aluno__isnull=False, estatura__gt=0)

    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))

        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if registros.exists():

            dados = list()
            dados2 = list()
            dados3 = list()
            dados4 = list()
            dados5 = list()
            dados6 = list()
            from dateutil.relativedelta import relativedelta

            hoje = datetime.datetime.today().date()
            mais_19_anos = hoje - relativedelta(years=19)
            imc_adultos = registros.filter(atendimento__aluno__pessoa_fisica__nascimento_data__lte=mais_19_anos).annotate(
                imc=ExpressionWrapper(F('peso') / ((F('estatura') / 100.0) * (F('estatura') / 100.0)), output_field=DecimalField())
            )

            dados.append(['Excesso de magreza', imc_adultos.filter(imc__lte=18.4).count()])
            dados.append(['Peso normal', imc_adultos.filter(imc__gt=18.4, imc__lte=24).count()])
            dados.append(['Acima do peso', imc_adultos.filter(imc__gt=15, imc__lte=29).count()])
            dados.append(['Obesidade grau 1', imc_adultos.filter(imc__gt=30, imc__lte=34).count()])
            dados.append(['Obesidade grau 2', imc_adultos.filter(imc__gt=35, imc__lte=39).count()])
            dados.append(['Obesidade grau 3 ou mórbida', imc_adultos.filter(imc__gt=40).count()])

            grafico1 = PieChart(
                'grafico1',
                title='Índice de Massa Corporal (IMC) - Alunos Maiores de 19 anos - Geral',
                subtitle='Classificação do IMC para alunos maiores de 19 anos - geral',
                minPointLength=0,
                data=dados,
            )

            setattr(grafico1, 'id', 'grafico1')

            homens = imc_adultos.filter(atendimento__aluno__pessoa_fisica__sexo='M')
            dados2.append(['Excesso de magreza', homens.filter(imc__lte=18.4).count()])
            dados2.append(['Peso normal', homens.filter(imc__gt=18.4, imc__lte=24).count()])
            dados2.append(['Acima do peso', homens.filter(imc__gt=15, imc__lte=29).count()])
            dados2.append(['Obesidade grau 1', homens.filter(imc__gt=30, imc__lte=34).count()])
            dados2.append(['Obesidade grau 2', homens.filter(imc__gt=35, imc__lte=39).count()])
            dados2.append(['Obesidade grau 3 ou mórbida', homens.filter(imc__gt=40).count()])

            grafico2 = PieChart(
                'grafico2',
                title='Índice de Massa Corporal (IMC) - Alunos Maiores de 19 anos - Homens',
                subtitle='Classificação do IMC para alunos maiores de 19 anos - Homens',
                minPointLength=0,
                data=dados2,
            )

            setattr(grafico2, 'id', 'grafico2')

            mulheres = imc_adultos.filter(atendimento__aluno__pessoa_fisica__sexo='F')
            dados3.append(['Excesso de magreza', mulheres.filter(imc__lte=18.4).count()])
            dados3.append(['Peso normal', mulheres.filter(imc__gt=18.4, imc__lte=24).count()])
            dados3.append(['Acima do peso', mulheres.filter(imc__gt=15, imc__lte=29).count()])
            dados3.append(['Obesidade grau 1', mulheres.filter(imc__gt=30, imc__lte=34).count()])
            dados3.append(['Obesidade grau 2', mulheres.filter(imc__gt=35, imc__lte=39).count()])
            dados3.append(['Obesidade grau 3 ou mórbida', mulheres.filter(imc__gt=40).count()])

            grafico3 = PieChart(
                'grafico3',
                title='Índice de Massa Corporal (IMC) - Alunos Maiores de 19 anos - Mulheres',
                subtitle='Classificação do IMC para alunos maiores de 19 anos - Mulheres',
                minPointLength=0,
                data=dados3,
            )

            setattr(grafico3, 'id', 'grafico3')

            jovens = registros.filter(atendimento__aluno__pessoa_fisica__nascimento_data__gte=mais_19_anos)
            ex_magreza_homem = 0
            magreza_homem = 0
            eutrofia_homem = 0
            sobrepeso_homem = 0
            obesidade_homem = 0
            obesidade_grave_homem = 0

            ex_magreza_mulher = 0
            magreza_mulher = 0
            eutrofia_mulher = 0
            sobrepeso_mulher = 0
            obesidade_mulher = 0
            obesidade_grave_mulher = 0

            for registro in jovens.filter(atendimento__aluno__pessoa_fisica__sexo='M'):
                idade_registro = registro.atendimento.prontuario.vinculo.pessoa.pessoafisica.idade
                tem_idade = False
                try:
                    int(idade_registro)
                    tem_idade = True
                except Exception:
                    pass
                if tem_idade and int(idade_registro) >= 10 and int(idade_registro) <= 19:
                    indice_z = registro.get_imc_jovens()
                    if indice_z < -3:
                        ex_magreza_homem = ex_magreza_homem + 1
                    elif indice_z >= -3 and indice_z < -2:
                        magreza_homem = magreza_homem + 1
                    elif indice_z >= -2 and indice_z < 1:
                        eutrofia_homem = eutrofia_homem + 1

                    elif indice_z >= 1 and indice_z < 2:
                        sobrepeso_homem = sobrepeso_homem + 1

                    elif indice_z >= 2 and indice_z < 3:
                        obesidade_homem = obesidade_homem + 1
                    elif indice_z > 3:
                        obesidade_grave_homem = obesidade_grave_homem + 1

            for registro in jovens.filter(atendimento__aluno__pessoa_fisica__sexo='F'):
                idade_registro = registro.atendimento.prontuario.vinculo.pessoa.pessoafisica.idade
                tem_idade = False
                try:
                    int(idade_registro)
                    tem_idade = True
                except Exception:
                    pass
                if tem_idade and int(idade_registro) >= 10 and int(idade_registro) <= 19:
                    indice_z = registro.get_imc_jovens()
                    if indice_z < -3:
                        ex_magreza_mulher = ex_magreza_mulher + 1
                    elif indice_z >= -3 and indice_z < -2:
                        magreza_mulher = magreza_mulher + 1
                    elif indice_z >= -2 and indice_z < 1:
                        eutrofia_mulher = eutrofia_mulher + 1

                    elif indice_z >= 1 and indice_z < 2:
                        sobrepeso_mulher = sobrepeso_mulher + 1

                    elif indice_z >= 2 and indice_z < 3:
                        obesidade_mulher = obesidade_mulher + 1
                    elif indice_z > 3:
                        obesidade_grave_mulher = obesidade_grave_mulher + 1

            dados4.append(['Magreza acentuada', ex_magreza_homem + ex_magreza_mulher])
            dados4.append(['Magreza', magreza_homem + magreza_mulher])
            dados4.append(['Eutrofia', eutrofia_homem + eutrofia_mulher])
            dados4.append(['Sobrepeso', sobrepeso_homem + sobrepeso_mulher])
            dados4.append(['Obesidade', obesidade_homem + obesidade_mulher])
            dados4.append(['Obesidade grave', obesidade_grave_homem + obesidade_grave_mulher])

            grafico4 = PieChart(
                'grafico4',
                title='Índice de Massa Corporal (IMC) - Alunos Menores de 19 anos - Geral',
                subtitle='Classificação do IMC para alunos menores de 19 anos - geral',
                minPointLength=0,
                data=dados4,
            )

            setattr(grafico4, 'id', 'grafico4')

            dados5.append(['Magreza acentuada', ex_magreza_homem])
            dados5.append(['Magreza', magreza_homem])
            dados5.append(['Eutrofia', eutrofia_homem])
            dados5.append(['Sobrepeso', sobrepeso_homem])
            dados5.append(['Obesidade', obesidade_homem])
            dados5.append(['Obesidade grave', obesidade_grave_homem])

            grafico5 = PieChart(
                'grafico5',
                title='Índice de Massa Corporal (IMC) - Alunos Menores de 19 anos - Homens',
                subtitle='Classificação do IMC para alunos menores de 19 anos - Homens',
                minPointLength=0,
                data=dados5,
            )

            setattr(grafico5, 'id', 'grafico5')

            dados6.append(['Magreza acentuada', ex_magreza_mulher])
            dados6.append(['Magreza', magreza_mulher])
            dados6.append(['Eutrofia', eutrofia_mulher])
            dados6.append(['Sobrepeso', sobrepeso_mulher])
            dados6.append(['Obesidade', obesidade_mulher])
            dados6.append(['Obesidade grave', obesidade_grave_mulher])

            grafico6 = PieChart(
                'grafico6',
                title='Índice de Massa Corporal (IMC) - Alunos Menores de 19 anos - Mulheres',
                subtitle='Classificação do IMC para alunos menores de 19 anos - Mulheres',
                minPointLength=0,
                data=dados6,
            )

            setattr(grafico6, 'id', 'grafico6')

            normal_mulheres = 0
            sobrepeso_mulheres = 0
            obesidade_mulheres = 0
            normal_homens = 0
            sobrepeso_homens = 0
            obesidade_homens = 0

            registros = Antropometria.objects.filter(atendimento__aluno__isnull=False)
            if 'xls' in request.GET:
                return tasks.graficos_antropometria_to_xls(registros)
            mulheres = registros.filter(atendimento__aluno__pessoa_fisica__sexo='F')
            homens = registros.filter(atendimento__aluno__pessoa_fisica__sexo='M')
            for item in mulheres:
                iac = item.get_IAC()
                if iac:
                    if iac >= 21 and iac <= 32:
                        normal_mulheres = normal_mulheres + 1

                    elif iac >= 33 and iac <= 38:
                        sobrepeso_mulheres = sobrepeso_mulheres + 1
                    elif iac > 38:
                        obesidade_mulheres = obesidade_mulheres + 1

            for item in homens:
                iac = item.get_IAC()
                if iac:
                    if iac >= 8 and iac <= 20:
                        normal_homens = normal_homens + 1

                    elif iac >= 21 and iac <= 25:
                        sobrepeso_homens = sobrepeso_homens + 1
                    elif iac > 25:
                        obesidade_homens = obesidade_homens + 1

            dados7 = list()
            dados8 = list()
            dados9 = list()

            dados7.append(['Normal', normal_homens + normal_mulheres])
            dados7.append(['Sobrepeso', sobrepeso_homens + sobrepeso_mulheres])
            dados7.append(['Obesidade', obesidade_homens + obesidade_mulheres])

            grafico7 = PieChart(
                'grafico7',
                title='Classificação do Índice de Adiposidade Corporal (IAC) - Geral',
                subtitle='Classificação do Índice de Adiposidade Corporal de todos os alunos',
                minPointLength=0,
                data=dados7,
            )
            setattr(grafico7, 'id', 'grafico7')

            dados8.append(['Normal', normal_homens])
            dados8.append(['Sobrepeso', sobrepeso_homens])
            dados8.append(['Obesidade', obesidade_homens])
            grafico8 = PieChart(
                'grafico8',
                title='Classificação do Índice de Adiposidade Corporal (IAC) - Homens',
                subtitle='Classificação do Índice de Adiposidade Corporal - Homens',
                minPointLength=0,
                data=dados8,
            )
            setattr(grafico8, 'id', 'grafico8')

            dados9.append(['Normal', normal_mulheres])
            dados9.append(['Sobrepeso', sobrepeso_mulheres])
            dados9.append(['Obesidade', obesidade_mulheres])
            grafico9 = PieChart(
                'grafico9',
                title='Classificação do Índice de Adiposidade Corporal (IAC) - Mulheres',
                subtitle='Classificação do Índice de Adiposidade Corporal - Mulheres',
                minPointLength=0,
                data=dados9,
            )
            setattr(grafico9, 'id', 'grafico9')

            dados10 = list()
            dados11 = list()
            dados12 = list()

            total_homens = {'Baixo': 0, 'Moderado': 0, 'Alto': 0, 'Muito alto': 0}
            total_mulheres = {'Baixo': 0, 'Moderado': 0, 'Alto': 0, 'Muito alto': 0}
            for item in homens:
                rcq = item.get_RCQ()
                if rcq:
                    inicio = rcq.index('(')
                    fim = rcq.index(')')
                    total_homens[rcq[inicio + 1: fim]] = total_homens[rcq[inicio + 1: fim]] + 1

            dados11.append(['Baixo', total_homens['Baixo']])
            dados11.append(['Moderado', total_homens['Moderado']])
            dados11.append(['Alto', total_homens['Alto']])
            dados11.append(['Muito alto', total_homens['Muito alto']])

            for item in mulheres:
                rcq = item.get_RCQ()
                if rcq:
                    inicio = rcq.index('(')
                    fim = rcq.index(')')
                    total_mulheres[rcq[inicio + 1: fim]] = total_mulheres[rcq[inicio + 1: fim]] + 1

            dados12.append(['Baixo', total_mulheres['Baixo']])
            dados12.append(['Moderado', total_mulheres['Moderado']])
            dados12.append(['Alto', total_mulheres['Alto']])
            dados12.append(['Muito alto', total_mulheres['Muito alto']])

            dados10.append(['Baixo', total_homens['Baixo'] + total_mulheres['Baixo']])
            dados10.append(['Moderado', total_homens['Moderado'] + total_mulheres['Moderado']])
            dados10.append(['Alto', total_homens['Alto'] + total_mulheres['Alto']])
            dados10.append(['Muito alto', total_homens['Muito alto'] + total_mulheres['Muito alto']])

            grafico10 = PieChart(
                'grafico10', title='Razão Cintura-Quadril (RCQ) - Geral', subtitle='Classificação da Razão Cintura-Quadril dos alunos', minPointLength=0, data=dados10
            )
            setattr(grafico10, 'id', 'grafico11')

            grafico11 = PieChart(
                'grafico11', title='Razão Cintura-Quadril (RCQ) - Homens', subtitle='Classificação da Razão Cintura-Quadril dos alunos - Homens', minPointLength=0, data=dados11
            )
            setattr(grafico11, 'id', 'grafico11')

            grafico12 = PieChart(
                'grafico12', title='Razão Cintura-Quadril (RCQ) - Mulheres', subtitle='Classificação da Razão Cintura-Quadril dos alunos - Mulheres', minPointLength=0, data=dados12
            )
            setattr(grafico12, 'id', 'grafico12')

            pie_chart_lists = [grafico1, grafico2, grafico3, grafico4, grafico5, grafico6, grafico7, grafico8, grafico9, grafico10, grafico11, grafico12]
    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_acuidade_visual(request):
    title = 'Gráficos - Acuidade Visual'

    registros = AcuidadeVisual.objects.all()
    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))

        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if 'xls' in request.GET:
            return tasks.exportar_graficos_acuidade_visual_to_xls(registros)

        if registros.exists():
            dados = list()
            olho_esquerdo = registros.values('olho_esquerdo').annotate(qtd=Count('olho_esquerdo')).order_by('olho_esquerdo')

            for registro in olho_esquerdo:
                dados.append([str(registro['olho_esquerdo']), registro['qtd']])
            if dados and dados[-1][1] == 0:
                dados.pop()

            grafico1 = PieChart('grafico1', title='Acuidade Visual - Olho Esquerdo', subtitle='Classificação por Acuidade Visual', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            olho_direito = registros.values('olho_direito').annotate(qtd=Count('olho_direito')).order_by('olho_direito')
            dados2 = list()
            for registro in olho_direito:
                dados2.append([str(registro['olho_direito']), registro['qtd']])
            if dados2 and dados2[-1][1] == 0:
                dados2.pop()

            grafico2 = PieChart('grafico2', title='Acuidade Visual - Olho Direito', subtitle='Classificação por Acuidade Visual', minPointLength=0, data=dados2)

            setattr(grafico2, 'id', 'grafico2')

            correcao = registros.values('com_correcao').annotate(qtd=Count('com_correcao')).order_by('com_correcao')
            dados3 = list()
            for registro in correcao:
                if registro['com_correcao']:
                    dados3.append(['Com correção', registro['qtd']])
                else:
                    dados3.append(['Sem correção', registro['qtd']])

            if dados3 and dados3[-1][1] == 0:
                dados3.pop()

            grafico3 = PieChart('grafico3', title='Acuidade Visual - Com ou Sem Correção', subtitle='Classificação por Acuidade Visual', minPointLength=0, data=dados3)

            setattr(grafico3, 'id', 'grafico3')

            pie_chart_lists = [grafico3, grafico1, grafico2]

    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_saude_doenca(request):
    title = 'Gráficos - Processo Saúde-Doença'
    form = EstatisticasAtendimentosForm(request.GET or None, request=request, exibe_vinculo=True)
    if form.is_valid():
        registros = ProcessoSaudeDoenca.objects.all().order_by('-id')
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))

        if int(form.cleaned_data['vinculo']) == Vinculo.ALUNO:
            registros = registros.filter(atendimento__aluno__isnull=False)

        elif int(form.cleaned_data['vinculo']) == Vinculo.SERVIDOR:
            registros = registros.filter(atendimento__servidor__isnull=False)

        elif int(form.cleaned_data['vinculo']) == Vinculo.PRESTADOR_SERVICO:
            registros = registros.filter(atendimento__prestador_servico__isnull=False)

        elif int(form.cleaned_data['vinculo']) == Vinculo.COMUNIDADE_EXTERNA:
            registros = registros.filter(atendimento__servidor__isnull=True, atendimento__prestador_servico__isnull=True, atendimento__aluno__isnull=True)

        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if 'xls' in request.GET:
            return tasks.graficos_saude_doenca_to_xls(registros)

        if registros.exists():
            dados = list()
            doencas_cronicas = registros.values('doencas_cronicas__nome').annotate(qtd=Count('doencas_cronicas__nome')).order_by('doencas_cronicas__nome')

            for registro in doencas_cronicas:
                dados.append([registro['doencas_cronicas__nome'], registro['qtd']])
            if dados and dados[-1][1] == 0:
                dados.pop()

            grafico1 = PieChart('grafico1', title='Doenças Crônicas', subtitle='Classificação por Doença Crônica', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            problema_auditivo = registros.values('problema_auditivo').annotate(qtd=Count('problema_auditivo')).order_by('problema_auditivo')
            dados2 = list()
            for registro in problema_auditivo:
                if registro['problema_auditivo']:
                    dados2.append(['Possui Problema Auditivo', registro['qtd']])
                else:
                    dados2.append(['Não Possui Problema Auditivo', registro['qtd']])
            if dados2 and dados2[-1][1] == 0:
                dados2.pop()

            grafico2 = PieChart('grafico2', title='Problema Auditivo', subtitle='Classificação por Problema Auditivo', minPointLength=0, data=dados2)

            setattr(grafico2, 'id', 'grafico2')

            gestante = registros.filter(atendimento__aluno__pessoa_fisica__sexo='F').values('gestante').annotate(qtd=Count('gestante')).order_by('gestante')
            dados3 = list()
            for registro in gestante:
                if registro['gestante']:
                    dados3.append(['Gestante', registro['qtd']])
                else:
                    dados3.append(['Não é gestante', registro['qtd']])

            if dados3 and dados3[-1][1] == 0:
                dados3.pop()

            grafico3 = PieChart('grafico3', title='Alunas Gestantes', subtitle='Quantidade de Alunas Gestantes', minPointLength=0, data=dados3)

            setattr(grafico3, 'id', 'grafico3')

            pie_chart_lists = [grafico1, grafico2, grafico3]

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def adicionar_anotacao_interdisciplinar(request, prontuario_id):
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)
    title = 'Adicionar Anotação Interdisciplinar'
    anotacao = AnotacaoInterdisciplinar()
    form = AnotacaoInterdisciplinarForm(request.POST or None)
    if form.is_valid():
        anotacao.profissional = request.user.get_relacionamento()
        anotacao.data = datetime.datetime.now()
        anotacao.prontuario = prontuario
        anotacao.anotacao = form.cleaned_data.get('anotacao')
        anotacao.save()
        return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_anotacoes_interdisciplinares', 'Anotação registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Psicólogo'])
def atendimento_psicologico(request, atendimento_id):
    title = 'Atendimento Psicológico'
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.PSICOLOGICO)
    if not (atendimento.usuario_aberto == request.user):
        raise PermissionDenied()
    pode_editar = False
    eh_psicologia = True
    if atendimento.aluno:
        programas = Participacao.objects.filter(aluno=atendimento.get_vinculo(), data_termino__isnull=True)
    is_coordenador_sistemico = in_group(request.user, 'Coordenador de Saúde Sistêmico')
    especialidade = Especialidades(request.user)
    is_medico = especialidade.is_medico()
    is_enfermagem = especialidade.is_enfermeiro() or especialidade.is_tecnico_enfermagem() or especialidade.is_auxiliar_enfermagem()
    atendimento_psicologia = AtendimentoPsicologia.objects.filter(atendimento=atendimento)
    atendimento_psicologia_responsavel = False
    if atendimento_psicologia.exists():
        atendimento_psicologia = atendimento_psicologia[0]
        atendimento_psicologia_responsavel = atendimento_psicologia.get_responsavel()
        if atendimento_psicologia.profissional != request.user:
            pode_editar = False
        else:
            pode_editar = True

    anexos = AnexoPsicologia.objects.filter(atendimento=atendimento)
    historicos = (
        AtendimentoPsicologia.objects.filter(atendimento__prontuario=atendimento.prontuario, atendimento__usuario_aberto=request.user)
        .exclude(atendimento__id=atendimento.id)
        .order_by('-id')
    )

    return locals()


@rtr()
@group_required(['Psicólogo'])
def adicionar_anamnese_psicologica(request, vinculo_id):
    vinculo = get_object_or_404(VinculoPessoa, id=vinculo_id)
    prontuario = Prontuario.get_prontuario(vinculo)
    title = f'Adicionar Anamnese - {vinculo}'
    obj = AnamnesePsicologia.objects.filter(prontuario=prontuario, profissional=request.user)
    if obj.exists():
        obj = obj.latest('id')
    else:
        obj = AnamnesePsicologia()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.prontuario = prontuario
    form = AnamnesePsicologiaForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/prontuario/{vinculo_id}/?tab=aba_anamnese_psicologia', 'Anamnese registrada com sucesso.')
    return locals()


@rtr()
@group_required(['Odontólogo'])
def ordem_plano_tratamento(request, item_plano_tratamento, tipo):
    item = get_object_or_404(PlanoTratamento, pk=item_plano_tratamento)
    atendimento = item.atendimento
    tem_permissao(atendimento, request)
    if tipo == '1':
        posicao_atual = item.ordem
        if PlanoTratamento.objects.filter(atendimento=item.atendimento, ordem__lt=posicao_atual).exists():
            item_acima = PlanoTratamento.objects.filter(atendimento=item.atendimento, ordem__lt=posicao_atual).order_by('-ordem')[0]
            posicao_anterior = item_acima.ordem
            item_acima.ordem = posicao_atual
            item.ordem = posicao_anterior
            item_acima.save()
            item.save()
    elif tipo == '2':
        posicao_atual = item.ordem
        if PlanoTratamento.objects.filter(atendimento=item.atendimento, ordem__gt=posicao_atual).exists():
            item_acima = PlanoTratamento.objects.filter(atendimento=item.atendimento, ordem__gt=posicao_atual).order_by('ordem')[0]
            posicao_posterior = item_acima.ordem
            item_acima.ordem = posicao_atual
            item.ordem = posicao_posterior
            item_acima.save()
            item.save()

    return httprr(f'/saude/atendimento_odontologico/{item.atendimento_id}/?tab=aba_plano_tratamento', 'Ordem do plano de tratamento alterada com sucesso.')


@rtr()
@group_required(['Odontólogo'])
def resolver_exame_periodontal(request, exame_id):
    exame = get_object_or_404(ExamePeriodontal, pk=exame_id)
    exame.resolvido = True
    exame.save()
    return httprr(f'/saude/atendimento_odontologico/{exame.atendimento_id}/?tab=aba_situacao_clinica', 'Exame periodontal alterado com sucesso.')


@rtr('historico_ficha.html')
@group_required(['Odontólogo'])
def historico_exame_estomatologico(request, atendimento_id):
    title = 'Histórico dos Exames Estomatológicos'
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    historico = ExameEstomatologico.objects.filter(atendimento=atendimento).order_by('-id')
    default_exclude = ('id', 'atendimento_id', 'profissional_id', 'data_cadastro')
    fields = [f.get_attname() for f in ExameEstomatologico._meta.get_fields() if f.get_attname() not in default_exclude]
    table_historico = get_table(queryset=historico, fields=fields)
    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_habitos_vida(request):
    title = 'Gráficos - Hábitos de Vida'
    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        registros = HabitosDeVida.objects.all().order_by('-id')
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))
        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if 'xls' in request.GET:
            return tasks.graficos_habitos_vida_to_xls(registros)
        if registros.exists():
            dados = list()
            pratica_atividade_fisica = registros.values('atividade_fisica').annotate(qtd=Count('atividade_fisica')).order_by('atividade_fisica')

            for registro in pratica_atividade_fisica:
                if registro['atividade_fisica']:
                    dados.append(['Pratica Atividade Física', registro['qtd']])
                else:
                    dados.append(['Não Pratica Atividade Física', registro['qtd']])

            grafico1 = PieChart('grafico1', title='Prática de Atividade Física', subtitle='Classificação por Prática de Atividade Física', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            frequencia_semanal = registros.filter(atividade_fisica=True).values('frequencia_semanal').annotate(qtd=Count('frequencia_semanal')).order_by('frequencia_semanal')
            dados2 = list()
            for registro in frequencia_semanal:
                if registro['frequencia_semanal'] == 2:
                    dados2.append(['Menos de 3x/semana', registro['qtd']])
                elif registro['frequencia_semanal'] == 3:
                    dados2.append(['3 ou mais x/semana', registro['qtd']])
                else:
                    dados2.append(['Não Informado', registro['qtd']])

            grafico2 = PieChart(
                'grafico2', title='Prática de Atividade Física - Frequencia Semanal', subtitle='Classificação por Frequencia Semanal', minPointLength=0, data=dados2
            )

            setattr(grafico2, 'id', 'grafico2')

            duracao_atividade = registros.filter(atividade_fisica=True).values('duracao_atividade').annotate(qtd=Count('duracao_atividade')).order_by('duracao_atividade')
            dados3 = list()
            for registro in duracao_atividade:
                if registro['duracao_atividade'] == 2:
                    dados3.append(['Menos de 50 min/dia', registro['qtd']])
                elif registro['duracao_atividade'] == 3:
                    dados3.append(['50 min ou mais/dia', registro['qtd']])
                else:
                    dados3.append(['Não Informado', registro['qtd']])

            grafico3 = PieChart('grafico3', title='Prática de Atividade Física - Duração', subtitle='Duração da Atividade Física', minPointLength=0, data=dados3)

            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            fumante = registros.values('fuma').annotate(qtd=Count('fuma')).order_by('fuma')

            for registro in fumante:
                if registro['fuma']:
                    dados4.append(['Fumante', registro['qtd']])
                else:
                    dados4.append(['Não Fumante', registro['qtd']])

            grafico4 = PieChart('grafico4', title='Fumantes', subtitle='Classificação por Fumante', minPointLength=0, data=dados4)

            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            etilista = registros.values('bebe').annotate(qtd=Count('bebe')).order_by('bebe')

            for registro in etilista:
                if registro['bebe']:
                    dados5.append(['Consome Bebida Alcoólica', registro['qtd']])
                else:
                    dados5.append(['Não Consome Bebida Alcoólica', registro['qtd']])

            grafico5 = PieChart('grafico5', title='Etilista', subtitle='Classificação por Consumo de Bebida Alcoólica', minPointLength=0, data=dados5)

            setattr(grafico5, 'id', 'grafico5')

            dados6 = list()
            frequencia_bebida = registros.filter(bebe=True).values('frequencia_bebida').annotate(qtd=Count('frequencia_bebida')).order_by('frequencia_bebida')

            for registro in frequencia_bebida:
                if registro['frequencia_bebida'] == 2:
                    dados6.append(['1x/dia', registro['qtd']])
                elif registro['frequencia_bebida'] == 3:
                    dados6.append(['1x/semana', registro['qtd']])
                elif registro['frequencia_bebida'] == 4:
                    dados6.append(['1x/mês', registro['qtd']])
                elif registro['frequencia_bebida'] == 5:
                    dados6.append(['1x/ano', registro['qtd']])
                else:
                    dados6.append(['Não Informado', registro['qtd']])

            grafico6 = PieChart(
                'grafico6', title='Frequencia do Consumo de Bebida Alcoólica', subtitle='Classificação por Frequencia do Consumo de Bebida Alcoólica', minPointLength=0, data=dados6
            )

            setattr(grafico6, 'id', 'grafico6')

            dados7 = list()
            usa_drogas = registros.values('usa_drogas').annotate(qtd=Count('usa_drogas')).order_by('usa_drogas')

            for registro in usa_drogas:
                if registro['usa_drogas']:
                    dados7.append(['Usuário de Drogas', registro['qtd']])
                else:
                    dados7.append(['Não é Usuário de Drogas', registro['qtd']])

            grafico7 = PieChart('grafico7', title='Usuário de Drogas', subtitle='Classificação por Uso de Drogas', minPointLength=0, data=dados7)

            setattr(grafico7, 'id', 'grafico7')

            dados8 = list()
            que_drogas = registros.values('que_drogas__nome').annotate(qtd=Count('que_drogas__nome')).order_by('que_drogas__nome')

            for registro in que_drogas:
                if registro['que_drogas__nome']:
                    dados8.append([registro['que_drogas__nome'], registro['qtd']])
            nao_disseram_o_tipo = registros.filter(usa_drogas=True, que_drogas__isnull=True).count()
            if nao_disseram_o_tipo:
                dados8.append(['Não Informado', nao_disseram_o_tipo])

            if dados8 and dados8[-1][1] == 0:
                dados8.pop()

            grafico8 = PieChart('grafico8', title='Tipo de Droga Utilizada', subtitle='Classificação por Tipo de Droga Utilizada', minPointLength=0, data=dados8)

            setattr(grafico8, 'id', 'grafico8')

            dados9 = list()
            dificuldade_dormir = registros.values('dificuldade_dormir').annotate(qtd=Count('dificuldade_dormir')).order_by('dificuldade_dormir')

            for registro in dificuldade_dormir:
                if registro['dificuldade_dormir']:
                    dados9.append(['Tem dificuldade para dormir', registro['qtd']])
                else:
                    dados9.append(['Não tem dificuldade para dormir', registro['qtd']])

            grafico9 = PieChart('grafico9', title='Dificuldade para Dormir', subtitle='Classificação por Dificuldade para Dormir', minPointLength=0, data=dados9)

            setattr(grafico9, 'id', 'grafico9')

            dados10 = list()
            horas_sono = registros.values('horas_sono').annotate(qtd=Count('horas_sono')).order_by('horas_sono')

            for registro in horas_sono:
                if registro['horas_sono'] == 2:
                    dados10.append(['Menos de 8 horas/dia', registro['qtd']])
                elif registro['horas_sono'] == 3:
                    dados10.append(['8 ou mais horas/dia', registro['qtd']])
                else:
                    dados10.append(['Não Informado', registro['qtd']])

            grafico10 = PieChart('grafico10', title='Horas de Sono por Dia', subtitle='Classificação por Horas de Sono por Dia', minPointLength=0, data=dados10)

            setattr(grafico10, 'id', 'grafico10')

            dados11 = list()
            refeicoes_por_dia = registros.values('refeicoes_por_dia').annotate(qtd=Count('refeicoes_por_dia')).order_by('refeicoes_por_dia')

            for registro in refeicoes_por_dia:
                if registro['refeicoes_por_dia'] == 2:
                    dados11.append(['1 refeição', registro['qtd']])
                elif registro['refeicoes_por_dia'] == 3:
                    dados11.append(['2 refeições', registro['qtd']])
                elif registro['refeicoes_por_dia'] == 4:
                    dados11.append(['3 refeições', registro['qtd']])
                elif registro['refeicoes_por_dia'] == 5:
                    dados11.append(['4 refeições', registro['qtd']])
                elif registro['refeicoes_por_dia'] == 6:
                    dados11.append(['5 refeições', registro['qtd']])
                elif registro['refeicoes_por_dia'] == 7:
                    dados11.append(['6 refeições', registro['qtd']])
                elif registro['refeicoes_por_dia'] == 8:
                    dados11.append(['Mais de 6 refeições', registro['qtd']])
                else:
                    dados11.append(['Não Informado', registro['qtd']])

            grafico11 = PieChart('grafico11', title='Quantidade de Refeições por Dia', subtitle='Classificação por Quantidade de Refeições por Dia', minPointLength=0, data=dados11)

            setattr(grafico11, 'id', 'grafico11')

            dados12 = list()
            vida_sexual_ativa = registros.values('vida_sexual_ativa').annotate(qtd=Count('vida_sexual_ativa')).order_by('vida_sexual_ativa')

            for registro in vida_sexual_ativa:
                if registro['vida_sexual_ativa']:
                    dados12.append(['Tem vida sexual ativa', registro['qtd']])
                else:
                    dados12.append(['Não tem vida sexual ativa', registro['qtd']])

            grafico12 = PieChart('grafico12', title='Vida Sexual Ativa', subtitle='Classificação por Presença de Vida Sexual Ativa', minPointLength=0, data=dados12)

            setattr(grafico12, 'id', 'grafico12')

            dados13 = list()
            metodo_contraceptivo = (
                registros.filter(vida_sexual_ativa=True).values('metodo_contraceptivo').annotate(qtd=Count('metodo_contraceptivo')).order_by('metodo_contraceptivo')
            )

            for registro in metodo_contraceptivo:
                if registro['metodo_contraceptivo']:
                    dados13.append(['Usa método contraceptivo', registro['qtd']])
                else:
                    dados13.append(['Não usa método contraceptivo', registro['qtd']])

            grafico13 = PieChart('grafico13', title='Uso de Método Contraceptivo', subtitle='Classificação por Uso de Método Contraceptivo', minPointLength=0, data=dados13)

            setattr(grafico13, 'id', 'grafico13')

            dados14 = list()
            qual_metodo_contraceptivo = (
                registros.filter(metodo_contraceptivo=True)
                .values('qual_metodo_contraceptivo__nome')
                .annotate(qtd=Count('qual_metodo_contraceptivo__nome'))
                .order_by('qual_metodo_contraceptivo__nome')
            )

            for registro in qual_metodo_contraceptivo:
                dados14.append([registro['qual_metodo_contraceptivo__nome'], registro['qtd']])

            if dados14 and dados14[-1][1] == 0:
                dados14.pop()

            grafico14 = PieChart('grafico14', title='Tipo de Método Contraceptivo', subtitle='Classificação por Tipo de Método Contraceptivo', minPointLength=0, data=dados14)

            setattr(grafico14, 'id', 'grafico14')

            dados15 = list()
            tempo_uso_internet = registros.values('tempo_uso_internet').annotate(qtd=Count('tempo_uso_internet')).order_by('tempo_uso_internet')

            for registro in tempo_uso_internet:
                if registro['tempo_uso_internet'] == 1:
                    dados15.append(['Menos de 2 horas/dia', registro['qtd']])
                elif registro['tempo_uso_internet'] == 2:
                    dados15.append(['2 a 3 horas/dia', registro['qtd']])
                elif registro['tempo_uso_internet'] == 3:
                    dados15.append(['3 a 4 horas/dia', registro['qtd']])
                elif registro['tempo_uso_internet'] == 4:
                    dados15.append(['4 ou mais horas/dia', registro['qtd']])

            grafico15 = PieChart('grafico15', title='Tempo de Uso da Internet', subtitle='Classificação por Tempo de Uso da Internet', minPointLength=0, data=dados15)

            setattr(grafico15, 'id', 'grafico15')

            dados16 = list()
            objetivo_uso_internet = registros.values('objetivo_uso_internet').annotate(qtd=Count('objetivo_uso_internet')).order_by('objetivo_uso_internet')
            pesquisa = jogos = redes_sociais = trabalho = outros = 0

            for registro in objetivo_uso_internet:
                if 'Pesquisa relacionada a estudo' in registro['objetivo_uso_internet']:
                    pesquisa = pesquisa + 1
                if 'Jogos' in registro['objetivo_uso_internet']:
                    jogos = jogos + 1
                if 'Redes Sociais' in registro['objetivo_uso_internet']:
                    redes_sociais = redes_sociais + 1
                if 'Trabalho' in registro['objetivo_uso_internet']:
                    trabalho = trabalho + 1
                if 'Outros' in registro['objetivo_uso_internet']:
                    outros = outros + 1

            dados16.append(['Pesquisa relacionada a estudo', pesquisa])
            dados16.append(['Jogos', jogos])
            dados16.append(['Redes Sociais', redes_sociais])
            dados16.append(['Trabalho', trabalho])
            dados16.append(['Outros', outros])

            grafico16 = PieChart('grafico16', title='Objetivo de Uso da Internet', subtitle='Classificação por Objetivo de Uso da Internet', minPointLength=0, data=dados16)

            setattr(grafico16, 'id', 'grafico16')

            pie_chart_lists = [
                grafico1,
                grafico2,
                grafico3,
                grafico4,
                grafico5,
                grafico6,
                grafico7,
                grafico8,
                grafico9,
                grafico10,
                grafico11,
                grafico12,
                grafico13,
                grafico14,
                grafico15,
                grafico16,
            ]
    return locals()


@rtr()
@group_required(['Psicólogo'])
def adicionar_motivo_psicologia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Motivo e Queixa Principal - {atendimento.get_vinculo()}'
    obj = AtendimentoPsicologia.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_psicologico/{atendimento.id}/?tab=aba_motivo', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoPsicologia()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoPsicologicoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_psicologico/{atendimento.id}/?tab=aba_motivo', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_desenvolvimento_pessoal(request):
    title = 'Gráficos - Desenvolvimento Pessoal'
    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        registros = DesenvolvimentoPessoal.objects.all()
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))
        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if 'xls' in request.GET:
            return tasks.graficos_desenvolvimento_pessoal_to_xls(registros)
        if registros.exists():
            dados = list()
            problema_aprendizado = registros.values('problema_aprendizado').annotate(qtd=Count('problema_aprendizado')).order_by('problema_aprendizado')

            for registro in problema_aprendizado:
                if registro['problema_aprendizado']:
                    dados.append(['Tem dificuldade de aprendizado', registro['qtd']])
                else:
                    dados.append(['Não tem dificuldade de aprendizado', registro['qtd']])

            grafico1 = PieChart('grafico1', title='Dificuldade de Aprendizado', subtitle='Classificação por Dificuldade de Aprendizado', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            pie_chart_lists = [grafico1]

    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_exame_fisico(request):
    title = 'Gráficos - Exame Físico'

    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        registros = ExameFisico.objects.all()
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))
        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if 'xls' in request.GET:
            return tasks.graficos_exame_fisico_to_xls(registros)
        if registros.exists():
            dados = list()
            ectoscopia_alterada = registros.values('ectoscopia_alterada').annotate(qtd=Count('ectoscopia_alterada')).order_by('ectoscopia_alterada')

            for registro in ectoscopia_alterada:
                if registro['ectoscopia_alterada']:
                    dados.append(['Tem Alteração na Ectoscopia', registro['qtd']])
                else:
                    dados.append(['Não tem Alteração na Ectoscopia', registro['qtd']])

            grafico1 = PieChart('grafico1', title='Ectoscopia', subtitle='Classificação por Alteração na Ectoscopia', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            acv_alterado = registros.values('acv_alterado').annotate(qtd=Count('acv_alterado')).order_by('acv_alterado')

            for registro in acv_alterado:
                if registro['acv_alterado']:
                    dados2.append(['Tem Alteração no Aparelho Cardiovascular', registro['qtd']])
                else:
                    dados2.append(['Não tem Alteração no Aparelho Cardiovascular', registro['qtd']])

            grafico2 = PieChart('grafico2', title='Aparelho Cardiovascular', subtitle='Classificação por Alteração no Aparelho Cardiovascular', minPointLength=0, data=dados2)

            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            ar_alterado = registros.values('ar_alterado').annotate(qtd=Count('ar_alterado')).order_by('ar_alterado')

            for registro in ar_alterado:
                if registro['ar_alterado']:
                    dados3.append(['Tem Alteração no Aparelho Respiratório', registro['qtd']])
                else:
                    dados3.append(['Não tem Alteração no Aparelho Respiratório', registro['qtd']])

            grafico3 = PieChart('grafico3', title='Aparelho Respiratório', subtitle='Classificação por Alteração no Aparelho Respiratório', minPointLength=0, data=dados3)

            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            abdome_alterado = registros.values('abdome_alterado').annotate(qtd=Count('abdome_alterado')).order_by('abdome_alterado')

            for registro in abdome_alterado:
                if registro['abdome_alterado']:
                    dados4.append(['Tem Alteração Abdominal', registro['qtd']])
                else:
                    dados4.append(['Não tem Alteração Abdominal', registro['qtd']])

            grafico4 = PieChart('grafico4', title='Alteração Abdominal', subtitle='Classificação por Alteração Abdominal', minPointLength=0, data=dados4)

            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            mmi_alterados = registros.values('mmi_alterados').annotate(qtd=Count('mmi_alterados')).order_by('mmi_alterados')

            for registro in mmi_alterados:
                if registro['mmi_alterados']:
                    dados5.append(['Tem Alteração nos Membros Inferiores', registro['qtd']])
                else:
                    dados5.append(['Não tem Alteração nos Membros Inferiores', registro['qtd']])

            grafico5 = PieChart('grafico5', title='Alteração nos Membros Inferiores', subtitle='Classificação por Alteração nos Membros Inferiores', minPointLength=0, data=dados5)

            setattr(grafico5, 'id', 'grafico5')

            dados6 = list()
            mms_alterados = registros.values('mms_alterados').annotate(qtd=Count('mms_alterados')).order_by('mms_alterados')

            for registro in mms_alterados:
                if registro['mms_alterados']:
                    dados6.append(['Tem Alteração nos Membros Superiores', registro['qtd']])
                else:
                    dados6.append(['Não tem Alteração nos Membros Superiores', registro['qtd']])

            grafico6 = PieChart('grafico6', title='Alteração nos Membros Superiores', subtitle='Classificação por Alteração nos Membros Superiores', minPointLength=0, data=dados6)

            setattr(grafico6, 'id', 'grafico6')

            pie_chart_lists = [grafico1, grafico2, grafico3, grafico4, grafico5, grafico6]
    return locals()


@rtr()
@group_required(['Odontólogo'])
def alterar_tipo_consulta(request, atendimento_id):
    title = 'Alterar Tipo de Consulta'
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    odontograma = get_object_or_404(Odontograma, atendimento=atendimento)
    form = TipoConsultaForm(request.POST or None, instance=odontograma)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_procedimento', 'Tipo de consulta alterado com sucesso.')

    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_percepcao_saude_bucal(request):
    title = 'Gráficos - Percepção de Saúde Bucal'

    registros = PercepcaoSaudeBucal.objects.all()
    form = EstatisticasAtendimentosForm(request.GET or None, request=request)
    if form.is_valid():
        if form.cleaned_data.get('data_inicio') and form.cleaned_data.get('data_termino'):
            registros = registros.filter(data_cadastro__gte=form.cleaned_data['data_inicio'], data_cadastro__lte=form.cleaned_data['data_termino'])
        if form.cleaned_data.get('uo'):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=form.cleaned_data.get('uo'))
        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            registros = registros.filter(atendimento__usuario_aberto__vinculo__setor__uo=get_uo(request.user))

        if 'xls' in request.GET:
            return tasks.graficos_percepcao_saude_bucal_to_xls(registros)
        if registros.exists():
            dados = list()
            foi_dentista_anteriormente = registros.values('foi_dentista_anteriormente').annotate(qtd=Count('foi_dentista_anteriormente')).order_by('foi_dentista_anteriormente')
            if nao_possui_dados_estatisticos(foi_dentista_anteriormente):
                dados.append(['Não Informado', registros.count()])
            else:
                for registro in foi_dentista_anteriormente:
                    if registro['foi_dentista_anteriormente']:
                        dados.append(['Foi ao Dentista Anteriormente', registro['qtd']])
                    else:
                        dados.append(['Não foi ao Dentista Anteriormente', registro['qtd']])

            grafico1 = BarChart('grafico1', title='Ida Anterior ao Dentista', subtitle='Classificação por Ida Anterior ao Dentista', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            tempo_ultima_vez_dentista = registros.values('tempo_ultima_vez_dentista').annotate(qtd=Count('tempo_ultima_vez_dentista')).order_by('tempo_ultima_vez_dentista')

            if nao_possui_dados_estatisticos(tempo_ultima_vez_dentista):
                dados2.append(['Não Informado', registros.count()])
            else:
                for registro in tempo_ultima_vez_dentista:
                    if registro['tempo_ultima_vez_dentista'] == 1:
                        dados2.append(['Menos de 1 mês', registro['qtd']])
                    elif registro['tempo_ultima_vez_dentista'] == 2:
                        dados2.append(['Entre 1 e 6 meses', registro['qtd']])
                    elif registro['tempo_ultima_vez_dentista'] == 3:
                        dados2.append(['Entre 6 e 12 meses', registro['qtd']])
                    elif registro['tempo_ultima_vez_dentista'] == 4:
                        dados2.append(['Entre 1 a 2 anos', registro['qtd']])
                    elif registro['tempo_ultima_vez_dentista'] == 5:
                        dados2.append(['Mais de 2 anos', registro['qtd']])

            grafico2 = BarChart('grafico2', title='Última Ida ao Dentista', subtitle='Classificação por Última Ida ao Dentista', minPointLength=0, data=dados2)

            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            qtd_vezes_fio_dental_ultima_semana = (
                registros.filter(qtd_vezes_fio_dental_ultima_semana__gte=0)
                .values('qtd_vezes_fio_dental_ultima_semana')
                .annotate(qtd=Count('qtd_vezes_fio_dental_ultima_semana'))
                .order_by('qtd_vezes_fio_dental_ultima_semana')
            )
            total_uso_fiodental_nenhuma_vez = 0
            total_uso_fiodental_uma_ou_mais_vezes = 0
            if nao_possui_dados_estatisticos(qtd_vezes_fio_dental_ultima_semana):
                dados3.append(['Não Informado', registros.count()])
            else:
                for registro in qtd_vezes_fio_dental_ultima_semana:
                    if registro['qtd_vezes_fio_dental_ultima_semana'] == 0:
                        quantidade = "Nenhuma vez"
                        total_uso_fiodental_nenhuma_vez += registro['qtd']
                    elif registro['qtd_vezes_fio_dental_ultima_semana'] == 1:
                        quantidade = "{} vez".format(registro['qtd_vezes_fio_dental_ultima_semana'])
                        total_uso_fiodental_uma_ou_mais_vezes += registro['qtd']
                    else:
                        quantidade = "{} vezes".format(registro['qtd_vezes_fio_dental_ultima_semana'])
                        total_uso_fiodental_uma_ou_mais_vezes += registro['qtd']
                    dados3.append([quantidade, registro['qtd']])

            grafico3 = BarChart(
                'grafico3', title='Uso do Fio Dental na Última Semana', subtitle='Classificação por Uso do Fio Dental na Última Semana', minPointLength=0, data=dados3
            )

            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            qtd_dias_consumiu_doce_ultima_semana = (
                registros.filter(qtd_dias_consumiu_doce_ultima_semana__gte=0)
                .values('qtd_dias_consumiu_doce_ultima_semana')
                .annotate(qtd=Count('qtd_dias_consumiu_doce_ultima_semana'))
                .order_by('qtd_dias_consumiu_doce_ultima_semana')
            )
            if nao_possui_dados_estatisticos(qtd_dias_consumiu_doce_ultima_semana):
                dados4.append(['Não Informado', registros.count()])
            else:
                for registro in qtd_dias_consumiu_doce_ultima_semana:
                    if registro['qtd_dias_consumiu_doce_ultima_semana'] == 0:
                        quantidade = "Nenhuma vez"
                    elif registro['qtd_dias_consumiu_doce_ultima_semana'] == 1:
                        quantidade = "{} vez".format(registro['qtd_dias_consumiu_doce_ultima_semana'])
                    else:
                        quantidade = "{} vezes".format(registro['qtd_dias_consumiu_doce_ultima_semana'])
                    dados4.append([quantidade, registro['qtd']])

            grafico4 = BarChart(
                'grafico4',
                title='Consumo de Doces, Balas e Refrigerantes na Última Semana',
                subtitle='Classificação por Consumo de Doces, Balas e Refrigerantes na Última Semana',
                minPointLength=0,
                data=dados4,
            )

            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            dificuldades = registros.values('dificuldades').annotate(qtd=Count('dificuldades')).order_by('dificuldades')

            if nao_possui_dados_estatisticos(dificuldades):
                dados5.append(['Não Informado', registros.count()])
            else:
                for registro in dificuldades:
                    if registro['dificuldades']:
                        dados5.append(['Tem Dificuldade', registro['qtd']])
                    else:
                        dados5.append(['Não Tem Dificuldade', registro['qtd']])

            grafico5 = BarChart('grafico5', title='Dificuldade Relacionada à Boca', subtitle='Classificação por Dificuldade Relacionada à Boca', minPointLength=0, data=dados5)

            setattr(grafico5, 'id', 'grafico5')

            dados6 = list()
            grau_dificuldade_sorrir = registros.values('grau_dificuldade_sorrir').annotate(qtd=Count('grau_dificuldade_sorrir')).order_by('grau_dificuldade_sorrir')

            total_dificuldade_sorrir = grau_dificuldade_sorrir.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_sorrir):
                dados6.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_sorrir:
                    if registro['grau_dificuldade_sorrir'] == 1:
                        dados6.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_sorrir'] == 2:
                        dados6.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_sorrir'] == 3:
                        dados6.append(['Baixo', registro['qtd']])

            grafico6 = BarChart('grafico6', title='Grau de Dificuldade para Sorrir', subtitle='Classificação por Grau de Dificuldade para Sorrir', minPointLength=0, data=dados6)

            setattr(grafico6, 'id', 'grafico6')

            dados7 = list()
            motivo_dificuldade_sorrir = (
                registros.filter(motivo_dificuldade_sorrir__isnull=False)
                .values('motivo_dificuldade_sorrir__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_sorrir__dificuldade'))
                .order_by('motivo_dificuldade_sorrir__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_sorrir):
                dados7.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_sorrir:
                    dados7.append([registro['motivo_dificuldade_sorrir__dificuldade'], registro['qtd']])

            grafico7 = BarChart(
                'grafico7', title='Motivo de Dificuldade para Sorrir', subtitle='Classificação por Motivo de Dificuldade para Sorrir', minPointLength=0, data=dados7
            )

            setattr(grafico7, 'id', 'grafico7')

            dados8 = list()
            grau_dificuldade_falar = registros.values('grau_dificuldade_falar').annotate(qtd=Count('grau_dificuldade_falar')).order_by('grau_dificuldade_falar')

            total_dificuldade_falar = grau_dificuldade_falar.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_falar):
                dados8.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_falar:
                    if registro['grau_dificuldade_falar'] == 1:
                        dados8.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_falar'] == 2:
                        dados8.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_falar'] == 3:
                        dados8.append(['Baixo', registro['qtd']])

            grafico8 = BarChart('grafico8', title='Grau de Dificuldade para Falar', subtitle='Classificação por Grau de Dificuldade para Falar', minPointLength=0, data=dados8)

            setattr(grafico8, 'id', 'grafico8')

            dados9 = list()
            motivo_dificuldade_falar = (
                registros.filter(motivo_dificuldade_falar__isnull=False)
                .values('motivo_dificuldade_falar__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_falar__dificuldade'))
                .order_by('motivo_dificuldade_falar__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_falar):
                dados9.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_falar:
                    dados9.append([registro['motivo_dificuldade_falar__dificuldade'], registro['qtd']])

            grafico9 = BarChart('grafico9', title='Motivo de Dificuldade para Falar', subtitle='Classificação por Motivo de Dificuldade para Falar', minPointLength=0, data=dados9)

            setattr(grafico9, 'id', 'grafico9')

            dados10 = list()
            grau_dificuldade_comer = registros.values('grau_dificuldade_comer').annotate(qtd=Count('grau_dificuldade_comer')).order_by('grau_dificuldade_comer')
            total_dificuldade_comer = grau_dificuldade_comer.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_comer):
                dados10.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_comer:
                    if registro['grau_dificuldade_comer'] == 1:
                        dados10.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_comer'] == 2:
                        dados10.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_comer'] == 3:
                        dados10.append(['Baixo', registro['qtd']])

            grafico10 = BarChart('grafico10', title='Grau de Dificuldade para Comer', subtitle='Classificação por Grau de Dificuldade para Comer', minPointLength=0, data=dados10)

            setattr(grafico10, 'id', 'grafico10')

            dados11 = list()
            motivo_dificuldade_comer = (
                registros.filter(motivo_dificuldade_comer__isnull=False)
                .values('motivo_dificuldade_comer__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_comer__dificuldade'))
                .order_by('motivo_dificuldade_comer__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_comer):
                dados11.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_comer:
                    dados11.append([registro['motivo_dificuldade_comer__dificuldade'], registro['qtd']])

            grafico11 = BarChart(
                'grafico11', title='Motivo de Dificuldade para Comer', subtitle='Classificação por Motivo de Dificuldade para Comer', minPointLength=0, data=dados11
            )

            setattr(grafico11, 'id', 'grafico11')

            dados12 = list()
            grau_dificuldade_relacionar = registros.values('grau_dificuldade_relacionar').annotate(qtd=Count('grau_dificuldade_relacionar')).order_by('grau_dificuldade_relacionar')
            total_dificuldade_relacionar = grau_dificuldade_relacionar.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_relacionar):
                dados12.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_relacionar:
                    if registro['grau_dificuldade_relacionar'] == 1:
                        dados12.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_relacionar'] == 2:
                        dados12.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_relacionar'] == 3:
                        dados12.append(['Baixo', registro['qtd']])

            grafico12 = BarChart(
                'grafico12', title='Grau de Dificuldade para se Relacionar', subtitle='Classificação por Grau de Dificuldade para se Relacionar', minPointLength=0, data=dados12
            )

            setattr(grafico12, 'id', 'grafico12')

            dados13 = list()
            motivo_dificuldade_relacionar = (
                registros.filter(motivo_dificuldade_relacionar__isnull=False)
                .values('motivo_dificuldade_relacionar__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_relacionar__dificuldade'))
                .order_by('motivo_dificuldade_relacionar__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_relacionar):
                dados13.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_relacionar:
                    dados13.append([registro['motivo_dificuldade_relacionar__dificuldade'], registro['qtd']])

            grafico13 = BarChart(
                'grafico13', title='Motivo de Dificuldade para se Relacionar', subtitle='Classificação por Motivo de Dificuldade para se Relacionar', minPointLength=0, data=dados13
            )

            setattr(grafico13, 'id', 'grafico13')

            dados14 = list()
            grau_dificuldade_manter_humor = (
                registros.values('grau_dificuldade_manter_humor').annotate(qtd=Count('grau_dificuldade_manter_humor')).order_by('grau_dificuldade_manter_humor')
            )
            total_dificuldade_manter_humor = grau_dificuldade_manter_humor.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_manter_humor):
                dados14.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_manter_humor:
                    if registro['grau_dificuldade_manter_humor'] == 1:
                        dados14.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_manter_humor'] == 2:
                        dados14.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_manter_humor'] == 3:
                        dados14.append(['Baixo', registro['qtd']])

            grafico14 = BarChart(
                'grafico14', title='Grau de Dificuldade para Manter o Humor', subtitle='Classificação por Grau de Dificuldade para Manter o Humor', minPointLength=0, data=dados14
            )

            setattr(grafico14, 'id', 'grafico14')

            dados15 = list()
            motivo_dificuldade_manter_humor = (
                registros.filter(motivo_dificuldade_manter_humor__isnull=False)
                .values('motivo_dificuldade_manter_humor__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_manter_humor__dificuldade'))
                .order_by('motivo_dificuldade_manter_humor__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_manter_humor):
                dados15.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_manter_humor:
                    dados15.append([registro['motivo_dificuldade_manter_humor__dificuldade'], registro['qtd']])

            grafico15 = BarChart(
                'grafico15',
                title='Motivo de Dificuldade para Manter o Humor',
                subtitle='Classificação por Motivo de Dificuldade para Manter o Humor',
                minPointLength=0,
                data=dados15,
            )

            setattr(grafico15, 'id', 'grafico15')

            dados16 = list()
            grau_dificuldade_estudar = registros.values('grau_dificuldade_estudar').annotate(qtd=Count('grau_dificuldade_estudar')).order_by('grau_dificuldade_estudar')
            total_dificuldade_estudar = grau_dificuldade_estudar.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_estudar):
                dados16.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_estudar:
                    if registro['grau_dificuldade_estudar'] == 1:
                        dados16.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_estudar'] == 2:
                        dados16.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_estudar'] == 3:
                        dados16.append(['Baixo', registro['qtd']])

            grafico16 = BarChart(
                'grafico16', title='Grau de Dificuldade para Estudar', subtitle='Classificação por Grau de Dificuldade para Estudar', minPointLength=0, data=dados16
            )

            setattr(grafico16, 'id', 'grafico16')

            dados17 = list()
            motivo_dificuldade_estudar = (
                registros.filter(motivo_dificuldade_estudar__isnull=False)
                .values('motivo_dificuldade_estudar__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_estudar__dificuldade'))
                .order_by('motivo_dificuldade_estudar__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_estudar):
                dados17.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_estudar:
                    dados17.append([registro['motivo_dificuldade_estudar__dificuldade'], registro['qtd']])

            grafico17 = BarChart(
                'grafico17', title='Motivo de Dificuldade para Estudar', subtitle='Classificação por Motivo de Dificuldade para Estudar', minPointLength=0, data=dados17
            )

            setattr(grafico17, 'id', 'grafico17')

            dados18 = list()
            grau_dificuldade_trabalhar = registros.values('grau_dificuldade_trabalhar').annotate(qtd=Count('grau_dificuldade_trabalhar')).order_by('grau_dificuldade_trabalhar')
            total_dificuldade_trabalhar = grau_dificuldade_trabalhar.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_trabalhar):
                dados18.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_trabalhar:
                    if registro['grau_dificuldade_trabalhar'] == 1:
                        dados18.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_trabalhar'] == 2:
                        dados18.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_trabalhar'] == 3:
                        dados18.append(['Baixo', registro['qtd']])

            grafico18 = BarChart(
                'grafico18', title='Grau de Dificuldade em Trabalhar', subtitle='Classificação por Grau de Dificuldade em Trabalhar', minPointLength=0, data=dados18
            )

            setattr(grafico18, 'id', 'grafico18')

            dados19 = list()
            motivo_dificuldade_trabalhar = (
                registros.filter(motivo_dificuldade_trabalhar__isnull=False)
                .values('motivo_dificuldade_trabalhar__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_trabalhar__dificuldade'))
                .order_by('motivo_dificuldade_trabalhar__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_trabalhar):
                dados19.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_trabalhar:
                    dados19.append([registro['motivo_dificuldade_trabalhar__dificuldade'], registro['qtd']])

            grafico19 = BarChart(
                'grafico19', title='Motivo de Dificuldade para Trabalhar', subtitle='Classificação por Motivo de Dificuldade para Trabalhar', minPointLength=0, data=dados19
            )

            setattr(grafico19, 'id', 'grafico19')

            dados20 = list()
            grau_dificuldade_higienizar = registros.values('grau_dificuldade_higienizar').annotate(qtd=Count('grau_dificuldade_higienizar')).order_by('grau_dificuldade_higienizar')
            total_dificuldade_higienizar = grau_dificuldade_higienizar.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_higienizar):
                dados20.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_higienizar:
                    if registro['grau_dificuldade_higienizar'] == 1:
                        dados20.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_higienizar'] == 2:
                        dados20.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_higienizar'] == 3:
                        dados20.append(['Baixo', registro['qtd']])

            grafico20 = BarChart(
                'grafico20', title='Grau de Dificuldade em Higienizar a Boca', subtitle='Classificação por Grau de Dificuldade em Higienizar a Boca', minPointLength=0, data=dados20
            )

            setattr(grafico20, 'id', 'grafico20')

            dados21 = list()
            motivo_dificuldade_higienizar = (
                registros.filter(motivo_dificuldade_higienizar__isnull=False)
                .values('motivo_dificuldade_higienizar__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_higienizar__dificuldade'))
                .order_by('motivo_dificuldade_higienizar__dificuldade')
            )

            if nao_possui_dados_estatisticos(motivo_dificuldade_higienizar):
                dados21.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_higienizar:
                    dados21.append([registro['motivo_dificuldade_higienizar__dificuldade'], registro['qtd']])

            grafico21 = BarChart(
                'grafico21',
                title='Motivo de Dificuldade para Higienizar a Boca',
                subtitle='Classificação por Motivo de Dificuldade para Higienizar a Boca',
                minPointLength=0,
                data=dados21,
            )

            setattr(grafico21, 'id', 'grafico21')

            dados22 = list()
            grau_dificuldade_dormir = registros.values('grau_dificuldade_dormir').annotate(qtd=Count('grau_dificuldade_dormir')).order_by('grau_dificuldade_dormir')
            total_dificuldade_dormir = grau_dificuldade_dormir.aggregate(total=Sum('qtd'))

            if nao_possui_dados_estatisticos(grau_dificuldade_dormir):
                dados22.append(['Não Informado', registros.count()])
            else:
                for registro in grau_dificuldade_dormir:
                    if registro['grau_dificuldade_dormir'] == 1:
                        dados22.append(['Alto', registro['qtd']])
                    elif registro['grau_dificuldade_dormir'] == 2:
                        dados22.append(['Médio', registro['qtd']])
                    elif registro['grau_dificuldade_dormir'] == 3:
                        dados22.append(['Baixo', registro['qtd']])

            grafico22 = BarChart('grafico22', title='Grau de Dificuldade para Dormir', subtitle='Classificação por Grau de Dificuldade para Dormir', minPointLength=0, data=dados22)

            setattr(grafico22, 'id', 'grafico22')

            dados23 = list()
            motivo_dificuldade_dormir = (
                registros.filter(motivo_dificuldade_dormir__isnull=False)
                .values('motivo_dificuldade_dormir__dificuldade')
                .annotate(qtd=Count('motivo_dificuldade_dormir__dificuldade'))
                .order_by('motivo_dificuldade_dormir__dificuldade')
            )
            if nao_possui_dados_estatisticos(motivo_dificuldade_dormir):
                dados23.append(['Não Informado', registros.count()])
            else:
                for registro in motivo_dificuldade_dormir:
                    dados23.append([registro['motivo_dificuldade_dormir__dificuldade'], registro['qtd']])

            grafico23 = BarChart(
                'grafico23', title='Motivo de Dificuldade para Dormir', subtitle='Classificação por Motivo de Dificuldade para Dormir', minPointLength=0, data=dados23
            )

            setattr(grafico23, 'id', 'grafico23')

            dados24 = list()
            dados24.append(['Dificuldade em Sorrir', total_dificuldade_sorrir['total']])
            dados24.append(['Dificuldade em Falar', total_dificuldade_falar['total']])
            dados24.append(['Dificuldade em Comer', total_dificuldade_comer['total']])
            dados24.append(['Dificuldade em se Relacionar', total_dificuldade_relacionar['total']])
            dados24.append(['Dificuldade em Manter o Humor', total_dificuldade_manter_humor['total']])
            dados24.append(['Dificuldade em Estudar', total_dificuldade_estudar['total']])
            dados24.append(['Dificuldade em Trabalhar', total_dificuldade_trabalhar['total']])
            dados24.append(['Dificuldade em Higienizar a Boca', total_dificuldade_higienizar['total']])
            dados24.append(['Dificuldade em Dormir', total_dificuldade_dormir['total']])

            grafico24 = BarChart('grafico24', title='Quantitativos Totais - Dificuldades', subtitle='Valor total para cada dificuldade', minPointLength=0, data=dados24)

            setattr(grafico24, 'id', 'grafico24')

            dados25 = list()
            dados25.append(['Nenhuma Vez', total_uso_fiodental_nenhuma_vez])
            dados25.append(['Uma ou Mais Vezes', total_uso_fiodental_uma_ou_mais_vezes])

            grafico25 = PieChart('grafico25', title='Uso do Fio Dentral', subtitle='Classificação por quem nunca usou e quem usou na ultima semana', minPointLength=0, data=dados25)

            setattr(grafico25, 'id', 'grafico25')

            dados26 = list()
            for dificuldade in DificuldadeOral.objects.all():
                valor = (
                    registros.filter(motivo_dificuldade_comer=dificuldade).count()
                    + registros.filter(motivo_dificuldade_falar=dificuldade).count()
                    + registros.filter(motivo_dificuldade_estudar=dificuldade).count()
                    + registros.filter(motivo_dificuldade_trabalhar=dificuldade).count()
                    + registros.filter(motivo_dificuldade_dormir=dificuldade).count()
                    + registros.filter(motivo_dificuldade_relacionar=dificuldade).count()
                    + registros.filter(motivo_dificuldade_manter_humor=dificuldade).count()
                    + registros.filter(motivo_dificuldade_sorrir=dificuldade).count()
                    + registros.filter(motivo_dificuldade_higienizar=dificuldade).count()
                )

                if valor:
                    dados26.append([dificuldade.dificuldade, valor])

            grafico26 = BarChart(
                'grafico26', title='Quantitativos Totais - Motivos da Dificuldade', subtitle='Valor total para cada motivo de dificulddade', minPointLength=0, data=dados26
            )

            setattr(grafico26, 'id', 'grafico26')

            pie_chart_lists = [
                grafico1,
                grafico2,
                grafico25,
                grafico3,
                grafico4,
                grafico5,
                grafico24,
                grafico26,
                grafico6,
                grafico7,
                grafico8,
                grafico9,
                grafico10,
                grafico11,
                grafico12,
                grafico13,
                grafico14,
                grafico15,
                grafico16,
                grafico17,
                grafico18,
                grafico19,
                grafico20,
                grafico21,
                grafico22,
                grafico23,
            ]

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Auditor'])
def envia_mensagem_vacina_atrasada(request, registros):
    title = 'Enviar Mensagem - Vacinas Atrasadas'
    form = MensagemVacinaAtrasadaForm(request.POST or None)
    if form.is_valid():
        titulo = '[SUAP] {}'.format(form.cleaned_data.get('titulo'))
        mensagem = form.cleaned_data.get('mensagem')
        texto = '<h1>Saúde</h1>' '<h2>Notificação de Vacina Atrasada</h2>' '{}</p>'.format(mensagem)

        for item in registros:
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [item.prontuario.vinculo], categoria='Saúde: Vacina Atrasada')

        return httprr('/saude/graficos_vacinas/', 'Mensagem enviada com sucesso.')
    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def graficos_vacinas(request):
    title = 'Relatório de Vacinas dos Alunos'
    form = TipoVacinaForm(request.GET or None, request=request)
    if form.is_valid():
        hoje = datetime.datetime.today().date()
        registros = CartaoVacinal.objects.filter(prontuario__vinculo__user__eh_aluno=True)
        vacinas_atrasadas = registros.filter(data_vacinacao__isnull=True)
        alunos_com_cartoes = Aluno.objects.filter(situacao=SituacaoMatricula.MATRICULADO, vinculos__vinculo_paciente_prontuario__cartaovacinal__isnull=False)

        if form.cleaned_data.get('vacina'):
            alunos_com_cartoes = alunos_com_cartoes.filter(vinculos__vinculo_paciente_prontuario__cartaovacinal__vacina=form.cleaned_data.get('vacina'))
            vacinas_atrasadas = vacinas_atrasadas.filter(vacina=form.cleaned_data.get('vacina'))

        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            alunos_com_cartoes = alunos_com_cartoes.filter(curso_campus__diretoria__setor__uo=get_uo(request.user))

        if form.cleaned_data.get('turma'):
            alunos_turma = form.cleaned_data.get('turma').get_alunos_matriculados()
            alunos_com_cartoes = alunos_com_cartoes.filter(id__in=alunos_turma.values_list('aluno', flat=True))

        if form.cleaned_data.get('campus'):
            alunos_com_cartoes = alunos_com_cartoes.filter(situacao=SituacaoMatricula.MATRICULADO, curso_campus__diretoria__setor__uo=form.cleaned_data.get('campus'))

        buscou_data = False
        if form.cleaned_data.get('data_inicial'):
            vacinas_atrasadas = vacinas_atrasadas.filter(data_prevista__gte=form.cleaned_data.get('data_inicial'))
            buscou_data = True
        if form.cleaned_data.get('data_final'):
            vacinas_atrasadas = vacinas_atrasadas.filter(data_prevista__lte=form.cleaned_data.get('data_final'))
            buscou_data = True
        if not buscou_data:
            vacinas_atrasadas = vacinas_atrasadas.filter(data_prevista__lt=hoje)

        alunos_com_cartoes = alunos_com_cartoes.order_by('pessoa_fisica__nome').distinct()
        registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos_com_cartoes.values_list('pessoa_fisica', flat=True))
        vacinas_atrasadas = vacinas_atrasadas.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos_com_cartoes.values_list('pessoa_fisica', flat=True))

        dados = list()
        vacinas = registros.values('vacina__nome').annotate(qtd=Count('vacina__nome')).order_by('vacina__nome')

        vacinas_atrasadas = vacinas_atrasadas.order_by('prontuario__vinculo__pessoa__nome').distinct()

        for registro in vacinas:
            dados.append([registro['vacina__nome'], registro['qtd']])

        grafico1 = PieChart('grafico1', title='Classificação por Vacinas - Alunos', subtitle='Classificação por Vacinas Registradas para Alunos', minPointLength=0, data=dados)
        setattr(grafico1, 'id', 'grafico1')

        pie_chart_lists = [grafico1]

        if request.GET.get('envia_mensagem'):
            return envia_mensagem_vacina_atrasada(request, vacinas_atrasadas)

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def adicionar_exame_laboratorial(request, prontuario_id):
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)
    title = 'Adicionar Exame Laboratorial'
    tipos_exame = TipoExameLaboratorial.objects.filter(ativo=True)
    exame_anterior = None
    url = request.META.get('HTTP_REFERER', '.')
    if 'exame_anterior_id' in request.GET:
        exame_anterior = get_object_or_404(ExameLaboratorial, pk=request.GET.get('exame_anterior_id'))
    form = ExameLaboratorialForm(request.POST or None, exame_anterior=exame_anterior, url=url)
    if form.is_valid():
        o = form.save(False)
        o.prontuario = prontuario
        o.data_cadastro = datetime.datetime.now()
        o.profissional = request.user.get_relacionamento()
        o.save()
        url_origem = form.cleaned_data.get('url_origem')

        if TipoExameLaboratorial.objects.filter(categoria=o.categoria).exists():
            return httprr(f'/saude/adicionar_valores_exame_laboratorial/{form.instance.id}/?url={url_origem}', 'Exame registrado com sucesso. Preencha os valores do exame.')

        else:
            return httprr(f'{url_origem}', 'Exame registrado com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def adicionar_valores_exame_laboratorial(request, exame_laboratorial_id):
    exame = get_object_or_404(ExameLaboratorial, pk=exame_laboratorial_id)
    title = 'Adicionar Valores do Exame Laboratorial'
    url = request.GET.get('url')
    form = ValoresExameLaboratorialForm(request.POST or None, exame=exame, url=url)

    if form.is_valid():
        url_origem = form.cleaned_data.get('url_origem')
        ids_valores = TipoExameLaboratorial.objects.values_list('id', flat=True)
        for item in list(request.POST.items()):
            try:
                int(item[0])
                if item[1] and int(item[0]) in ids_valores:
                    novo_exame = ValorExameLaboratorial()
                    novo_exame.exame = exame
                    novo_exame.tipo = get_object_or_404(TipoExameLaboratorial, pk=item[0])
                    novo_exame.valor = item[1]
                    novo_exame.save()
            except ValueError:
                pass
        if url_origem and 'atendimento_nutricional' in url_origem:
            return httprr(f'{url_origem}', 'Exame registrado com sucesso.')
        return httprr(f'/saude/adicionar_exame_laboratorial/{exame.prontuario_id}/?exame_anterior_id={exame.id}', 'Exame registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def adicionar_exame_imagem(request, prontuario_id):
    prontuario = get_object_or_404(Prontuario, pk=prontuario_id)
    title = 'Adicionar Exame de Imagem'
    form = ExameImagemForm(request.POST or None)
    if form.is_valid():
        o = form.save(False)
        o.prontuario = prontuario
        o.data_cadastro = datetime.datetime.now()
        o.profissional = request.user.get_relacionamento()
        o.save()
        return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_exames_imagem', 'Exame registrado com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Coordenador de Saúde Sistêmico'])
def ver_exame_laboratorial(request, exame_id):
    exame = get_object_or_404(ExameLaboratorial, pk=exame_id)
    title = 'Exame Laboratorial'
    if exame.sigiloso and not exame.profissional == request.user.get_relacionamento():
        raise PermissionDenied()
    valores = ValorExameLaboratorial.objects.filter(exame=exame)

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Coordenador de Saúde Sistêmico'])
def ver_exame_imagem(request, exame_id):
    exame = get_object_or_404(ExameImagem, pk=exame_id)
    title = 'Exame de Imagem'
    if exame.sigiloso and not exame.profissional == request.user.get_relacionamento():
        raise PermissionDenied()

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista'])
def exame_laboratorial_valores_referencia(request):
    title = "Valores de Referência dos Exames Laboratoriais"
    exames = TipoExameLaboratorial.objects.filter(ativo=True)

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Coordenador de Saúde Sistêmico'])
def editar_exame_laboratorial(request, exame_id):
    exame = get_object_or_404(ExameLaboratorial, pk=exame_id)
    title = 'Editar Exame Laboratorial'
    if not exame.profissional == request.user.get_relacionamento():
        raise PermissionDenied()
    valores = ValorExameLaboratorial.objects.filter(exame=exame)

    form = EditarExameLaboratorialForm(request.POST or None, instance=exame, valores=valores)
    if form.is_valid():
        form.save()
        for item in valores:
            id_registro = item.id
            valor = request.POST.get(str(id_registro))
            registro = get_object_or_404(ValorExameLaboratorial, pk=id_registro)
            if valor:
                registro.valor = valor
                registro.save()
            else:
                registro.delete()

        return httprr(f'/saude/prontuario/{exame.prontuario.vinculo_id}/?tab=aba_exames_laboratoriais', 'Exame alterado com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Coordenador de Saúde Sistêmico'])
def editar_exame_imagem(request, exame_id):
    exame = get_object_or_404(ExameImagem, pk=exame_id)
    title = 'Editar Exame de Imagem'
    if not exame.profissional == request.user.get_relacionamento():
        raise PermissionDenied()
    form = ExameImagemForm(request.POST or None, instance=exame)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/prontuario/{exame.prontuario.vinculo_id}/?tab=aba_exames_imagem', 'Exame alterado com sucesso.')

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Coordenador de Saúde Sistêmico'])
def excluir_exame_laboratorial(request, exame_id):
    exame = get_object_or_404(ExameLaboratorial, pk=exame_id)
    prontuario = exame.prontuario
    if not exame.profissional == request.user.get_relacionamento():
        raise PermissionDenied()
    exame.delete()
    return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_exames_laboratoriais', 'Exame alterado com sucesso.')


@rtr()
@group_required(['Médico', 'Odontólogo', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Fisioterapeuta', 'Nutricionista', 'Coordenador de Saúde Sistêmico'])
def excluir_exame_imagem(request, exame_id):
    exame = get_object_or_404(ExameImagem, pk=exame_id)
    prontuario = exame.prontuario
    if not exame.profissional == request.user.get_relacionamento():
        raise PermissionDenied()
    exame.delete()
    return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_exames_imagem', 'Exame alterado com sucesso.')


@rtr()
@group_required(['Médico'])
def editar_hipotese_diagnostica(request, hipotese_diagnostica_id):
    title = 'Editar Hipótese Diagnóstica'
    hipotese = get_object_or_404(HipoteseDiagnostica, pk=hipotese_diagnostica_id)
    if hipotese.atendimento.is_aberto() and hipotese.profissional == request.user:
        form = HipoteseDiagnosticaModelForm(request.POST or None, instance=hipotese)
        if form.is_valid():
            form.save()
            return httprr(f'/saude/atendimento_medico_enfermagem/{hipotese.atendimento_id}/?tab=aba_hipotesediagnostica', 'Hipótese Diagnóstica alterada com sucesso.')

    else:
        raise PermissionDenied()

    return locals()


@rtr()
@group_required(['Médico'])
def editar_conduta_medica(request, conduta_medica_id):
    title = 'Editar Conduta Médica'
    conduta = get_object_or_404(CondutaMedica, pk=conduta_medica_id)
    if conduta.atendimento.is_aberto() and conduta.profissional == request.user:
        form = CondutaMedicaForm(request.POST or None, instance=conduta, request=request)
        if form.is_valid():
            form.save()
            return httprr(f'/saude/atendimento_medico_enfermagem/{conduta.atendimento_id}/?tab=aba_hipotesediagnostica', 'Conduta Médica alterada com sucesso.')

    else:
        raise PermissionDenied()

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Auditor', 'Coordenador de Atividades Estudantis', 'Coordenador de Atividades Estudantis Sistêmico'])
def relatorio_cartoes_vacinais(request):
    title = 'Relatórios de Cartões Vacinais'

    registros = CartaoVacinal.objects.all()
    if not request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
        alunos_do_campus = Aluno.objects.filter(situacao=SituacaoMatricula.MATRICULADO, curso_campus__diretoria__setor__uo=get_uo(request.user))
        registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos_do_campus.values_list('pessoa_fisica', flat=True))
    pode_ver_prontuario = request.user.groups.filter(name__in=Especialidades.GRUPOS)
    form = CartaoVacinalForm(request.GET or None, request=request)
    if form.is_valid():

        if form.cleaned_data.get('ano_ingresso'):
            alunos = Aluno.objects.filter(situacao=SituacaoMatricula.MATRICULADO, ano_letivo=form.cleaned_data.get('ano_ingresso'))
            registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos.values_list('pessoa_fisica', flat=True))
        if form.cleaned_data.get('modalidade'):
            alunos = Aluno.objects.filter(situacao=SituacaoMatricula.MATRICULADO, curso_campus__modalidade=form.cleaned_data.get('modalidade'))
            registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos.values_list('pessoa_fisica', flat=True))
        if form.cleaned_data.get('turma'):
            alunos = form.cleaned_data.get('turma').get_alunos_matriculados()
            registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos.values_list('aluno__pessoa_fisica', flat=True))

        categoria = form.cleaned_data.get('categoria')
        if categoria:
            if categoria == '1':
                registros = registros.filter(prontuario__vinculo__user__eh_aluno=True)
            elif categoria == '2':
                registros = registros.filter(prontuario__vinculo__user__eh_servidor=True)
            elif categoria == '3':
                registros = registros.filter(prontuario__vinculo__user__eh_prestador=True)
            elif categoria == '4':
                registros = registros.filter(prontuario__vinculo__user__eh_aluno=False, prontuario__vinculo__user__eh_servidor=False, prontuario__vinculo__user__eh_prestador=False)

        if form.cleaned_data.get('campus'):
            if categoria == '1':
                alunos_do_campus = Aluno.objects.filter(situacao=SituacaoMatricula.MATRICULADO, curso_campus__diretoria__setor__uo=form.cleaned_data.get('campus'))
                registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__in=alunos_do_campus.values_list('pessoa_fisica', flat=True))
            else:
                registros = registros.filter(prontuario__vinculo__pessoa__pessoafisica__funcionario__setor__uo=form.cleaned_data.get('campus'))

        registros_alunos_distintos = registros.distinct('prontuario__vinculo')
        registros = registros.filter(id__in=registros_alunos_distintos.values_list('id', flat=True)).order_by('prontuario__vinculo__pessoa__nome')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def atendimento_multidisciplinar(request, atendimento_id):
    title = 'Atendimento Multidisciplinar'
    especialidade = Especialidades(request.user)

    pode_gerenciar_atend_multidisciplinar = especialidade.is_odontologo() or especialidade.is_medico() or especialidade.is_nutricionista()

    # Carrega dados do atendimento, cabecalho e do vinculo do usuario
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.MULTIDISCIPLINAR)

    cadastrou_processosaudedoenca = False
    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento)
    processosaudedoenca_count = processosaudedoenca.count()
    if processosaudedoenca.exists():
        cadastrou_processosaudedoenca = True
        processosaudedoenca = processosaudedoenca.latest('id')
        processosaudedoenca_responsavel = processosaudedoenca.get_responsavel()

    procedimentos = AtendimentoMultidisciplinar.objects.filter(atendimento=atendimento).order_by('-id')
    procedimentos_titulo = 'Procedimentos'
    procedimentos_count = procedimentos.count()
    exclude_fields = ('id', 'data_cadastro', 'atendimento', 'profissional')
    custom_fields = dict(get_cadastro_display=Column('Cadastrado por', accessor="get_cadastro_display"))
    campos = ('procedimentos', 'descricao')
    sequence = ['procedimentos', 'descricao', 'get_cadastro_display']
    table_procedimentos = get_table(queryset=procedimentos, sequence=sequence, custom_fields=custom_fields, fields=campos, exclude_fields=exclude_fields)

    return locals()


@rtr()
@group_required(['Médico', 'Odontólogo', 'Nutricionista'])
def adicionar_procedimento_multidisciplinar(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    if atendimento.usuario_aberto != request.user:
        raise PermissionDenied

    title = f'Adicionar Procedimento - {atendimento.get_vinculo()}'

    procedimento = AtendimentoMultidisciplinar.objects.filter(atendimento=atendimento.pk)

    if procedimento.exists():
        procedimento = procedimento.latest('id')
    else:
        procedimento = AtendimentoMultidisciplinar()

    procedimento.profissional = request.user
    procedimento.data_cadastro = datetime.datetime.now()
    procedimento.atendimento = atendimento

    especialidade = Especialidades(request.user)
    form = AtendimentoMultidisciplinarForm(request.POST or None, instance=procedimento, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_multidisciplinar/{atendimento.id}/', 'Atendimento multidisciplinar registrado com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def cancelar_atividade_grupo(request, atividade_id):
    atividade = get_object_or_404(AtividadeGrupo, pk=atividade_id)
    if get_uo(request.user) == atividade.uo:
        atividade.cancelada = True
        atividade.save()
        return httprr('/admin/saude/atividadegrupo/', 'Atendimento cancelado com sucesso.')

    raise PermissionDenied()


@rtr()
@group_required(Especialidades.GRUPOS)
def atendimento_nutricional(request, atendimento_id):
    title = 'Atendimento Nutricional'
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.NUTRICIONAL)

    pode_editar = (request.user == atendimento.usuario_aberto) and atendimento.situacao == SituacaoAtendimento.ABERTO

    especialidade = Especialidades(request.user)

    atendimento_nutricao = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    atendimento_nutricao_responsavel = False
    if atendimento_nutricao.exists():
        atendimento_nutricao = atendimento_nutricao[0]
        atendimento_nutricao_responsavel = atendimento_nutricao.get_responsavel()

    cadastrou_antecedentes = False
    cadastrou_processosaudedoenca = False

    antecedentesfamiliares = AntecedentesFamiliares.objects.filter(atendimento=atendimento)
    antecedentesfamiliares_titulo = 'Antecedentes'
    antecedentesfamiliares_count = antecedentesfamiliares.count()
    if antecedentesfamiliares.exists():
        cadastrou_antecedentes = True
        antecedentesfamiliares = antecedentesfamiliares.latest('id')
        antecedentesfamiliares_responsavel = antecedentesfamiliares.get_responsavel()

    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento)
    processosaudedoenca_titulo = 'Processo Saúde-Doença'
    processosaudedoenca_count = processosaudedoenca.count()
    if processosaudedoenca.exists():
        cadastrou_processosaudedoenca = True
        processosaudedoenca = processosaudedoenca.latest('id')
        processosaudedoenca_responsavel = processosaudedoenca.get_responsavel()

    aba_antecedentes_preenchida = cadastrou_antecedentes or cadastrou_processosaudedoenca

    habitosdevida = HabitosDeVida.objects.filter(atendimento=atendimento)
    habitos_count = habitosdevida.count()
    if habitosdevida.exists():
        habitosdevida = habitosdevida.latest('id')
        habitosdevida_responsavel = habitosdevida.get_responsavel()

    antropometria = Antropometria.objects.filter(atendimento=atendimento)
    antropometria_count = antropometria.count()
    if antropometria.exists():
        cadastrou_antropometria = True
        antropometria = antropometria.latest('id')
        antropometria_responsavel = antropometria.get_responsavel()

    dados_gerais_alimentacao = atendimento_nutricao.tem_dados_gerais_alimentacao()
    dados_consumo = ConsumoNutricao.objects.filter(atendimento=atendimento).order_by('id')
    plano_alimentar = PlanoAlimentar.objects.filter(atendimento=atendimento)

    lista_respostas_marcadores = {}
    respostas_marcadores = RespostaMarcadorNutricao.objects.filter(atendimento=atendimento)
    respostas_marcadores_responsavel = None
    if respostas_marcadores.exists():
        respostas_marcadores_responsavel = respostas_marcadores.latest('id').get_responsavel()
    for pergunta in respostas_marcadores.distinct('pergunta'):
        chave = f'{pergunta.pergunta}'
        lista_respostas_marcadores[chave] = list()

    for resposta in RespostaMarcadorNutricao.objects.filter(atendimento=atendimento):
        chave = f'{resposta.pergunta}'
        lista_respostas_marcadores[chave].append(resposta.resposta)

    frequencia_marcadores = FrequenciaAlimentarNutricao.objects.filter(atendimento=atendimento)
    aba_anamnese_preenchida = habitos_count or antropometria_count or dados_gerais_alimentacao or dados_consumo or atendimento_nutricao.restricao_alimentar.exists()
    prontuario = atendimento.prontuario
    exames_laboratoriais = ExameLaboratorial.objects.filter(prontuario=prontuario).order_by('-data_realizado',
                                                                                            'categoria')
    dados_exames = dict()

    categorias = CategoriaExameLaboratorial.objects.filter(
        tipoexamelaboratorial__isnull=False,
        id__in=ExameLaboratorial.objects.filter(prontuario=prontuario).values_list('categoria', flat=True)
    )

    for categoria in categorias:
        registros = dict()
        for item in ValorExameLaboratorial.objects.filter(exame__prontuario=prontuario,
                                                          tipo__categoria=categoria).order_by('tipo__nome'):
            if not item.exame.sigiloso or (
                    item.exame.sigiloso and item.exame.profissional == request.user.get_relacionamento()):
                chave = f'{item.tipo.nome} ({item.tipo.unidade})'
                registros[chave] = dict()
        meses = dict()

        for idx, exame in enumerate(
                ExameLaboratorial.objects.filter(prontuario=prontuario, categoria=categoria).order_by('data_realizado'),
                1):
            if not exame.sigiloso or (exame.sigiloso and exame.profissional == request.user.get_relacionamento()):
                if str(format_(exame.data_realizado)) in meses.keys():
                    index = 1
                    for indice in list(meses.keys()):
                        if str(format_(exame.data_realizado)) in indice:
                            index += 1
                    chave_exame = '{} ({})'.format(exame.data_realizado.strftime("%d/%m/%Y"), index)
                else:
                    chave_exame = '{}'.format(exame.data_realizado.strftime("%d/%m/%Y"))
                meses[chave_exame] = dict()

            for item in ValorExameLaboratorial.objects.filter(exame=exame).order_by('tipo__nome'):
                if not item.exame.sigiloso or (
                        item.exame.sigiloso and item.exame.profissional == request.user.get_relacionamento()):
                    chave = f'{item.tipo.nome} ({item.tipo.unidade})'
                    registros[chave][chave_exame] = f'{item.valor} {item.tipo.unidade}'

        meses_ordenados = collections.OrderedDict(sorted(list(meses.items()), reverse=True))
        registros_ordenados = collections.OrderedDict(sorted(list(registros.items()), key=lambda x: x[0]))
        dados_exames[categoria.nome] = dict(meses=meses_ordenados, registros=registros_ordenados)
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_motivo_nutricao(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Motivo do Atendimento - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_motivo', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoMotivoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_motivo', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_avaliacao_gastrointestinal(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Motivo do Atendimento - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoAvalGastroForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_dados_alimentacao(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Dados Gerais de Alimentação - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoDadosAlimentacaoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_restricao_alimentar(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Restrição Alimentar - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoRestricaoAlimentarForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_consumo_nutricao(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Recordatório Alimentar - {atendimento.get_vinculo()}'
    obj = ConsumoNutricao()
    obj.atendimento = atendimento
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    form = AtendimentoNutricaoConsumoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_diagnostico_nutricional(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Diagnóstico Nutricional - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_diagnostico_nutricional', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoDiagnosticoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_diagnostico_nutricional', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_categoria_trabalho(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Diagnóstico Nutricional - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_conduta_nutricional', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoCategoriaTrabalhoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_conduta_nutricional', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_conduta_nutricao(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Diagnóstico Nutricional - {atendimento.get_vinculo()}'
    obj = AtendimentoNutricao.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_conduta_nutricional', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoNutricao()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = AtendimentoNutricaoCondutaForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_conduta_nutricional', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_plano_alimentar(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Plano Alimentar - {atendimento.get_vinculo()}'
    form = PlanoAlimentarForm(request.POST or None, request=request)
    if form.is_valid():
        o = form.save(False)
        o.profissional = request.user
        o.data_cadastro = datetime.datetime.now()
        o.atendimento = atendimento
        o.save()
        form.save_m2m()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_conduta_nutricional', 'Atendimento registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Nutricionista'])
def editar_plano_alimentar(request, plano_id):
    plano = get_object_or_404(PlanoAlimentar, pk=plano_id)
    title = f'Editar Plano Alimentar - {plano.atendimento.get_vinculo()}'
    form = PlanoAlimentarForm(request.POST or None, request=request, instance=plano)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_nutricional/{plano.atendimento_id}/?tab=aba_conduta_nutricional', 'Plano alimentar editado com sucesso.')
    return locals()


@documento(enumerar_paginas=False, validade=360)
@rtr()
@group_required(['Nutricionista'])
def imprimir_plano_alimentar(request, plano_id):
    plano = get_object_or_404(PlanoAlimentar, pk=plano_id)
    atendimento = plano.atendimento
    especialidade = Especialidades(request.user)
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    if request.user == atendimento.usuario_aberto or (especialidade.is_nutricionista() and plano.plano_alimentar_liberado):

        hoje = datetime.datetime.now().date()
        if atendimento.aluno:
            campus = atendimento.aluno.curso_campus.diretoria.setor.uo
        else:
            campus = get_uo(request.user)

        if Antropometria.objects.filter(atendimento=atendimento).exists():
            registro = Antropometria.objects.filter(atendimento=atendimento)[0]
            peso = registro.get_peso_display()
            altura = registro.get_estatura_display()
            imc = registro.get_IMC()
        orientacoes = receitas = None

        orientacoes = plano.orientacao_nutricional.all()
        receitas = plano.receita_nutricional.all()

        if campus.sigla in ['NC', 'CN', 'PF']:
            titulo = 'Coordenação de Atividades Estudantis'
        elif campus.sigla == 'CNAT':
            titulo = 'Diretoria de Atividades Estudantis'
        elif campus.sigla == get_sigla_reitoria():
            titulo = 'Diretoria de Gestão de Atividades Estudantis'

        return locals()

    else:
        raise PermissionDenied


@group_required(['Nutricionista'])
def remover_plano_alimentar(request, plano_id):
    plano = get_object_or_404(PlanoAlimentar, pk=plano_id)
    atendimento = plano.atendimento
    if request.user == plano.atendimento.usuario_aberto:
        plano.delete()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_conduta_nutricional', 'Plano Alimentar excluído com sucesso.')

    raise PermissionDenied()


@group_required(['Nutricionista'])
def remover_receita(request, atendimentonutricao_id, receita_id):
    atendimento_nutricao = get_object_or_404(AtendimentoNutricao, pk=atendimentonutricao_id)
    receita = get_object_or_404(ReceitaNutricional, pk=receita_id)
    if request.user == atendimento_nutricao.atendimento.usuario_aberto:
        atendimento_nutricao.receita_nutricional.remove(receita)
        return httprr(f'/saude/atendimento_nutricional/{atendimento_nutricao.atendimento_id}/?tab=aba_conduta_nutricional', 'Receita excluída com sucesso.')

    raise PermissionDenied()


@group_required(['Nutricionista'])
def remover_conduta_nutricao(request, atendimentonutricao_id):
    atendimento_nutricao = get_object_or_404(AtendimentoNutricao, pk=atendimentonutricao_id)
    if request.user == atendimento_nutricao.atendimento.usuario_aberto:
        atendimento_nutricao.conduta = None
        atendimento_nutricao.save()
        return httprr(f'/saude/atendimento_nutricional/{atendimento_nutricao.atendimento_id}/?tab=aba_conduta_nutricional', 'Conduta excluída com sucesso.')

    raise PermissionDenied()


@group_required(['Nutricionista'])
def remover_consumo(request, consumo_id):
    consumo = get_object_or_404(ConsumoNutricao, pk=consumo_id)
    if request.user == consumo.atendimento.usuario_aberto:
        atendimento = consumo.atendimento
        consumo.delete()
        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Registro de consumo excluído com sucesso.')

    raise PermissionDenied()


@rtr()
@group_required(['Nutricionista'])
def editar_consumo(request, consumo_id):
    consumo = get_object_or_404(ConsumoNutricao, pk=consumo_id)
    title = 'Editar Consumo'
    if request.user == consumo.atendimento.usuario_aberto:
        form = AtendimentoNutricaoConsumoForm(request.POST or None, request=request, instance=consumo)
        if form.is_valid():
            form.save()
            return httprr(f'/saude/atendimento_nutricional/{consumo.atendimento_id}/?tab=aba_anamnese', 'Consumo editado com sucesso.')

        return locals()

    raise PermissionDenied()


@rtr()
@group_required(
    ['Odontólogo', 'Coordenador de Saúde Sistêmico', 'Auditor', 'Coordenador de Atividades Estudantis Sistêmico', 'Coordenador de Atividades Estudantis', 'Técnico em Saúde Bucal', 'Coordenador de Saúde']
)
def relatorios_atendimentos_odontologicos(request):
    title = 'Relatórios de Atendimentos Odontológicos'
    atendimentos = (
        Atendimento.objects.filter(tipo=TipoAtendimento.ODONTOLOGICO).exclude(situacao=SituacaoAtendimento.CANCELADO).order_by('prontuario__vinculo__pessoa__nome', '-id')
    )
    form = RelatorioOdontologicoForm(request.GET or None)
    if form.is_valid():
        campus = form.cleaned_data.get('campus')
        categoria = form.cleaned_data.get('categoria')
        data_inicial = form.cleaned_data.get('data_inicial')
        data_final = form.cleaned_data.get('data_final')
        if campus:
            atendimentos = atendimentos.filter(usuario_aberto__vinculo__setor__uo=campus)

        if categoria:
            if categoria == Atendimento.CATEGORIA_ALUNO:
                atendimentos = atendimentos.filter(aluno__isnull=False)
            elif categoria == Atendimento.CATEGORIA_SERVIDOR:
                atendimentos = atendimentos.filter(servidor__isnull=False)
            elif categoria == Atendimento.CATEGORIA_PRESTADOR_SERVICO:
                atendimentos = atendimentos.filter(prestador_servico__isnull=False)
            elif categoria == Atendimento.CATEGORIA_COMUNIDADE_EXTERNA:
                atendimentos = atendimentos.filter(pessoa_externa__isnull=False)

        if data_inicial:
            atendimentos = atendimentos.filter(data_aberto__gte=data_inicial)

        if data_final:
            atendimentos = atendimentos.filter(data_aberto__lte=data_final)

        if 'xls' in request.GET:
            return tasks.relatorios_atendimentos_odontologicos_to_xls(atendimentos)

    return locals()


@rtr()
@group_required('Odontólogo')
def excluir_exame_periodontal(request, exame_id):
    exame = get_object_or_404(ExamePeriodontal, pk=exame_id)
    if request.user == exame.profissional:
        atendimento = exame.atendimento
        exame.delete()
        return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/', 'Exame periodontal excluido com sucesso.')

    raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def editar_cartao_sus(request, aluno_id):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    title = f'Editar Cartão SUS - {aluno}'
    form = CartaoSUSAlunoForm(request.POST or None, instance=aluno)
    if form.is_valid():
        form.save()
        return httprr('..', 'Número SUS cadastrado com sucesso.')

    return locals()


@rtr()
@group_required('Odontólogo')
def excluir_procedimento_odontologico(request, procedimento_id):
    procedimento = get_object_or_404(ProcedimentoOdontologico, pk=procedimento_id)

    if procedimento.profissional == request.user:
        atendimento = procedimento.atendimento
        procedimento.delete()

        return httprr(
            f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_procedimento',
            'Procedimento excluído com sucesso. Atualize o odontograma e o plano de tratamento manualmente, caso seja necessário.',
        )

    raise PermissionDenied


@rtr()
@group_required(['Odontólogo'])
def obs_registrar_execucao(request, plano_tratamento_id):
    title = 'Adicionar Observações'
    form = ObsRegistroExecucaoForm(request.POST or None)
    if form.is_valid():
        return httprr('/saude/registrar_execucao_plano/{}/?obs={}'.format(plano_tratamento_id, form.cleaned_data.get('obs')))
    return locals()


@rtr()
@group_required(['Nutricionista'])
def adicionar_marcadores_consumo_alimentar(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = 'Marcadores de Práticas e de Consumo Alimentar'
    if request.user == atendimento.usuario_aberto:
        form = MarcadorConsumoAlimentarForm(request.POST or None, request=request)
        if form.is_valid():

            chaves = list(request.POST.keys())
            for item in chaves:
                valores = request.POST.getlist(item)
                if 'pergunta_' in item:
                    id = item.split('_')[1]
                    for valor in valores:
                        if PerguntaMarcadorNutricao.objects.filter(id=id, ativo=True).exists():
                            o = RespostaMarcadorNutricao()
                            o.profissional = request.user
                            o.data_cadastro = datetime.datetime.now()
                            o.atendimento = atendimento
                            o.pergunta = get_object_or_404(PerguntaMarcadorNutricao, pk=id)
                            o.resposta = get_object_or_404(OpcaoRespostaMarcadorNutricao, pk=int(valor))
                            o.save()

                elif 'frequencia_' in item:
                    id = item.split('_')[1]
                    for valor in valores:
                        if FrequenciaPraticaAlimentar.objects.filter(id=id, ativo=True).exists():
                            o = FrequenciaAlimentarNutricao()
                            o.profissional = request.user
                            o.data_cadastro = datetime.datetime.now()
                            o.atendimento = atendimento
                            o.frequencia = get_object_or_404(FrequenciaPraticaAlimentar, pk=id)
                            o.valor = valor
                            o.save()

            return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Marcadores alterados com sucesso.')

        return locals()

    raise PermissionDenied()


def excluir_marcadores_consumo_alimentar(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    if request.user == atendimento.usuario_aberto:
        RespostaMarcadorNutricao.objects.filter(atendimento=atendimento).delete()
        FrequenciaAlimentarNutricao.objects.filter(atendimento=atendimento).delete()

        return httprr(f'/saude/atendimento_nutricional/{atendimento.id}/?tab=aba_anamnese', 'Marcadores removidos com sucesso.')

    raise PermissionDenied()


@rtr()
@group_required(['Psicólogo'])
def registrar_hora_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Registrar Data/Hora do Atendimento - {atendimento.get_vinculo()}'
    obj = AtendimentoPsicologia.objects.filter(atendimento=atendimento)
    if obj.exists():
        obj = obj.latest('id')
        if obj.profissional != request.user:
            return httprr(f'/saude/atendimento_psicologico/{atendimento.id}/?tab=aba_motivo', 'Você não pode editar este registro.', tag='error')
    else:
        obj = AtendimentoPsicologia()
    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento
    form = DataHoraAtendimentoPsicologicoForm(request.POST or None, instance=obj, request=request)
    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_psicologico/{atendimento.id}/?tab=aba_motivo', 'Data/hora do atendimento registrada com sucesso.')
    return locals()


@rtr()
@group_required(['Psicólogo'])
def adicionar_anexo_psicologia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Anexo - {atendimento.get_vinculo()}'
    form = AnexoPsicologiaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        o = form.save(False)
        o.atendimento = atendimento
        o.cadastrado_por_vinculo = request.user.get_vinculo()
        gera_string = str(uuid.uuid4())
        extensao = o.arquivo.url.split('.')
        if len(extensao) > 1:
            extensao = extensao[len(extensao) - 1]
            novo_nome = gera_string + '.' + extensao
        else:
            novo_nome = gera_string
        o.arquivo.name = novo_nome
        o.save()
        return httprr(f'/saude/atendimento_psicologico/{atendimento.id}/?tab=aba_anexos', 'Anexo registrado com sucesso.')
    return locals()


@rtr()
@group_required(['Psicólogo'])
def editar_anexo_psicologia(request, anexo_id):
    anexo = get_object_or_404(AnexoPsicologia, pk=anexo_id)
    if request.user.get_vinculo() == anexo.cadastrado_por_vinculo:
        title = f'Editar Anexo - {anexo.atendimento.get_vinculo()}'
        form = AnexoPsicologiaForm(request.POST or None, request.FILES or None, instance=anexo)
        if form.is_valid():
            o = form.save(False)
            gera_string = str(uuid.uuid4())
            extensao = o.arquivo.url.split('.')
            if len(extensao) > 1:
                extensao = extensao[len(extensao) - 1]
                novo_nome = gera_string + '.' + extensao
            else:
                novo_nome = gera_string
            o.arquivo.name = novo_nome
            o.save()
            return httprr(f'/saude/atendimento_psicologico/{anexo.atendimento.id}/?tab=aba_anexos', 'Anexo editado com sucesso.')
    else:
        raise PermissionDenied
    return locals()


@rtr()
@group_required(['Psicólogo'])
def remover_anexo_psicologia(request, anexo_id):
    anexo = get_object_or_404(AnexoPsicologia, pk=anexo_id)
    if request.user.get_vinculo() == anexo.cadastrado_por_vinculo:
        atendimento = anexo.atendimento
        anexo.delete()
        return httprr(f'/saude/atendimento_psicologico/{atendimento.id}/?tab=aba_anexos', 'Anexo removido com sucesso.')
    raise PermissionDenied


@rtr()
@permission_required('saude.view_atividadegrupo')
def relatorio_atendimento_odontologia(request):
    title = 'Relatório de Atendimento de Odontologia'
    form = RelatorioAtendimentoForm(request.GET or None, request=request)
    if form.is_valid():
        atendimentos = Atendimento.objects.filter(tipo=TipoAtendimento.ODONTOLOGICO, aluno__isnull=False).exclude(situacao=SituacaoAtendimento.CANCELADO)
        data_inicial = form.cleaned_data.get('data_inicial')
        data_final = form.cleaned_data.get('data_final')
        campus = form.cleaned_data.get('campus')
        curso = form.cleaned_data.get('curso')
        turma = form.cleaned_data.get('turma')
        modalidade = form.cleaned_data.get('modalidade')
        sexo = form.cleaned_data.get('sexo')
        idade = form.cleaned_data.get('idade')
        participante = form.cleaned_data.get('participante')

        if data_inicial:
            atendimentos = atendimentos.filter(data_aberto__gte=datetime.datetime(data_inicial.year, data_inicial.month, data_inicial.day, 0, 0, 0))

        if data_final:
            atendimentos = atendimentos.filter(data_aberto__lte=datetime.datetime(data_final.year, data_final.month, data_final.day, 23, 59, 59))

        if campus:
            atendimentos = atendimentos.filter(usuario_aberto__vinculo__setor__uo=campus)

        if curso:
            atendimentos = atendimentos.filter(aluno__curso_campus=curso)

        if turma:
            alunos = turma.get_alunos_matriculados()
            atendimentos = atendimentos.filter(aluno__pessoa_fisica__in=alunos.values_list('aluno__pessoa_fisica', flat=True))

        if modalidade:
            atendimentos = atendimentos.filter(aluno__curso_campus__modalidade=modalidade)

        if sexo:
            atendimentos = atendimentos.filter(aluno__pessoa_fisica__sexo=sexo)

        if idade:
            try:
                int(idade)
                pessoas = PessoaFisica.objects.filter(id__in=atendimentos.values_list('aluno__pessoa_fisica', flat=True))
                ids = list()
                for pessoa in pessoas:
                    if pessoa.idade == int(idade):
                        ids.append(pessoa.id)
                atendimentos = atendimentos.filter(aluno__pessoa_fisica__in=ids)
            except Exception:
                return httprr('/saude/relatorio_atendimento_odontologia/', 'Valor inválido para o campo "Idade".', tag='error')

        if participante:
            hoje = datetime.datetime.today()
            participantes = Participacao.objects.filter(Q(data_inicio__lte=hoje), Q(data_termino__gte=hoje) | Q(data_termino__isnull=True))
            atendimentos = atendimentos.filter(aluno__id__in=participantes.values_list('aluno', flat=True))

        if atendimentos.exists():
            media_cpo = media_c = media_p = media_o = 0
            total_alunos_atendidos = atendimentos.distinct('aluno').count()
            tabela = {}
            for indice in range(0, 33):
                chave = f'{indice}'
                tabela[chave] = list()

            for atendimento in atendimentos.distinct('aluno'):
                if atendimento.get_odontograma():
                    cpo, c, p, o = atendimento.get_odontograma().get_indice_cpod()

                    media_cpo += int(cpo)
                    media_c += int(c)
                    media_p += int(p)
                    media_o += int(o)
                    chave = f'{cpo}'
                    tabela[chave].append(atendimento.id)

            media_cpo = Decimal(float(media_cpo) / float(total_alunos_atendidos)).quantize(Decimal(10) ** -2)
            media_c = Decimal(float(media_c) / float(total_alunos_atendidos)).quantize(Decimal(10) ** -2)
            media_p = Decimal(float(media_p) / float(total_alunos_atendidos)).quantize(Decimal(10) ** -2)
            media_o = Decimal(float(media_o) / float(total_alunos_atendidos)).quantize(Decimal(10) ** -2)
            resultado = collections.OrderedDict(sorted(list(tabela.items()), reverse=True, key=lambda x: int(x[0])))
            dados = list()
            for item in list(resultado.items()):
                qtd = len(item[1])
                if qtd:
                    dados.append([item[0], qtd])

            grafico1 = BarChart('grafico1', title='Alunos por índice CPO-D ', subtitle='Número de alunos por índice CPO-D', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            total = (
                ProcedimentoOdontologico.objects.filter(atendimento__in=atendimentos.values_list('id', flat=True))
                .values('procedimento__denominacao')
                .annotate(qtd=Count('procedimento__denominacao'))
                .order_by('procedimento__denominacao')
            )
            for registro in total:
                dados2.append([registro['procedimento__denominacao'], registro['qtd']])

            dados2.append(['Procedimentos Odontológicos', total.count()])

            grafico2 = BarChart(
                'grafico2', title='Procedimentos Odontológicos Realizados', subtitle='Quantitativo de Procedimentos Odontológicos Realizados', minPointLength=0, data=dados2
            )

            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            total = Odontograma.objects.filter(atendimento__in=atendimentos.values_list('id', flat=True))
            for tipo in TipoConsultaOdontologia.objects.all():
                dados3.append([tipo.descricao, total.filter(tipo_consulta=tipo).count()])

            grafico3 = BarChart('grafico3', title='Quantitativo de Consultas', subtitle='Quantitativo de Consultas', minPointLength=0, data=dados3)

            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            gravidas = ProcessoSaudeDoenca.objects.filter(gestante=True)
            gravidas_atendidas = atendimentos.filter(id__in=gravidas.values_list('atendimento', flat=True))
            total = Odontograma.objects.filter(atendimento__in=gravidas_atendidas.values_list('id', flat=True))

            dados4.append(['Tratamento Concluído', total.filter(tipo_consulta__id=TipoConsultaOdontologia.CONCLUIDO).count()])
            dados4.append(['Tratamento em Andamento', total.exclude(tipo_consulta__id=TipoConsultaOdontologia.CONCLUIDO).count()])

            grafico4 = PieChart('grafico4', title='Gestantes com Tratamento Concluído', subtitle='Quantitativo de Consultas', minPointLength=0, data=dados4)

            setattr(grafico4, 'id', 'grafico4')

            pie_chart_lists = [grafico1, grafico2, grafico3, grafico4]

    return locals()


@rtr()
@permission_required('saude.view_atividadegrupo')
def relatorio_atendimento_medico_enfermagem(request):
    title = 'Relatório de Atendimento Médico/Enfermagem'
    form = RelatorioAtendimentoForm(request.GET or None, request=request)
    if form.is_valid():
        data_inicial = form.cleaned_data.get('data_inicial')
        data_final = form.cleaned_data.get('data_final')
        campus = form.cleaned_data.get('campus')
        modalidade = form.cleaned_data.get('modalidade')
        curso = form.cleaned_data.get('curso')
        turma = form.cleaned_data.get('turma')
        sexo = form.cleaned_data.get('sexo')
        idade = form.cleaned_data.get('idade')
        participante = form.cleaned_data.get('participante')
        atendimentos = Atendimento.objects.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO, aluno__isnull=False).exclude(situacao=SituacaoAtendimento.CANCELADO)

        if data_inicial:
            atendimentos = atendimentos.filter(data_aberto__gte=datetime.datetime(data_inicial.year, data_inicial.month, data_inicial.day, 0, 0, 0))

        if data_final:
            atendimentos = atendimentos.filter(data_aberto__lte=datetime.datetime(data_final.year, data_final.month, data_final.day, 23, 59, 59))

        if campus:
            atendimentos = atendimentos.filter(usuario_aberto__vinculo__setor__uo=campus)

        if curso:
            atendimentos = atendimentos.filter(aluno__curso_campus=curso)

        if turma:
            alunos = turma.get_alunos_matriculados()
            atendimentos = atendimentos.filter(aluno__pessoa_fisica__in=alunos.values_list('aluno__pessoa_fisica', flat=True))

        if modalidade:
            atendimentos = atendimentos.filter(aluno__curso_campus__modalidade=modalidade)

        if sexo:
            atendimentos = atendimentos.filter(aluno__pessoa_fisica__sexo=sexo)

        if idade:
            try:
                int(idade)
                pessoas = PessoaFisica.objects.filter(id__in=atendimentos.values_list('aluno__pessoa_fisica', flat=True))
                ids = list()
                for pessoa in pessoas:
                    if pessoa.idade == int(idade):
                        ids.append(pessoa.id)
                atendimentos = atendimentos.filter(aluno__pessoa_fisica__in=ids)
            except Exception:
                return httprr('/saude/relatorio_atendimento_medico_enfermagem/', 'Valor inválido para o campo "Idade".', tag='error')

        if participante:
            hoje = datetime.datetime.today()
            participantes = Participacao.objects.filter(Q(data_inicio__lte=hoje), Q(data_termino__gte=hoje) | Q(data_termino__isnull=True))
            atendimentos = atendimentos.filter(aluno__id__in=participantes.values_list('aluno', flat=True))

        if 'xls' in request.GET:
            return tasks.relatorio_atendimento_medico_enfermagem_to_xls(atendimentos)
        if atendimentos.exists():

            dados = list()
            dados.append(
                [
                    'Capítulo I - Algumas doenças infecciosas e parasitárias',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='A00', hipotesediagnostica__cid__codigo__lte='B99').count(),
                ]
            )
            dados.append(
                ['Capítulo II - Neoplasias [tumores]', atendimentos.filter(hipotesediagnostica__cid__codigo__gte='C00', hipotesediagnostica__cid__codigo__lte='D48').count()]
            )
            dados.append(
                [
                    'Capítulo III - Doenças do sangue e dos órgãos hematopoéticos e alguns transtornos imunitários',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='D50', hipotesediagnostica__cid__codigo__lte='D89').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo IV - Doenças endócrinas, nutricionais e metabólicas',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='E00', hipotesediagnostica__cid__codigo__lte='E90').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo V - Transtornos mentais e comportamentais',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='F00', hipotesediagnostica__cid__codigo__lte='F99').count(),
                ]
            )
            dados.append(
                ['Capítulo VI - Doenças do sistema nervoso', atendimentos.filter(hipotesediagnostica__cid__codigo__gte='G00', hipotesediagnostica__cid__codigo__lte='G99').count()]
            )
            dados.append(
                ['Capítulo VII - Doenças do olho e anexos', atendimentos.filter(hipotesediagnostica__cid__codigo__gte='H00', hipotesediagnostica__cid__codigo__lte='H59').count()]
            )
            dados.append(
                [
                    'Capítulo VIII - Doenças do ouvido e da apófise mastóide',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='H60', hipotesediagnostica__cid__codigo__lte='H95').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo IX - Doenças do aparelho circulatório',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='I00', hipotesediagnostica__cid__codigo__lte='I99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo X - Doenças do aparelho respiratório',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='J00', hipotesediagnostica__cid__codigo__lte='J99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XI - Doenças do aparelho digestivo',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='K00', hipotesediagnostica__cid__codigo__lte='K93').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XII - Doenças da pele e do tecido subcutâneo',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='L00', hipotesediagnostica__cid__codigo__lte='L99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XIII - Doenças do sistema osteomuscular e do tecido conjuntivo',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='M00', hipotesediagnostica__cid__codigo__lte='M99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XIV - Doenças do aparelho geniturinário',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='N00', hipotesediagnostica__cid__codigo__lte='N99').count(),
                ]
            )
            dados.append(
                ['Capítulo XV - Gravidez, parto e puerpério', atendimentos.filter(hipotesediagnostica__cid__codigo__gte='O00', hipotesediagnostica__cid__codigo__lte='O99').count()]
            )
            dados.append(
                [
                    'Capítulo XVI - Algumas afecções originadas no período perinatal',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='P00', hipotesediagnostica__cid__codigo__lte='P96').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XVII - Malformações congênitas, deformidades e anomalias cromossômicas',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='Q00', hipotesediagnostica__cid__codigo__lte='Q99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XVIII - Sintomas, sinais e achados anormais de exames clínicos e de laboratório, não classificados em outra parte',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='R00', hipotesediagnostica__cid__codigo__lte='R99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XIX - Lesões, envenenamento e algumas outras conseqüências de causas externas',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='S00', hipotesediagnostica__cid__codigo__lte='T98').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XX - Causas externas de morbidade e de mortalidade',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='V01', hipotesediagnostica__cid__codigo__lte='Y98').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XXI - Fatores que influenciam o estado de saúde e o contato com os serviços de saúde',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='Z00', hipotesediagnostica__cid__codigo__lte='Z99').count(),
                ]
            )
            dados.append(
                [
                    'Capítulo XXII - Códigos para propósitos especiais',
                    atendimentos.filter(hipotesediagnostica__cid__codigo__gte='U04', hipotesediagnostica__cid__codigo__lte='U99').count(),
                ]
            )

            grafico1 = BarChart('grafico1', title='Diagnósticos do CID-10 por capítulo', subtitle='Quantidade de diagnósticos do CID-10 por capítulo', minPointLength=0, data=dados)

            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            total = (
                IntervencaoEnfermagem.objects.filter(atendimento__in=atendimentos.values_list('id', flat=True))
                .values('procedimento_enfermagem__denominacao')
                .annotate(qtd=Count('procedimento_enfermagem__denominacao'))
                .order_by('procedimento_enfermagem__denominacao')
            )

            for registro in total:
                dados2.append([registro['procedimento_enfermagem__denominacao'], registro['qtd']])

            grafico2 = BarChart('grafico2', title='Intervenções de Enfermagem', subtitle='Quantitativo de Intervenções de Enfermagem', minPointLength=0, data=dados2)

            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            ids_verificados = list()
            tem_alergia_alimento = tem_alergia_medicamento = 0
            for atendimento in atendimentos.filter(processosaudedoenca__isnull=False):
                if not atendimento.id in ids_verificados:
                    if ProcessoSaudeDoenca.objects.filter(atendimento=atendimento).order_by('-id')[0].alergia_alimentos:
                        tem_alergia_alimento += 1
                    if ProcessoSaudeDoenca.objects.filter(atendimento=atendimento).order_by('-id')[0].alergia_medicamentos:
                        tem_alergia_medicamento += 1

                    ids_verificados.append(atendimento.id)

            dados3.append(['Alunos com Alergias à Alimentos', tem_alergia_alimento])
            dados3.append(['Alunos com Alergias à Medicamentos', tem_alergia_medicamento])

            grafico3 = BarChart(
                'grafico3', title='Alergias à Alimentos e Medicamentos', subtitle='Quantitativo de alunos com alergias à alimentos e medicamentos', minPointLength=0, data=dados3
            )

            setattr(grafico3, 'id', 'grafico3')

            pie_chart_lists = [grafico1, grafico2, grafico3]
    return locals()


@rtr()
@group_required('Psicólogo')
def relatorio_atendimento_psicologia(request):
    title = 'Relatório de Atendimento de Psicologia'
    form = RelatorioAtendimentoForm(request.GET or None, request=request)
    if form.is_valid():
        data_inicial = form.cleaned_data.get('data_inicial')
        data_final = form.cleaned_data.get('data_final')
        campus = form.cleaned_data.get('campus')
        curso = form.cleaned_data.get('curso')
        turma = form.cleaned_data.get('turma')
        modalidade = form.cleaned_data.get('modalidade')
        sexo = form.cleaned_data.get('sexo')
        idade = form.cleaned_data.get('idade')
        participante = form.cleaned_data.get('participante')

        atendimentos = AtendimentoPsicologia.objects.filter(atendimento__aluno__isnull=False)

        if data_inicial:
            atendimentos = atendimentos.filter(data_atendimento__gte=datetime.datetime(data_inicial.year, data_inicial.month, data_inicial.day, 0, 0, 0))

        if data_final:
            atendimentos = atendimentos.filter(data_atendimento__lte=datetime.datetime(data_final.year, data_final.month, data_final.day, 23, 59, 59))

        if campus:
            atendimentos = atendimentos.filter(atendimento__usuario_aberto__vinculo__setor__uo=campus)

        if curso:
            atendimentos = atendimentos.filter(atendimento__aluno__curso_campus=curso)

        if turma:
            alunos = turma.get_alunos_matriculados()
            atendimentos = atendimentos.filter(atendimento__aluno__pessoa_fisica__in=alunos.values_list('aluno__pessoa_fisica', flat=True))

        if modalidade:
            atendimentos = atendimentos.filter(atendimento__aluno__curso_campus__modalidade=modalidade)

        if sexo:
            atendimentos = atendimentos.filter(atendimento__aluno__pessoa_fisica__sexo=sexo)

        if idade:
            try:
                int(idade)
                pessoas = PessoaFisica.objects.filter(id__in=atendimentos.values_list('aluno__pessoa_fisica', flat=True))
                ids = list()
                for pessoa in pessoas:
                    if pessoa.idade == int(idade):
                        ids.append(pessoa.id)
                atendimentos = atendimentos.filter(atendimento__aluno__pessoa_fisica__in=ids)
            except Exception:
                return httprr('/saude/relatorio_atendimento_psicologia/', 'Valor inválido para o campo "Idade".', tag='error')

        if participante:
            hoje = datetime.datetime.today()
            participantes = Participacao.objects.filter(Q(data_inicio__lte=hoje), Q(data_termino__gte=hoje) | Q(data_termino__isnull=True))
            atendimentos = atendimentos.filter(atendimento__aluno__id__in=participantes.values_list('aluno', flat=True))

        dados = list()
        total = atendimentos.values('queixa_principal__descricao').annotate(qtd=Count('queixa_principal__descricao')).order_by('queixa_principal__descricao')
        for registro in total:
            dados.append([registro['queixa_principal__descricao'], registro['qtd']])

        grafico1 = BarChart('grafico1', title='Quantitativo por Queixa Principal', subtitle='Quantitativo por queixa principal', minPointLength=0, data=dados)

        setattr(grafico1, 'id', 'grafico1')

        dados2 = list()
        total = atendimentos.values('queixa_identificada__descricao').annotate(qtd=Count('queixa_identificada__descricao')).order_by('queixa_identificada__descricao')
        for registro in total:
            dados2.append([registro['queixa_identificada__descricao'], registro['qtd']])

        grafico2 = BarChart('grafico2', title='Quantitativo por Queixa Identificada', subtitle='Quantitativo por Queixa Identificada', minPointLength=0, data=dados2)

        setattr(grafico2, 'id', 'grafico2')
        pie_chart_lists = [grafico1, grafico2]

    return locals()


@rtr()
@group_required('Odontólogo')
def encaminhar_enfermagem_odonto(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    odontograma = atendimento.get_odontograma()
    if odontograma:
        odontograma.encaminhado_enfermagem = True
        odontograma.save()
        return httprr(f'/saude/atendimento_odontologico/{atendimento.id}/?tab=aba_procedimento', 'Atendimento encaminhado à enfermagem com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS_ATENDIMENTO_ENF)
def registrar_intervencao_odonto(request, atendimento_id, atendimento_origem_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    odontograma = atendimento.get_odontograma()
    if odontograma and not odontograma.atendido:
        odontograma.atendido = True
        odontograma.atendido_por_vinculo = request.user.get_vinculo()
        odontograma.atendido_em = datetime.datetime.now()
        odontograma.save()
        return httprr(
            f'/saude/atendimento_medico_enfermagem/{atendimento_origem_id}/?tab=aba_intervencaoenfermagem', 'A intervenção de enfermagem foi registrada com sucesso.'
        )
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS + ['Aluno', 'Atendente', 'Assistente Social'])
def agenda_atendimentos(request):
    title = 'Agenda de Atendimentos'
    especialidade = Especialidades(request.user)
    eh_profissional_saude = Especialidades.eh_profissional_saude(especialidade)
    eh_assistente_social = request.user.has_perm('ae.save_caracterizacao_do_campus')
    pode_cadastrar_horario = request.user.has_perm('saude.view_prontuario') or eh_assistente_social
    eh_aluno = False
    if request.user.eh_aluno:
        if request.user.get_relacionamento().situacao.ativo:
            eh_aluno = True
        else:
            return httprr('/', 'Apenas alunos com situação ativa podem agendar atendimentos.', tag='error')

    hoje = datetime.date.today()

    inicio_semana = hoje
    fim_semana = inicio_semana + datetime.timedelta(4)
    uo_ids = get_ids_uos(request.user)

    if not 'campus' in request.GET:
        if request.user.has_perm('ae.save_caracterizacao_do_campus'):
            return httprr(
                '/saude/agenda_atendimentos/?campus=&especialidade=Assistente Social&data_inicio={}&data_final={}&filtraratendimentos_form=Aguarde...'.format(
                    inicio_semana, fim_semana
                )
            )

        elif not request.user.has_perm('saude.add_prontuario') and not eh_aluno:
            return httprr(
                '/saude/agenda_atendimentos/?campus=&especialidade=Odontólogo&data_inicio={}&data_final={}&filtraratendimentos_form=Aguarde...'.format(
                    inicio_semana, fim_semana
                )
            )
        return httprr(
            '/saude/agenda_atendimentos/?campus=&especialidade=Todos&disponivel=on&data_inicio={}&data_final={}&filtraratendimentos_form=Aguarde...'.format(
                inicio_semana, fim_semana
            )
        )

    string = request.get_full_path()
    if '?' in string:
        string = string.split('?')[1]
    else:
        string = ''

    form = FiltrarAtendimentosForm(request.GET or None, request=request, eh_aluno=eh_aluno, uo_ids=uo_ids)
    if form.is_valid():

        especialidade = form.cleaned_data.get('especialidade')
        campus = form.cleaned_data.get('campus')
        data_inicial = form.cleaned_data.get('data_inicio') or inicio_semana
        data_final = form.cleaned_data.get('data_final') or fim_semana
        meus_agendamentos = form.cleaned_data.get('meus_agendamentos')
        disponivel = form.cleaned_data.get('disponivel')

        horarios = HorarioAtendimento.objects.filter(data__gte=data_inicial, data__lte=data_final, campus__in=uo_ids, cancelado=False).order_by('data', 'hora_termino')

        if campus:
            horarios = horarios.filter(campus=campus, cancelado=False).order_by('data', 'hora_termino')
        else:
            horarios = horarios.filter(campus__in=uo_ids, cancelado=False).order_by('data', 'hora_termino')

        if especialidade and not (especialidade == Especialidades.TODOS):
            horarios = horarios.filter(especialidade=especialidade)

        if meus_agendamentos:
            if pode_cadastrar_horario:
                horarios = horarios.filter(cadastrado_por_vinculo=request.user.get_vinculo())
            elif eh_aluno:
                horarios = horarios.filter(vinculo_paciente=request.user.get_vinculo())

        if disponivel:
            horarios = horarios.filter(disponivel=True)

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Atendente', 'Assistente Social'])
def adicionar_horario_atendimento_saude(request):
    especialidade = Especialidades(request.user)
    lista = list()
    title = 'Adicionar Horário de Atendimento'
    especialidade = Especialidades(request.user)
    especialidade_professional = ''
    eh_atendente = not request.user.has_perm('saude.add_prontuario') and not request.user.has_perm('ae.save_caracterizacao_do_campus')
    if especialidade.is_odontologo() or eh_atendente:
        especialidade_professional = Especialidades.ODONTOLOGO
    elif especialidade.is_psicologo():
        especialidade_professional = Especialidades.PSICOLOGO
    elif especialidade.is_medico():
        especialidade_professional = Especialidades.MEDICO
    elif especialidade.is_nutricionista():
        especialidade_professional = Especialidades.NUTRICIONISTA
    elif especialidade.is_fisioterapeuta():
        especialidade_professional = Especialidades.FISIOTERAPEUTA
    elif especialidade.is_enfermeiro():
        especialidade_professional = Especialidades.ENFERMEIRO
    elif especialidade.is_tecnico_enfermagem():
        especialidade_professional = Especialidades.TECNICO_ENFERMAGEM
    elif especialidade.is_auxiliar_enfermagem():
        especialidade_professional = Especialidades.AUXILIAR_DE_ENFERMAGEM
    elif especialidade.is_tecnico_saude_bucal():
        especialidade_professional = Especialidades.TECNICO_SAUDE_BUCAL
    elif especialidade.is_assistente_social():
        especialidade_professional = Especialidades.ASSISTENTE_SOCIAL
    form = HorarioAtendimentoForm(request.GET or None, request=request, especialidade_professional=especialidade_professional, eh_atendente=eh_atendente)
    if form.is_valid():
        inicio = form.cleaned_data.get('hora_inicio_1')
        termino = form.cleaned_data.get('hora_termino_1')
        duracao = form.cleaned_data.get('duracao')
        data = form.cleaned_data.get('data')
        data_fim_periodo = form.cleaned_data.get('data_fim')
        especialidade_escolhida = form.cleaned_data.get('especialidade')
        campus_escolhido = form.cleaned_data.get('campus_escolhido')
        campus_do_atendimento = campus_escolhido or get_uo(request.user)
        if data and inicio and termino and duracao and especialidade_escolhida:
            lista = list()
            termino_atendimento = datetime.datetime.combine(data, inicio) + datetime.timedelta(minutes=duracao)
            horario_inicial = datetime.datetime.combine(data, inicio)
            while termino_atendimento <= datetime.datetime.combine(data, termino):
                hora_inicio = horario_inicial
                hora_termino = termino_atendimento
                string = f'{hora_inicio.time()} - {hora_termino.time()}'
                lista.append(string)
                horario_inicial = termino_atendimento
                termino_atendimento = termino_atendimento + datetime.timedelta(minutes=duracao)
            ConfirmarHorarioAtendimentoForm = GetConfirmarHorarioAtendimentoForm(lista=lista)
            form2 = ConfirmarHorarioAtendimentoForm()
            if request.GET.get('confirmado'):
                termino_atendimento = datetime.datetime.combine(data, inicio) + datetime.timedelta(minutes=duracao)
                while termino_atendimento <= datetime.datetime.combine(data, termino):
                    hora_inicio = horario_inicial
                    hora_termino = termino_atendimento
                    string = f'{hora_inicio.time()} - {hora_termino.time()}'
                    lista.append(string)
                    horario_inicial = termino_atendimento
                    termino_atendimento = termino_atendimento + datetime.timedelta(minutes=duracao)
                ConfirmarHorarioAtendimentoForm = GetConfirmarHorarioAtendimentoForm(lista=lista)
                form2 = ConfirmarHorarioAtendimentoForm()
                if request.GET.get('confirmado'):
                    if not data_fim_periodo:
                        data_fim_periodo = data
                    data_em_processamento = data
                    while data_em_processamento <= data_fim_periodo:
                        termino_atendimento = datetime.datetime.combine(data_em_processamento, inicio) + datetime.timedelta(minutes=duracao)
                        while termino_atendimento <= datetime.datetime.combine(data_em_processamento, termino):
                            if not HorarioAtendimento.objects.filter(
                                data=data_em_processamento,
                                hora_inicio=inicio,
                                hora_termino=termino_atendimento,
                                especialidade=especialidade_escolhida,
                                campus=campus_do_atendimento,
                                cadastrado_por_vinculo=request.user.get_vinculo(),
                            ).exists():
                                novo_agendamento = HorarioAtendimento()
                                novo_agendamento.data = data_em_processamento
                                novo_agendamento.hora_inicio = inicio
                                novo_agendamento.hora_termino = termino_atendimento
                                novo_agendamento.cadastrado_em = datetime.datetime.now()
                                novo_agendamento.especialidade = especialidade_escolhida
                                if eh_atendente:
                                    novo_agendamento.cadastrado_por_vinculo = form.cleaned_data.get('profissional').get_vinculo()
                                    novo_agendamento.campus = get_uo(form.cleaned_data.get('profissional'))
                                else:
                                    novo_agendamento.cadastrado_por_vinculo = request.user.get_vinculo()
                                    novo_agendamento.campus = campus_do_atendimento
                                novo_agendamento.save()
                            else:
                                HorarioAtendimento.objects.filter(
                                    data=data_em_processamento,
                                    hora_inicio=inicio,
                                    hora_termino=termino_atendimento,
                                    especialidade=especialidade_escolhida,
                                    campus=campus_do_atendimento,
                                    cadastrado_por_vinculo=request.user.get_vinculo(),
                                    cancelado=True,
                                ).update(cancelado=False, disponivel=True, vinculo_paciente=None)
                            inicio = termino_atendimento
                            termino_atendimento = termino_atendimento + datetime.timedelta(minutes=duracao)
                        data_em_processamento = data_em_processamento + datetime.timedelta(days=1)
                        inicio = form.cleaned_data.get('hora_inicio_1')
                        termino = form.cleaned_data.get('hora_termino_1')

                return httprr('/saude/adicionar_horario_atendimento_saude/', 'Horário(s) de atendimento(s) registrado(s) com sucesso.')
    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Aluno'])
def reservar_horario_atendimento(request, horario_id):
    title = 'Agendar Horário'
    horario = get_object_or_404(HorarioAtendimento, pk=horario_id)
    uo_ids = get_ids_uos(request.user)
    url_origem = request.META.get('HTTP_REFERER', '.')
    if not (horario.campus_id in uo_ids) or not horario.dentro_prazo_agendamento():
        raise PermissionDenied
    if horario.disponivel:
        vinculo = request.user.get_vinculo()
        if vinculo.eh_aluno() and not vinculo.relacionamento.situacao.ativo:
            return httprr(url_origem, 'Alunos com situação de matrícula inativa não podem agendar atendimento.', tag='error')
        if horario.especialidade == Especialidades.AVALIACAO_BIOMEDICA:
            especialidade = Especialidades(request.user)
            eh_profissional_saude = Especialidades.eh_profissional_saude(especialidade)
            eh_paciente = not (eh_profissional_saude and (horario.campus == get_uo(request.user)))
        else:
            eh_paciente = not (vinculo == horario.cadastrado_por_vinculo)
        form = PacienteAgendamentoForm(request.POST or None, url_origem=url_origem)
        if form.is_valid():
            vinculo = form.cleaned_data.get('pessoa')
            url_origem = form.cleaned_data.get('url_origem')
        if eh_paciente or form.is_valid():
            inicio_semana = horario.data - datetime.timedelta(horario.data.weekday())
            fim_semana = inicio_semana + datetime.timedelta(4)
            if HorarioAtendimento.objects.filter(
                especialidade=horario.especialidade, vinculo_paciente=vinculo, data__lte=fim_semana, data__gte=inicio_semana, cancelado=False, disponivel=False
            ).exists():
                return httprr(url_origem, 'Você já possui atendimento marcado esta semana.', tag='error')
            if BloqueioAtendimentoSaude.objects.filter(vinculo_profissional=horario.cadastrado_por_vinculo, vinculo_paciente=vinculo, data__gt=horario.data).exists():
                bloqueio = BloqueioAtendimentoSaude.objects.filter(vinculo_profissional=horario.cadastrado_por_vinculo, vinculo_paciente=vinculo, data__gt=horario.data)[0]
                return httprr(url_origem, 'Você só pode agendar atendimento com este profissional a partir de {}.'.format(bloqueio.data.strftime("%d/%m/%Y")), tag='error')
            horario.disponivel = False
            horario.vinculo_paciente = vinculo
            horario.save()
            titulo = '[SUAP] Agendamento de Atendimento de Saúde'
            texto = (
                '<h1>Saúde</h1>'
                '<h2>Agendamento de Atendimento de Saúde</h2>'
                '<p>Você possui um atendimento de saúde agendado. Data: {}, Horário: {} - {}. Especialidade: {}</p>'
                '<p>Procure o setor de Saúde do seu campus para mais informações. Em caso de consulta de tele-atendimento, fique atento às informações no seu e-mail acadêmico.</p>'.format(
                    horario.data.strftime("%d/%m/%Y"), horario.hora_inicio.strftime("%H:%M"), horario.hora_termino.strftime("%H:%M"), horario.especialidade
                )
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [horario.vinculo_paciente])
            return httprr(url_origem, 'Horário de atendimento agendado com sucesso.')
    else:
        return httprr(url_origem, 'Horário de atendimento já agendado.', tag='error')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Aluno', 'Atendente', 'Assistente Social'])
def cancelar_horario_atendimento(request, horario_id):
    horario = get_object_or_404(HorarioAtendimento, pk=horario_id)
    if horario.pode_cancelar(request.user):
        if request.user.get_vinculo() == horario.cadastrado_por_vinculo or request.user.groups.filter(name='Atendente').exists():
            if horario.vinculo_paciente:
                title = 'Justificativa do Cancelamento'
                form = JustificativaCancelamentoHorarioForm(request.POST or None, instance=horario)
                if form.is_valid():
                    o = form.save(False)
                    o.disponivel = False
                    o.cancelado = True
                    o.save()
                    titulo = '[SUAP] Cancelamento de Agendamento de Saúde'
                    texto = (
                        '<h1>Saúde</h1>'
                        '<h2>Cancelamento de Agendamento de Saúde</h2>'
                        '<p>Seu agendamento com o(a) {} foi cancelado pelo profissional responsável. Justificativa: {}</p>'
                        '<p>Procure o setor de Saúde do seu campus para mais informações.</p>'.format(horario.especialidade, horario.motivo_cancelamento)
                    )
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [horario.vinculo_paciente])
                    return httprr('/saude/agenda_atendimentos/', 'Horário de atendimento cancelado com sucesso.')
            else:
                horario.disponivel = False
                horario.cancelado = True
                horario.save()
                return httprr('/saude/agenda_atendimentos/', 'Horário de atendimento cancelado com sucesso.')

        else:
            horario.disponivel = True
            horario.vinculo_paciente = None
            horario.save()
            return httprr('/saude/agenda_atendimentos/', 'Horário de atendimento cancelado com sucesso.')

        return locals()

    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def bloquear_aluno_atendimento(request, horario_id):
    horario = get_object_or_404(HorarioAtendimento, pk=horario_id)
    if horario.pode_bloquear_aluno(request.user):
        bloqueado_ate = datetime.datetime.now().date() + datetime.timedelta(days=15)
        vinculo_paciente = horario.vinculo_paciente
        if not BloqueioAtendimentoSaude.objects.filter(vinculo_profissional=horario.cadastrado_por_vinculo, vinculo_paciente=vinculo_paciente, data=bloqueado_ate).exists():
            novo_bloqueio = BloqueioAtendimentoSaude()
            novo_bloqueio.vinculo_profissional = horario.cadastrado_por_vinculo
            novo_bloqueio.vinculo_paciente = vinculo_paciente
            novo_bloqueio.data = bloqueado_ate
            novo_bloqueio.save()

            titulo = '[SUAP] Atendimento de Saúde'
            texto = (
                '<h1>Saúde</h1>'
                '<h2>Bloqueio de Paciente</h2>'
                'Você não poderá realizar agendamentos para atendimentos de saúde até o dia {}. Procure o setor de saúde do seu campus para mais detalhes.</p>'.format(
                    bloqueado_ate.strftime("%d/%m/%Y")
                )
            )
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo_paciente])
            return httprr('/saude/agenda_atendimentos/', f'{novo_bloqueio.vinculo_paciente.pessoa.nome} está bloqueado(a) até o dia {format_(novo_bloqueio.data)}.')
        return httprr('/saude/agenda_atendimentos/', 'Aluno já bloqueado.')
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def desbloquear_aluno_atendimento(request, vinculo_paciente_id):
    vinculo_paciente = get_object_or_404(VinculoPessoa, pk=vinculo_paciente_id)
    if BloqueioAtendimentoSaude.objects.filter(vinculo_paciente=vinculo_paciente, data__gte=datetime.datetime.now().date()).exists():
        BloqueioAtendimentoSaude.objects.filter(vinculo_paciente=vinculo_paciente, data__gte=datetime.datetime.now().date()).update(
            data=datetime.datetime.now().date() + datetime.timedelta(days=-1)
        )
        titulo = '[SUAP] Atendimento de Saúde'
        texto = (
            '<h1>Saúde</h1>'
            '<h2>Desbloqueio de Paciente</h2>'
            'Você já pode realizar agendamentos para atendimentos de saúde. Procure o setor de saúde do seu campus para mais detalhes.</p>'
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo_paciente])
        return httprr('/saude/agenda_atendimentos/', f'{vinculo_paciente} está desbloqueado(a).')
    else:
        return httprr('/saude/agenda_atendimentos/', 'Aluno já está desbloqueado.')


@rtr()
@group_required(Especialidades.GRUPOS)
def adicionar_acao_educativa(request, meta_id):
    title = 'Adicionar Ação Educativa'
    meta = get_object_or_404(MetaAcaoEducativa, pk=meta_id)
    if meta.ativo:
        if not meta.pode_adicionar_meta():
            return httprr('/admin/saude/metaacaoeducativa/', 'Não é possível adicionar uma ação à uma meta de anos anteriores ao ano atual.', tag='error')

        form = AtividadeGrupoForm(request.POST or None, eh_acao_educativa=True)
        if form.is_valid():
            o = form.save(False)
            o.uo = get_uo(request.user)
            o.meta = meta
            o.save()
            return httprr('/admin/saude/metaacaoeducativa/', 'Ação cadastrada com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def adicionar_acao_educativa_sem_meta(request):
    title = 'Adicionar Ação Educativa'
    form = AtividadeGrupoForm(request.POST or None, eh_acao_educativa=True)
    if form.is_valid():
        o = form.save(False)
        o.uo = get_uo(request.user)
        o.save()
        return httprr('/admin/saude/metaacaoeducativa/', 'Ação cadastrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def visualizar_acoes_educativas(request, meta_id):
    title = 'Ações Educativas'
    meta = get_object_or_404(MetaAcaoEducativa, pk=meta_id)
    acoes = AtividadeGrupo.objects.filter(meta=meta)
    if not request.user.groups.filter(name='Coordenador de Saúde Sistêmico'):
        acoes = acoes.filter(uo=get_uo(request.user))

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def registrar_execucao_acao_educativa(request, atividadegrupo_id):
    title = 'Registrar Execução da Ação Educativa'
    atividade = get_object_or_404(AtividadeGrupo, pk=atividadegrupo_id)
    if not atividade.tema and (atividade.cadastrado_por and atividade.cadastrado_por == request.user or not atividade.cadastrado_por):
        form = AtividadeGrupoForm(request.POST or None, eh_acao_educativa=True, instance=atividade)
        if form.is_valid():
            form.save()
            return httprr(f'/saude/visualizar_acoes_educativas/{atividade.meta_id}/', 'Execução da ação registrada com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def visualizar_acao_educativa(request, atividadegrupo_id):
    atividade = get_object_or_404(AtividadeGrupo, pk=atividadegrupo_id)
    if (atividade.uo == get_uo(request.user)) or request.user.groups.filter(name='Coordenador de Saúde Sistêmico'):
        title = 'Visualizar Ação Educativa'
        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def visualizar_meta_acao_educativa(request, meta_id):
    meta = get_object_or_404(MetaAcaoEducativa, pk=meta_id)
    pode_adicionar_indicador = request.user.groups.filter(name='Coordenador de Saúde Sistêmico') and meta.ativo
    title = 'Visualizar Meta da Ação Educativa'
    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def cancelar_acao_educativa(request, atividadegrupo_id):
    atividade = get_object_or_404(AtividadeGrupo, pk=atividadegrupo_id)
    if (atividade.cadastrado_por and atividade.cadastrado_por == request.user) or not atividade.cadastrado_por:
        id_meta = atividade.meta_id
        atividade.delete()
        return httprr(f'/saude/visualizar_acoes_educativas/{id_meta}/', 'Ação cancelada com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('saude.view_atividadegrupo')
def lista_alunos(request):
    title = 'Lista de Alunos'
    form = ListaAlunosForm(request.GET or None)
    if form.is_valid():
        campus = form.cleaned_data.get('campus')
        curso = form.cleaned_data.get('curso')
        alergia_alimentos = form.cleaned_data.get('alergia_alimentos')
        alergia_medicamentos = form.cleaned_data.get('alergia_medicamentos')
        ver_nome = form.cleaned_data['ver_nome']
        ver_matricula = form.cleaned_data['ver_matricula']
        ver_curso = form.cleaned_data['ver_curso']
        ver_turma = form.cleaned_data['ver_turma']
        ver_rg = form.cleaned_data['ver_rg']
        ver_cpf = form.cleaned_data['ver_cpf']
        ver_alergia_alimentos = ver_alergia_medicamentos = False
        if alergia_alimentos:
            ver_alergia_alimentos = True

        if alergia_medicamentos:
            ver_alergia_medicamentos = True

        atendimentos = Atendimento.objects.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO, processosaudedoenca__isnull=False, aluno__isnull=False)

        if campus:
            atendimentos = atendimentos.filter(usuario_aberto__vinculo__setor__uo=campus)

        if curso:
            atendimentos = atendimentos.filter(aluno__curso_campus=curso)

        if alergia_alimentos:
            ids_verificados = list()
            for atendimento in atendimentos:
                if not atendimento.id in ids_verificados:
                    if ProcessoSaudeDoenca.objects.filter(atendimento=atendimento).order_by('-id')[0].alergia_alimentos:
                        ids_verificados.append(atendimento.id)

            atendimentos = atendimentos.filter(id__in=ids_verificados)
        if alergia_medicamentos:
            ids_verificados = list()
            for atendimento in atendimentos:
                if not atendimento.id in ids_verificados:
                    if ProcessoSaudeDoenca.objects.filter(atendimento=atendimento).order_by('-id')[0].alergia_medicamentos:
                        ids_verificados.append(atendimento.id)

            atendimentos = atendimentos.filter(id__in=ids_verificados).distinct()
        atendimentos = atendimentos.distinct()

        if 'xls' in request.GET:
            return tasks.lista_alunos_to_xls(atendimentos, ver_nome, ver_matricula, ver_curso, ver_turma, ver_rg, ver_cpf, ver_alergia_alimentos, ver_alergia_medicamentos)

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Assistente Social'])
def cancelar_horarios_atendimentos(request):
    if request.POST and request.POST.getlist('action')[0] == 'Cancelar Horários':
        ids = request.POST.getlist('registros')
        if ids:

            if HorarioAtendimento.objects.filter(id__in=ids, vinculo_paciente__isnull=False).exists():
                return httprr('/saude/informar_motivo_cancelamento_horario/?ids={}'.format(",".join(ids)), 'Informe a justificativa de cancelamento')
            else:
                for horario in HorarioAtendimento.objects.filter(id__in=ids):
                    horario.disponivel = False
                    horario.cancelado = True
                    horario.save()
                return httprr('/saude/agenda_atendimentos/', 'Horários de atendimentos cancelados com sucesso.')
        else:
            return httprr('/saude/agenda_atendimentos/', 'Nenhum horário de atendimento selecionado.', tag='error')
    else:
        raise PermissionDenied


@rtr()
@group_required(Especialidades.GRUPOS)
def adicionar_documento_prontuario(request, vinculo_id):
    vinculo = get_object_or_404(VinculoPessoa, id=vinculo_id)
    prontuario = Prontuario.get_prontuario(vinculo)
    title = f'Adicionar Documento - {prontuario.vinculo}'
    especialidade = Especialidades(request.user)
    eh_medico_ou_odontologo = especialidade.is_medico() or especialidade.is_odontologo()
    form = TipoDocumentoForm(request.POST or None, eh_medico_ou_odontologo=eh_medico_ou_odontologo)
    if form.is_valid():
        return httprr('/saude/preencher_documento_prontuario/{}/{}/'.format(vinculo_id, form.cleaned_data.get('tipo')), 'Preencha os dados do documento.')
    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def informar_motivo_cancelamento_horario(request):
    title = 'Justificativa do Cancelamento'
    url_origem = request.META.get('HTTP_REFERER', '.')
    if request.POST:
        form = JustificativaCancelamentoHorariosForm(request.POST or None)
        if form.is_valid():
            motivo_cancelamento = form.cleaned_data.get('motivo_cancelamento')
            ids = request.GET.get('ids').split(',')
            for item in ids:
                horario = get_object_or_404(HorarioAtendimento, pk=item)
                if horario.vinculo_paciente:
                    title = 'Justificativa do Cancelamento'
                    horario.disponivel = False
                    horario.cancelado = True
                    horario.motivo_cancelamento = motivo_cancelamento
                    horario.save()
                    titulo = '[SUAP] Cancelamento de Agendamento de Saúde'
                    texto = (
                        '<h1>Saúde</h1>'
                        '<h2>Cancelamento de Agendamento de Saúde</h2>'
                        '<p>Seu agendamento com o(a) {} foi cancelado pelo profissional responsável. Justificativa: {}</p>'
                        '<p>Procure o setor de Saúde do seu campus para mais informações.</p>'.format(horario.especialidade, motivo_cancelamento)
                    )
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [horario.vinculo_paciente])
                else:
                    horario.disponivel = False
                    horario.cancelado = True
                    horario.motivo_cancelamento = motivo_cancelamento
                    horario.save()

            return httprr('/saude/agenda_atendimentos/', 'Horários de atendimentos cancelados com sucesso.')

    else:
        form = JustificativaCancelamentoHorariosForm(request.POST or None)
    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def preencher_documento_prontuario(request, vinculo_id, tipo):
    especialidade = Especialidades(request.user)
    eh_medico_ou_odontologo = especialidade.is_medico() or especialidade.is_odontologo()
    if not eh_medico_ou_odontologo and tipo != 1:
        raise PermissionDenied()
    vinculo = get_object_or_404(VinculoPessoa, id=vinculo_id)
    prontuario = Prontuario.get_prontuario(vinculo)
    descricao_tipo_documento = DocumentoProntuario.TIPO_DOCUMENTO_CHOICES[int(tipo)][1]
    title = f'Preencher {descricao_tipo_documento} - {prontuario.vinculo}'
    form = PreencherDocumentoForm(request.POST or None, tipo=tipo, nome_paciente=prontuario.vinculo.pessoa.nome)
    if 'visualizar' in request.POST:
        return locals()
    if form.is_valid():
        o = form.save(False)
        o.prontuario = prontuario
        o.tipo = descricao_tipo_documento
        o.cadastrado_por_vinculo = request.user.get_vinculo()
        o.save()
        return httprr(f'/saude/prontuario/{vinculo_id}/?tab=aba_documentos', 'Documento cadastrado com sucesso.')
    return locals()


@documento(enumerar_paginas=False, validade=360)
@rtr()
@group_required(Especialidades.GRUPOS)
def imprimir_documento_prontuario(request, documento_id):
    documento = get_object_or_404(DocumentoProntuario, pk=documento_id)
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    hoje = documento.data
    campus = get_uo(documento.cadastrado_por_vinculo.user)
    if documento.tipo == DocumentoProntuario.RECEITUARIO:
        subtitulo = 'Serviço de Saúde'
    else:
        subtitulo = 'Setor de Saúde'
    return locals()


@documento(enumerar_paginas=False, validade=360)
@rtr('imprimir_documento_prontuario.html')
@group_required(Especialidades.GRUPOS)
def previsualizar_documento_prontuario(request):
    documento = DocumentoProntuario()
    documento.texto = request.POST.get('texto')
    documento.data = request.POST.get('data')
    tipo = request.POST.get('tipo')
    documento.tipo = DocumentoProntuario.TIPO_DOCUMENTO_CHOICES[int(tipo)][1]
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    hoje = documento.data
    campus = get_uo(request.user)
    if documento.tipo == DocumentoProntuario.RECEITUARIO:
        subtitulo = 'Serviço de Saúde'
    else:
        subtitulo = 'Setor de Saúde'
    return locals()


@rtr()
@group_required(Especialidades.GRUPOS + ['Aluno', 'Atendente'])
def ver_calendario_agendamento(request):
    title = 'Calendário de Agendamento'
    if request.user.eh_aluno and not request.user.get_relacionamento().situacao.ativo:
        return httprr('/', 'Apenas alunos com situação ativa podem agendar atendimentos.', tag='error')
    qs_solicitacoes = HorarioAtendimento.objects.all().order_by('data')
    cal_meses = []
    uo = ''
    uo_ids = get_ids_uos(request.user)
    if request.GET.get('campus'):
        uo = get_object_or_404(UnidadeOrganizacional, pk=request.GET.get('campus'))
        qs_solicitacoes = HorarioAtendimento.objects.filter(campus=uo)
    else:
        qs_solicitacoes = HorarioAtendimento.objects.filter(campus__in=uo_ids).order_by('data', 'hora_termino')

    data_agora = datetime.datetime.now()
    ano_corrente = data_agora.year
    mes_corrente = data_agora.month
    especialidade = Especialidades(request.user)
    pode_cadastrar_horario = Especialidades.eh_profissional_saude(especialidade)

    if request.GET.get('meus_agendamentos'):
        eh_aluno = Aluno.objects.filter(pessoa_fisica=request.user.pessoafisica, situacao__ativo=True).exists()

        if pode_cadastrar_horario:
            qs_solicitacoes = qs_solicitacoes.filter(cadastrado_por_vinculo=request.user.get_vinculo())
        elif eh_aluno:
            qs_solicitacoes = qs_solicitacoes.filter(vinculo_paciente=request.user.get_vinculo())

    if request.GET.get('disponivel'):
        qs_solicitacoes = qs_solicitacoes.filter(disponivel=True)

    if request.GET.get('data_inicio'):
        try:
            data = datetime.datetime.strptime(request.GET.get('data_inicio'), '%Y-%m-%d')
        except Exception:
            return httprr('/saude/ver_calendario_agendamento/', 'Data inicial inválida.', tag='error')
        if data and data.year < 1900:
            return httprr('/saude/ver_calendario_agendamento/', 'O ano precisa ser maior do que 1900.', tag='error')

        qs_solicitacoes = qs_solicitacoes.filter(data__gte=data)
        ano_corrente = data.year
        mes_corrente = data.month

    if request.GET.get('data_final'):
        try:
            data_fim_informada = datetime.datetime.strptime(request.GET.get('data_final'), '%Y-%m-%d')
        except Exception:
            return httprr('/saude/ver_calendario_agendamento/', 'Data final inválida.', tag='error')
        if data_fim_informada and data_fim_informada.year < 1900:
            return httprr('/saude/ver_calendario_agendamento/', 'O ano precisa ser maior do que 1900.', tag='error')
        qs_solicitacoes = qs_solicitacoes.filter(data__lte=data_fim_informada)

    if request.GET.get('especialidade') and not (request.GET.get('especialidade') == Especialidades.TODOS):
        qs_solicitacoes = qs_solicitacoes.filter(especialidade=request.GET.get('especialidade'))

    if qs_solicitacoes.exists():
        data_fim = qs_solicitacoes.latest('data').data
        if (data_fim.year == ano_corrente and data_fim.month >= mes_corrente) or (data_fim.year > ano_corrente):
            ultimo_ano = data_fim.year
            ultimo_mes = data_fim.month
            cal = CalendarioPlus()
            cal.mostrar_mes_e_ano = True
            cal.destacar_hoje = False
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
                                if not solicitacao.cancelado and not solicitacao.vinculo_paciente and solicitacao.disponivel:
                                    css = 'success'
                                elif not solicitacao.cancelado and solicitacao.vinculo_paciente:
                                    css = 'alert'
                                else:
                                    css = 'error'
                                nome_do_paciente = '-'
                                if solicitacao.vinculo_paciente and (pode_cadastrar_horario or solicitacao.vinculo_paciente == request.user.get_vinculo()):
                                    nome_do_paciente = solicitacao.vinculo_paciente.pessoa.nome
                                horario = '{} - {}'.format(solicitacao.hora_inicio.strftime("%H:%M"), solicitacao.hora_termino.strftime("%H:%M"))
                                descricao = '<strong>{}</strong><br><b>Especialidade:</b> {}<br><b>Profissional:</b> {}<br><b>Paciente:</b> {}'.format(
                                    horario, solicitacao.especialidade, solicitacao.cadastrado_por_vinculo.pessoa.nome, nome_do_paciente
                                )

                                cal.adicionar_evento_calendario(agenda_data_inicio, agenda_data_fim, descricao, css)
                    cal_meses.append(cal.formato_mes(ano, mes))
                    # -------------------
                mes = 1

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def excluir_documento_prontuario(request, documento_id):
    documento = get_object_or_404(DocumentoProntuario, pk=documento_id)
    if documento.cadastrado_por_vinculo == request.user.get_vinculo():
        prontuario = documento.prontuario
        documento.delete()
        return httprr(f'/saude/prontuario/{prontuario.vinculo_id}/?tab=aba_documentos', 'Documento excluído com sucesso.')

    else:
        raise PermissionDenied


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def adicionar_cartao_vacinal(request, vinculo_id):
    vinculo = get_object_or_404(VinculoPessoa, id=vinculo_id)
    prontuario = Prontuario.get_prontuario(vinculo)
    title = f'Adicionar Cartão Vacinal - {vinculo}'
    form = AdicionarCartaoVacinalForm(request.POST or None, request.FILES or None, instance=prontuario)
    if form.is_valid():
        with transaction.atomic():
            o = form.save(False)
            o.cadastrado_por_vinculo = request.user.get_vinculo()
            o.cadastrado_em = datetime.datetime.now()
            o.save()
            novo_registro = HistoricoCartaoVacinal()
            novo_registro.prontuario = prontuario
            novo_registro.vinculo = request.user.get_vinculo()
            novo_registro.cadastrado_em = datetime.datetime.now()
            novo_registro.save()
        return httprr(f'/saude/prontuario/{vinculo.id}/?tab=aba_cartao_vacinal', 'Cartão vacinal cadastrado com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.GRUPOS)
def atendimento_fisioterapia(request, atendimento_id):
    title = 'Atendimento de Fisioterapia'
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id, tipo=TipoAtendimento.FISIOTERAPIA)
    pode_editar = (request.user == atendimento.usuario_aberto) and atendimento.situacao == SituacaoAtendimento.ABERTO

    especialidade = Especialidades(request.user)

    atendimento_fisioterapia = AtendimentoFisioterapia.objects.filter(atendimento=atendimento)
    atendimento_fisioterapia_responsavel = False
    if atendimento_fisioterapia.exists():
        atendimento_fisioterapia = atendimento_fisioterapia[0]
        atendimento_fisioterapia_responsavel = atendimento_fisioterapia.get_responsavel()

    cadastrou_antecedentes = False
    cadastrou_processosaudedoenca = False

    antecedentesfamiliares = AntecedentesFamiliares.objects.filter(atendimento=atendimento)
    antecedentesfamiliares_titulo = 'Antecedentes'
    antecedentesfamiliares_count = antecedentesfamiliares.count()
    if antecedentesfamiliares.exists():
        cadastrou_antecedentes = True
        antecedentesfamiliares = antecedentesfamiliares.latest('id')
        antecedentesfamiliares_responsavel = antecedentesfamiliares.get_responsavel()

    processosaudedoenca = ProcessoSaudeDoenca.objects.filter(atendimento=atendimento)
    processosaudedoenca_titulo = 'Processo Saúde-Doença'
    processosaudedoenca_count = processosaudedoenca.count()
    if processosaudedoenca.exists():
        cadastrou_processosaudedoenca = True
        processosaudedoenca = processosaudedoenca.latest('id')
        processosaudedoenca_responsavel = processosaudedoenca.get_responsavel()

    aba_antecedentes_preenchida = cadastrou_antecedentes or cadastrou_processosaudedoenca

    return locals()


@rtr()
@group_required(Especialidades.FISIOTERAPEUTA)
def adicionar_anamnese_fisioterapia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Anamnese - {atendimento.get_vinculo()}'
    obj = get_object_or_404(AtendimentoFisioterapia, atendimento=atendimento)

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = AnamneseFisioterapiaForm(request.POST or None, instance=obj, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_fisioterapia/{atendimento.id}/?tab=aba_anamnese', 'Anamnese registrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.FISIOTERAPEUTA)
def adicionar_hipotese_fisioterapia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Hipótese Diagnóstica - {atendimento.get_vinculo()}'
    obj = get_object_or_404(AtendimentoFisioterapia, atendimento=atendimento)

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = HipoteseFisioterapiaForm(request.POST or None, instance=obj, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_fisioterapia/{atendimento.id}/?tab=aba_hipotesediagnostica', 'Hipótese Diagnóstica registrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.FISIOTERAPEUTA)
def adicionar_conduta_fisioterapia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Adicionar Conduta de Fisioterapia - {atendimento.get_vinculo()}'
    obj = get_object_or_404(AtendimentoFisioterapia, atendimento=atendimento)

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = CondutaFisioterapiaForm(request.POST or None, instance=obj, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_fisioterapia/{atendimento.id}/?tab=aba_hipotesediagnostica', 'Conduta de Fisioterapia registrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.FISIOTERAPEUTA)
def adicionar_intervencao_fisioterapia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Intervenção de Fisioterapia - {atendimento.get_vinculo()}'

    condutas_medicas = CondutaMedica.objects.filter(atendimento=atendimento, encaminhado_fisioterapia=True, atendido_fisioterapia=False)

    form = IntervencaoFisioterapiaForm(request.POST or None, request=request, atendimento=atendimento)

    if form.is_valid():
        obj = IntervencaoFisioterapia()
        obj.profissional = request.user
        obj.data_cadastro = datetime.datetime.now()
        obj.atendimento = atendimento
        obj.conduta_medica = form.cleaned_data.get('conduta_medica')
        obj.descricao = form.cleaned_data.get('descricao')
        obj.save()

        if form.cleaned_data.get('conduta_medica'):
            CondutaMedica.objects.filter(id=form.cleaned_data.get('conduta_medica').id).update(atendido_fisioterapia=True)

        AtendimentoEspecialidade.cadastrar(atendimento, request)
        return httprr(f'/saude/atendimento_medico_enfermagem/{atendimento.id}/?tab=aba_intervencaofisioterapia', 'Intervenção de fisioterapia registrada com sucesso.')

    return locals()


@rtr()
@group_required(Especialidades.FISIOTERAPEUTA)
def adicionar_retorno_fisioterapia(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    title = f'Descrição da Evolução - {atendimento.get_vinculo()}'
    obj = get_object_or_404(AtendimentoFisioterapia, atendimento=atendimento)

    obj.profissional = request.user
    obj.data_cadastro = datetime.datetime.now()
    obj.atendimento = atendimento

    form = RetornoFisioterapiaForm(request.POST or None, instance=obj, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/saude/atendimento_fisioterapia/{atendimento.id}/?tab=aba_retorno', 'Evolução registrada com sucesso.')

    return locals()


@rtr()
@group_required(['Coordenador de Saúde Sistêmico'])
def reabrir_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)

    atendimento.data_reaberto = datetime.datetime.today()
    atendimento.situacao = SituacaoAtendimento.REABERTO
    atendimento.usuario_reaberto = request.user
    atendimento.save()
    msg_sucesso = 'Atendimento reaberto com sucesso.'
    if atendimento.tipo == TipoAtendimento.AVALIACAO_BIOMEDICA:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_avaliacao_biomedica", msg_sucesso)
    elif atendimento.tipo == TipoAtendimento.ENFERMAGEM_MEDICO:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_medico_enfermagem", msg_sucesso)
    elif atendimento.tipo == TipoAtendimento.ODONTOLOGICO:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_odontologico", msg_sucesso)
    elif atendimento.tipo == TipoAtendimento.PSICOLOGICO:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_psicologico", msg_sucesso)
    elif atendimento.tipo == TipoAtendimento.NUTRICIONAL:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_nutricional", msg_sucesso)
    elif atendimento.tipo == TipoAtendimento.FISIOTERAPIA:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_fisioterapia", msg_sucesso)
    elif atendimento.tipo == TipoAtendimento.MULTIDISCIPLINAR:
        return httprr(f"/saude/prontuario/{atendimento.prontuario.vinculo_id}/?tab=aba_atendimento_multidisciplinar", msg_sucesso)

    return locals()


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def cartao_vacinal(request):
    vinculo_logado = request.user.get_vinculo()
    prontuario = Prontuario.get_prontuario(vinculo_logado)
    title = f'Cartão Vacinal - {vinculo_logado}'
    pode_adicionar_cartao = not prontuario.cartao_vacinal or (HistoricoCartaoVacinal.objects.filter(prontuario=prontuario).exists() and HistoricoCartaoVacinal.objects.filter(prontuario=prontuario).latest('id').vinculo == vinculo_logado)
    vacinas = CartaoVacinal.objects.filter(prontuario=prontuario).order_by('id')
    grupo_vacina = Vacina.objects.filter(id__in=prontuario.vacinas.all().distinct()).order_by('-id')
    grupos = []
    for grupo in grupo_vacina:
        lista = []
        for registro_vacina in vacinas:
            if registro_vacina.vacina_id == grupo.id:
                lista.append(registro_vacina)
        grupos.append(lista)

    return locals()


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def adicionar_cartao_vacinal_aluno(request):
    vinculo_logado = request.user.get_vinculo()
    prontuario = Prontuario.get_prontuario(vinculo_logado)
    title = f'Adicionar Cartão Vacinal - {vinculo_logado}'
    if not prontuario.cartao_vacinal or (HistoricoCartaoVacinal.objects.filter(prontuario=prontuario).exists() and HistoricoCartaoVacinal.objects.filter(prontuario=prontuario).latest('id').vinculo == vinculo_logado):
        form = AdicionarCartaoVacinalForm(request.POST or None, request.FILES or None, instance=prontuario)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                novo_registro = HistoricoCartaoVacinal()
                novo_registro.prontuario = prontuario
                novo_registro.vinculo = vinculo_logado
                novo_registro.cadastrado_em = datetime.datetime.now()
                novo_registro.save()
            return httprr('/saude/cartao_vacinal/', 'Cartão vacinal cadastrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(['Coordenador de Saúde Sistêmico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar de Enfermagem', 'Médico'])
def historico_cartao_vacinal(request, vinculo_id):
    vinculo = get_object_or_404(VinculoPessoa, id=vinculo_id)
    prontuario = Prontuario.get_prontuario(vinculo)
    title = f'Histórico do Cartão Vacinal - {vinculo}'
    historico = HistoricoCartaoVacinal.objects.filter(prontuario=prontuario).order_by('-id')
    return locals()


@rtr(two_factor_authentication=True)
@group_required(Especialidades.GRUPOS)
def enviar_mensagem_aluno(request, vinculo_id, atendimento_id):
    vinculo = get_object_or_404(VinculoPessoa, id=vinculo_id)
    atendimento = get_object_or_404(Atendimento, pk=atendimento_id)
    if atendimento.is_aberto():
        title = f'Enviar Mensagem - {vinculo}'
        form = EnviarMensagemForm(request.POST or None)
        if form.is_valid():
            titulo = '[SUAP] {}'.format(form.cleaned_data.get('titulo'))
            mensagem = form.cleaned_data.get('mensagem')
            enviada_por = '{}'
            texto = '<h1>Saúde</h1>' '<h2>Avaliação Biomédica</h2>' '{}</p><p>Mensagem enviada por: {}</p>'.format(mensagem, request.user.get_vinculo().__str__())
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo], categoria='Saúde: Avaliação Biomédica', salvar_no_banco=False)
            return httprr(f"/saude/avaliacao_biomedica/{atendimento_id}/", 'Mensagem enviada com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def passaporte_vacinacao_covid(request):
    vinculo = request.user.get_vinculo()
    form = None
    title = 'Passaporte Vacinal da COVID'
    obj = None
    tem_teste = False
    if PassaporteVacinalCovid.objects.filter(vinculo=vinculo).exists():
        obj = get_object_or_404(PassaporteVacinalCovid, vinculo=vinculo)
        tem_teste = obj.resultadotestecovid_set.exists()
        cpf = obj.cpf
    else:
        if request.user.eh_aluno:
            cpf = vinculo.relacionamento.pessoa_fisica.cpf
        else:
            cpf = vinculo.relacionamento.cpf
    pode_cadastrar_teste = obj and obj.termo_aceito_em and not obj.atestado_medico and not obj.cartao_vacinal
    pode_adicionar_cartao_vacinal = not obj or obj.situacao_passaporte == PassaporteVacinalCovid.INVALIDO
    if (obj and obj.situacao_declaracao in (PassaporteVacinalCovid.AGUARDANDO_AUTODECLARACAO, PassaporteVacinalCovid.AGUARDANDO_VALIDACAO, PassaporteVacinalCovid.INDEFERIDA)) or not obj:
        form = PassaporteVacinalCovidForm(request.POST or None, request.FILES or None, instance=obj, request=request)
        if form.is_valid():
            o = form.save(False)
            o.uo = get_uo(request.user)
            o.cpf = cpf.replace('.', '').replace('-', '')
            o.recebeu_alguma_dose = False
            o.vinculo = vinculo
            if form.cleaned_data.get('tem_atestado_medico') == 'sim':
                o.possui_atestado_medico = True
                o.termo_aceito_em = None
            else:
                o.possui_atestado_medico = False
                o.atestado_medico = None
            o.atualizado_em = datetime.datetime.now()
            if form.cleaned_data.get('aceite_termo'):
                o.termo_aceito_em = datetime.datetime.now()
            o.situacao_declaracao = PassaporteVacinalCovid.AGUARDANDO_VALIDACAO
            o.save()
            return httprr("/saude/passaporte_vacinacao_covid/", 'Autodeclaração preenchida com sucesso.')
    return locals()


@transaction.atomic()
@rtr()
@permission_required('saude.view_passaportevacinalcovid')
def deferir_passaporte_vacinal(request, declaracao_id):
    url = request.META.get('HTTP_REFERER', '.')
    obj = get_object_or_404(PassaporteVacinalCovid, pk=declaracao_id)
    if pode_validar_passaporte(request, obj) and not obj.esquema_completo:
        obj.situacao_declaracao = PassaporteVacinalCovid.DEFERIDA
        if obj.possui_atestado_medico or obj.recebeu_alguma_dose or obj.cartao_vacinal:
            obj.situacao_passaporte = PassaporteVacinalCovid.VALIDO
        else:
            if obj.situacao_passaporte != PassaporteVacinalCovid.VALIDO:
                obj.situacao_passaporte = PassaporteVacinalCovid.INVALIDO
        obj.avaliada_por = request.user.get_vinculo()
        obj.avaliada_em = datetime.datetime.now()
        obj.justificativa_indeferimento = None
        obj.save()
        HistoricoValidacaoPassaporte.objects.create(passaporte=obj, possui_atestado_medico=obj.possui_atestado_medico, termo_aceito_em=obj.termo_aceito_em, avaliado_por=request.user.get_vinculo(), situacao_passaporte=obj.situacao_passaporte, situacao_declaracao=obj.situacao_declaracao)
        titulo = '[SUAP] Saúde - Passaporte Vacinal da COVID'
        texto = '<h1>Saúde</h1>' '<h2>Passaporte Vacinal da COVID</h2><p>Sua declaração foi {}.</p><p>Acesse o SUAP para mais detalhes.</p>'.format(obj.situacao_declaracao)
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obj.vinculo], categoria='Saúde: Passaporte Vacinal', salvar_no_banco=True)
        return httprr(url, 'Passaporte vacinal avaliado com sucesso.')

    else:
        raise PermissionDenied


@transaction.atomic()
@rtr()
@permission_required('saude.view_passaportevacinalcovid')
def indeferir_passaporte_vacinal(request, declaracao_id):
    url = request.META.get('HTTP_REFERER', '.')
    obj = get_object_or_404(PassaporteVacinalCovid, pk=declaracao_id)
    if pode_validar_passaporte(request, obj) and not obj.esquema_completo:
        title = f'Indeferir Declaração - {obj}'
        form = JustificativaIndeferirPassaporteForm(request.POST or None, url_origem=url)
        if form.is_valid():
            obj.situacao_declaracao = PassaporteVacinalCovid.INDEFERIDA
            obj.situacao_passaporte = PassaporteVacinalCovid.INVALIDO
            obj.avaliada_por = request.user.get_vinculo()
            obj.avaliada_em = datetime.datetime.now()
            obj.justificativa_indeferimento = form.cleaned_data.get('justificativa')
            obj.save()
            HistoricoValidacaoPassaporte.objects.create(justificativa_indeferimento=form.cleaned_data.get('justificativa'), possui_atestado_medico=obj.possui_atestado_medico, termo_aceito_em=obj.termo_aceito_em, passaporte=obj, avaliado_por=request.user.get_vinculo(), situacao_passaporte=obj.situacao_passaporte, situacao_declaracao=obj.situacao_declaracao)
            titulo = '[SUAP] Saúde - Passaporte Vacinal da COVID'
            texto = '<h1>Saúde</h1>' '<h2>Passaporte Vacinal da COVID</h2><p>Sua declaração foi {}.</p><p>Acesse o SUAP para mais detalhes.</p>'.format(obj.situacao_declaracao)
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [obj.vinculo], categoria='Saúde: Passaporte Vacinal', salvar_no_banco=True)
            return httprr(form.cleaned_data.get('url_origem'), 'Passaporte vacinal avaliado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('saude.pode_ver_todos_passaportes, saude.pode_ver_passaportes_do_campus, saude.pode_ver_passaportes_dos_prestadores_do_campus, saude.pode_ver_passaportes_dos_alunos_do_curso')
def relatorio_passaporte_vacinal(request):
    title = 'Relatório de Passaporte Vacinal de COVID'
    campi_consulta = []
    campi_consulta.append(get_uo(request.user).id)
    if request.user.has_perm('saude.pode_ver_todos_passaportes'):
        registros = PassaporteVacinalCovid.objects.all().order_by('vinculo__pessoa__nome')
        todos_campi = True
    elif request.user.has_perm('saude.pode_ver_passaportes_do_campus'):
        eh_validador_intercampi = ValidadorIntercampi.objects.filter(vinculo=request.user.get_vinculo(),
                                                                     ativo=True)
        if eh_validador_intercampi.exists():
            campi_consulta += eh_validador_intercampi.values_list('campi', flat=True)
        registros = PassaporteVacinalCovid.objects.filter(uo__in=campi_consulta).order_by('vinculo__pessoa__nome')
        todos_campi = False
    elif request.user.has_perm('saude.pode_ver_passaportes_dos_prestadores_do_campus'):
        prestadores = PrestadorServico.objects.filter(setor__uo=get_uo(request.user), ativo=True, cpf__isnull=False,
                                                      ocupacaoprestador__isnull=False)
        registros = PassaporteVacinalCovid.objects.filter(vinculo__in=prestadores.values_list('vinculos', flat=True), uo=get_uo(request.user)).order_by('vinculo__pessoa__nome')
        todos_campi = False
    if request.user.has_perm('saude.pode_ver_passaportes_dos_alunos_do_curso'):
        cursos = CursoCampus.objects.filter(
            coordenador=request.user.get_relacionamento().funcionario) | CursoCampus.objects.filter(
            coordenador_2=request.user.get_relacionamento().funcionario)
        alunos = Aluno.ativos.filter(curso_campus__in=cursos.values_list('id', flat=True))
        if not request.user.has_perm('saude.pode_ver_passaportes_dos_prestadores_do_campus') and not request.user.has_perm('saude.pode_ver_todos_passaportes') and not request.user.has_perm('saude.pode_ver_passaportes_do_campus'):
            registros = PassaporteVacinalCovid.objects.filter(vinculo__in=alunos.values_list('vinculos', flat=True), uo=get_uo(request.user)).order_by('vinculo__pessoa__nome')
        else:
            registros = registros | PassaporteVacinalCovid.objects.filter(vinculo__in=alunos.values_list('vinculos', flat=True), uo=get_uo(request.user)).order_by('vinculo__pessoa__nome')
        todos_campi = False

    form = RelatorioPassaporteCovidForm(request.GET or None, todos_campi=todos_campi, request=request, busca_nome=True, campi_consulta=campi_consulta)
    if form.is_valid():
        nome = form.cleaned_data.get('nome')
        situacao = form.cleaned_data.get('situacao')
        categoria = form.cleaned_data.get('categoria')
        uo = form.cleaned_data.get('uo')
        curso = form.cleaned_data.get('curso')
        turma = form.cleaned_data.get('turma')
        faixa_etaria = form.cleaned_data.get('faixa_etaria')
        situacao_declaracao = form.cleaned_data.get('situacao_declaracao')

        if nome:
            registros = registros.filter(Q(vinculo__pessoa__nome__icontains=nome) | Q(vinculo__user__username__icontains=nome))

        if situacao:
            registros = registros.filter(situacao_passaporte=situacao)

        if situacao_declaracao:
            registros = registros.filter(situacao_declaracao=situacao_declaracao)

        if categoria:
            if categoria == '1':
                registros = registros.filter(vinculo__user__eh_aluno=True)
            elif categoria == '2':
                registros = registros.filter(vinculo__user__eh_servidor=True)
            elif categoria == '3':
                registros = registros.filter(vinculo__user__eh_prestador=True)
            elif categoria == '4':
                registros = registros.filter(vinculo__user__eh_servidor=True, vinculo__in=Servidor.objects.ativos().filter(eh_docente=True).values_list('vinculos', flat=True))
            elif categoria == '5':
                registros = registros.filter(vinculo__user__eh_servidor=True, vinculo__in=Servidor.objects.ativos().filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True))

        if uo:
            registros = registros.filter(uo=uo)

        if curso:
            registros = registros.filter(vinculo__in=Aluno.objects.filter(curso_campus=curso).values_list('vinculos', flat=True))

        if turma:
            alunos = turma.get_alunos_matriculados()
            registros = registros.filter(vinculo__in=alunos.values_list('aluno__vinculos', flat=True))

        if faixa_etaria:
            dezoito_anos = datetime.date.today() + relativedelta(years=-18)
            sessenta_anos = datetime.date.today() + relativedelta(years=-60)
            if faixa_etaria == '1':
                registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__gt=dezoito_anos)
            elif faixa_etaria == '2':
                registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__lte=dezoito_anos, vinculo__pessoa__pessoafisica__nascimento_data__gt=sessenta_anos)
            elif faixa_etaria == '3':
                registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__lte=sessenta_anos)

    return locals()


@rtr()
@group_required('Chefe de Setor')
def relatorio_passaporte_vacinal_chefia(request):
    historico_funcao = request.user.get_relacionamento().historico_funcao().filter(
        funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False)
    if historico_funcao.exists():
        setor = historico_funcao.latest('id').setor_suap
        title = f'Relatório de Passaporte Vacinal de COVID - Servidores sob sua chefia ({setor})'
        servidores_do_setor = Servidor.objects.ativos().filter(setor__in=setor.descendentes)

        registros = PassaporteVacinalCovid.objects.filter(vinculo__in=servidores_do_setor.values_list('vinculos', flat=True)).order_by('vinculo__pessoa__nome')
        form = RelatorioPassaporteCovidChefiaForm(request.GET or None)
        if form.is_valid():
            nome = form.cleaned_data.get('nome')
            situacao = form.cleaned_data.get('situacao')
            categoria = form.cleaned_data.get('categoria')
            uo = form.cleaned_data.get('uo')
            curso = form.cleaned_data.get('curso')
            turma = form.cleaned_data.get('turma')
            faixa_etaria = form.cleaned_data.get('faixa_etaria')
            situacao_declaracao = form.cleaned_data.get('situacao_declaracao')
            registrou_frequencia = form.cleaned_data.get('registrou_frequencia')

            if nome:
                registros = registros.filter(
                    Q(vinculo__pessoa__nome__icontains=nome) | Q(vinculo__user__username__icontains=nome))

            if registrou_frequencia:
                data_inicio_checagem_ponto = Configuracao.get_valor_por_chave('saude', 'data_checagem_ponto')
                if data_inicio_checagem_ponto:
                    registros = registros.filter(vinculo__in=Frequencia.objects.filter(vinculo__in=servidores_do_setor.values_list('vinculo', flat=True), horario__gt=data_inicio_checagem_ponto).values_list('vinculo', flat=True))

            if situacao:
                registros = registros.filter(situacao_passaporte=situacao)

            if situacao_declaracao:
                registros = registros.filter(situacao_declaracao=situacao_declaracao)

            if categoria:
                if categoria == '1':
                    registros = registros.filter(vinculo__user__eh_aluno=True)
                elif categoria == '2':
                    registros = registros.filter(vinculo__user__eh_servidor=True)
                elif categoria == '3':
                    registros = registros.filter(vinculo__user__eh_prestador=True)
                elif categoria == '4':
                    registros = registros.filter(vinculo__user__eh_servidor=True, vinculo__in=Servidor.objects.ativos().filter(eh_docente=True).values_list('vinculos', flat=True))
                elif categoria == '5':
                    registros = registros.filter(vinculo__user__eh_servidor=True, vinculo__in=Servidor.objects.ativos().filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True))

            if uo:
                registros = registros.filter(uo=uo)

            if curso:
                registros = registros.filter(vinculo__in=Aluno.objects.filter(curso_campus=curso).values_list('vinculos', flat=True))

            if turma:
                alunos = turma.get_alunos_matriculados()
                registros = registros.filter(vinculo__in=alunos.values_list('aluno__vinculos', flat=True))

            if faixa_etaria:
                dezoito_anos = datetime.date.today() + relativedelta(years=-18)
                sessenta_anos = datetime.date.today() + relativedelta(years=-60)
                if faixa_etaria == '1':
                    registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__gt=dezoito_anos)
                elif faixa_etaria == '2':
                    registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__lte=dezoito_anos, vinculo__pessoa__pessoafisica__nascimento_data__gt=sessenta_anos)
                elif faixa_etaria == '3':
                    registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__lte=sessenta_anos)

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('saude.pode_ver_todos_passaportes, saude.pode_ver_passaportes_do_campus')
def relatorio_vacinacao_covid(request):
    title = 'Relatório de Vacinação da COVID'
    campi_consulta = []
    campi_consulta.append(get_uo(request.user).id)
    if request.user.has_perm('saude.pode_ver_todos_passaportes'):
        registros = PassaporteVacinalCovid.objects.all()
        todos_campi = True
    else:
        eh_validador_intercampi = ValidadorIntercampi.objects.filter(vinculo=request.user.get_vinculo(),
                                                                     ativo=True)
        if eh_validador_intercampi.exists():
            campi_consulta += eh_validador_intercampi.values_list('campi', flat=True)
        registros = PassaporteVacinalCovid.objects.filter(uo__in=campi_consulta).order_by('vinculo__pessoa__nome')
        todos_campi = False
    form = RelatorioPassaporteCovidForm(request.GET or None, todos_campi=todos_campi, request=request, busca_nome=False, campi_consulta=campi_consulta)
    if form.is_valid():
        situacao = form.cleaned_data.get('situacao')
        categoria = form.cleaned_data.get('categoria')
        uo = form.cleaned_data.get('uo')
        curso = form.cleaned_data.get('curso')
        turma = form.cleaned_data.get('turma')
        faixa_etaria = form.cleaned_data.get('faixa_etaria')
        situacao_declaracao = form.cleaned_data.get('situacao_declaracao')

        if situacao:
            registros = registros.filter(situacao_passaporte=situacao)

        if situacao_declaracao:
            registros = registros.filter(situacao_declaracao=situacao_declaracao)

        if categoria:
            if categoria == '1':
                registros = registros.filter(vinculo__user__eh_aluno=True)
            elif categoria == '2':
                registros = registros.filter(vinculo__user__eh_servidor=True)
            elif categoria == '3':
                registros = registros.filter(vinculo__user__eh_prestador=True)
            elif categoria == '4':
                registros = registros.filter(vinculo__user__eh_servidor=True, vinculo__in=Servidor.objects.ativos().filter(eh_docente=True).values_list('vinculos', flat=True))
            elif categoria == '5':
                registros = registros.filter(vinculo__user__eh_servidor=True, vinculo__in=Servidor.objects.ativos().filter(eh_tecnico_administrativo=True).values_list('vinculos', flat=True))

        if uo:
            registros = registros.filter(uo=uo)

        if curso:
            registros = registros.filter(vinculo__in=Aluno.objects.filter(curso_campus=curso).values_list('vinculos', flat=True))

        if turma:
            alunos = turma.get_alunos_matriculados()
            registros = registros.filter(vinculo__in=alunos.values_list('aluno__vinculos', flat=True))

        if faixa_etaria:
            dezoito_anos = datetime.date.today() + relativedelta(years=-18)
            sessenta_anos = datetime.date.today() + relativedelta(years=-60)
            if faixa_etaria == '1':
                registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__gt=dezoito_anos)
            elif faixa_etaria == '2':
                registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__lte=dezoito_anos, vinculo__pessoa__pessoafisica__nascimento_data__gt=sessenta_anos)
            elif faixa_etaria == '3':
                registros = registros.filter(vinculo__pessoa__pessoafisica__nascimento_data__lte=sessenta_anos)

        dados = list()
        esquema_completo = registros.filter(esquema_completo=True)
        primeira_dose = registros.filter(data_primeira_dose__isnull=False, esquema_completo=False)
        dados.append(
            ['Esquema Vacinal Completo', esquema_completo.count()])
        dados.append(
            ['Primeira Dose', primeira_dose.count()])
        dados.append(
            ['Sem registro de vacina no RN+Vacina', registros.filter(recebeu_alguma_dose=False, tem_cadastro=True).count()])
        dados.append(
            ['Sem cadastro no RN+Vacina', registros.filter(recebeu_alguma_dose=False, tem_cadastro=False).count()])

        grafico = PieChart('grafico', title='Percentuais de usuários com cada nível (dose) de vacinação.',
                           subtitle='Quantitativo de usuários com esquema vacinal completo, com primeira dose ou sem registros de vacina no RN+Vacina', minPointLength=0, data=dados)

        setattr(grafico, 'id', 'grafico')

        pie_chart_lists = [grafico]

    return locals()


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def importar_dados_vacinacao(request):
    args = ()
    vinculo = request.user.get_vinculo()
    if request.user.eh_aluno:
        cpf = vinculo.relacionamento.pessoa_fisica.cpf
    else:
        cpf = vinculo.relacionamento.cpf
    options = {'cpf': cpf, 'vinculo': vinculo.id, 'campus': get_uo(request.user).id, 'origem_view': True, 'pythonpath': None, 'verbosity': '1', 'traceback': None, 'settings': None}
    importar_dados_command = importar_dados_rnmaisvacina.Command()
    count_exceptions = importar_dados_command.handle(*args, **options)
    if count_exceptions:
        if count_exceptions == 'erro':
            return httprr(
                '/saude/passaporte_vacinacao_covid/', 'As variáveis de acesso ao RN+Vacina não foram configuradas.', tag='error'
            )
        return httprr(
            '/saude/passaporte_vacinacao_covid/', 'Não foi possível localizar seus dados de vacinação no RN+Vacina. Caso você tenha se vacinado em outro estado ou suas doses ainda não tenham sido registradas, favor atualizar os seus dados no RN+Vacina.', tag='error'
        )
    else:
        return httprr('/saude/passaporte_vacinacao_covid/', 'Dados sobre a vacinação importados com sucesso.')


@rtr()
@permission_required('saude.view_passaportevacinalcovid')
def ver_historico_validacao_passaporte(request, passaporte_id):
    passaporte = get_object_or_404(PassaporteVacinalCovid, pk=passaporte_id)
    if pode_validar_passaporte(request, passaporte):
        title = f'Histórico de Validação do Passaporte Vacinal: {passaporte}'
        historico = HistoricoValidacaoPassaporte.objects.filter(passaporte=passaporte).order_by('-avaliado_em')
        return locals()
    else:
        raise PermissionDenied


@transaction.atomic()
@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def cadastrar_resultado_teste(request, passaporte_id):
    passaporte = get_object_or_404(PassaporteVacinalCovid, pk=passaporte_id)
    pode_cadastrar_teste = passaporte.termo_aceito_em and passaporte.situacao_passaporte == PassaporteVacinalCovid.INVALIDO
    if passaporte.vinculo == request.user.get_vinculo() and pode_cadastrar_teste:
        title = 'Adicionar Resultado de Teste Negativo para COVID'
        form = CadastroResultadoTesteCovidForm(request.POST or None, request.FILES or None, request=request)
        if form.is_valid():
            o = form.save(False)
            o.passaporte = passaporte
            o.save()
            data_exame = form.cleaned_data.get('realizado_em')
            data_expiracao = data_exame + relativedelta(hours=+72)
            if data_exame < datetime.datetime.now() and data_expiracao > datetime.datetime.now():
                passaporte.situacao_passaporte = PassaporteVacinalCovid.VALIDO
            passaporte.situacao_declaracao == PassaporteVacinalCovid.AGUARDANDO_VALIDACAO
            passaporte.data_expiracao = data_expiracao
            passaporte.save()
            return httprr('/saude/passaporte_vacinacao_covid/', 'Resultado do teste cadastrado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def resultados_testes_covid(request, passaporte_id):
    passaporte = get_object_or_404(PassaporteVacinalCovid, pk=passaporte_id)
    if (request.user.has_perm('saude.view_passaportevacinalcovid') and get_uo(request.user) == passaporte.uo) or request.user.groups.filter(name='Validador de Passaporte Vacinal Sistêmico').exists() or passaporte.vinculo == request.user.get_vinculo() or pode_validar_passaporte(request, passaporte):
        title = f'Resultados de Testes Covid: {passaporte}'
        pode_avaliar = request.user.has_perm('saude.view_passaportevacinalcovid')
        historico = ResultadoTesteCovid.objects.filter(passaporte=passaporte).order_by('-avaliado_em')
        return locals()
    else:
        raise PermissionDenied


@transaction.atomic()
@rtr()
@permission_required('saude.view_passaportevacinalcovid')
def deferir_teste_covid(request, resultado_id):
    url = request.META.get('HTTP_REFERER', '.')
    obj = get_object_or_404(ResultadoTesteCovid, pk=resultado_id)
    passaporte = obj.passaporte
    if pode_validar_passaporte(request, passaporte):
        obj.situacao = ResultadoTesteCovid.DEFERIDO
        obj.avaliado_por = request.user.get_vinculo()
        obj.avaliado_em = datetime.datetime.now()
        obj.save()
        if (obj.realizado_em + relativedelta(hours=72)) > datetime.datetime.now():
            passaporte.situacao_passaporte = PassaporteVacinalCovid.VALIDO
            passaporte.save()
        titulo = '[SUAP] Saúde - Validação do Resultado do Teste contra COVID'
        texto = '<h1>Saúde</h1>' '<h2>Validação do Resultado do Teste contra COVID</h2><p>O resultado do seu teste foi {}.</p><p>Acesse o SUAP para mais detalhes.</p>'.format(obj.situacao)
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [passaporte.vinculo], categoria='Saúde: Resultado do Teste contra COVID', salvar_no_banco=True)
        return httprr(url, 'Resultado do teste avaliado com sucesso.')

    else:
        raise PermissionDenied


@transaction.atomic()
@rtr()
@permission_required('saude.view_passaportevacinalcovid')
def indeferir_teste_covid(request, resultado_id):
    url = request.META.get('HTTP_REFERER', '.')
    obj = get_object_or_404(ResultadoTesteCovid, pk=resultado_id)
    passaporte = obj.passaporte
    if pode_validar_passaporte(request, passaporte):
        title = f'Indeferir Resultado do Teste Covid - {passaporte}'
        form = JustificativaIndeferirPassaporteForm(request.POST or None, url_origem=url)
        if form.is_valid():
            obj.situacao = ResultadoTesteCovid.INDEFERIDO
            obj.avaliado_por = request.user.get_vinculo()
            obj.avaliado_em = datetime.datetime.now()
            obj.justificativa_indeferimento = form.cleaned_data.get('justificativa')
            obj.save()
            if (obj.realizado_em + relativedelta(hours=72)) > datetime.datetime.now():
                passaporte.situacao_passaporte = PassaporteVacinalCovid.INVALIDO
                passaporte.data_expiracao = None
                passaporte.save()
            titulo = '[SUAP] Saúde - Validação do Resultado do Teste contra COVID'
            texto = '<h1>Saúde</h1>' '<h2>Validação do Resultado do Teste contra COVID</h2><p>O resultado do seu teste foi {}.</p><p>Acesse o SUAP para mais detalhes.</p>'.format(obj.situacao)
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [passaporte.vinculo], categoria='Saúde: Resultado do Teste contra COVID', salvar_no_banco=True)
            return httprr(form.cleaned_data.get('url_origem'), 'Resultado do teste avaliado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@transaction.atomic()
@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def cadastrar_cartao_vacinal_covid(request):
    title = 'Cadastrar Cartão Vacinal Covid-19'
    obj = None
    tem_teste = False
    vinculo = request.user.get_vinculo()
    if PassaporteVacinalCovid.objects.filter(vinculo=vinculo).exists():
        obj = get_object_or_404(PassaporteVacinalCovid, vinculo=vinculo)
        cpf = obj.cpf
    else:
        if request.user.eh_aluno:
            cpf = vinculo.relacionamento.pessoa_fisica.cpf
        else:
            cpf = vinculo.relacionamento.cpf
    pode_adicionar_cartao_vacinal = not obj or obj.situacao_passaporte == PassaporteVacinalCovid.INVALIDO
    if pode_adicionar_cartao_vacinal:
        form = CadastroCartaoVacinalCovidForm(request.POST or None, request.FILES or None, instance=obj, request=request)
        if form.is_valid():
            o = form.save(False)
            o.cartao_vacinal_cadastrado_em = datetime.datetime.now()
            o.situacao_declaracao = PassaporteVacinalCovid.AGUARDANDO_VALIDACAO
            o.uo = get_uo(request.user)
            if cpf:
                o.cpf = cpf.replace('.', '').replace('-', '')
            o.vinculo = vinculo
            o.save()
            return httprr('/saude/passaporte_vacinacao_covid/', 'Cartão vacinal Covid-19 cadastrado com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def notificar_caso_covid(request):
    title = 'Notificar Caso de Síndromes Gripais e COVID-19'
    pode_indicar_usuario = False
    user = request.user
    especialidade = Especialidades(user)
    if especialidade.is_medico() or especialidade.is_enfermeiro() or especialidade.is_tecnico_enfermagem() or especialidade.is_auxiliar_enfermagem() or especialidade.is_odontologo() or especialidade.is_nutricionista() or especialidade.is_assistente_social():
        pode_indicar_usuario = True
    form = NotificarCovidForm(request.POST or None, request.FILES or None, pode_indicar_usuario=pode_indicar_usuario, user=user)
    if form.is_valid():
        if pode_indicar_usuario:
            pessoa = form.cleaned_data.get('usuario').user
        else:
            pessoa = request.user
        o = form.save(False)
        o.uo = get_uo(pessoa)
        o.vinculo = pessoa.get_vinculo()
        o.situacao = form.cleaned_data.get('declaracao')
        o.save()
        o.sintomas.set(form.cleaned_data.get('sintomas'))
        msg = None
        if form.cleaned_data.get('declaracao') == 'Confirmado':
            if pessoa.eh_servidor:
                msg = 'Caro servidor, foi enviada notificação a sua chefia imediata. Busque o atendimento de saúde de seu município para avaliação. Após avaliação médica envie seu atestado pelo sou.gov para justificar suas ausências.'
            elif pessoa.eh_aluno:
                msg = 'Caro estudante, foi enviada notificação a sua coordenação de curso. Busque o atendimento de saúde de seu município para avaliação médica. Após avaliação médica anexe seu atestado no SUAP via <a href="https://suap.ifrn.edu.br/centralservicos/abrir_chamado/216/">abertura de chamado</a> para justificar suas ausências enquanto precise se manter afastado.'
        else:
            if pessoa.eh_servidor:
                msg = 'Caro servidor, foi enviada notificação a sua chefia imediata. Busque o atendimento de saúde de seu município para avaliação médica e testagem COVID. Após avaliação médica envie seu atestado pelo sou.gov para justificar suas ausências caso precise se manter afastado.'
            elif pessoa.eh_aluno:
                msg = 'Caro estudante, foi enviada notificação a sua coordenação de curso. Busque o atendimento de saúde de seu município para avaliação médica e testagem COVID. Após avaliação médica anexe seu atestado no SUAP via <a href="https://suap.ifrn.edu.br/centralservicos/abrir_chamado/216/">abertura de chamado</a> para justificar suas ausências caso precise se manter afastado.'
        if msg:
            titulo = '[SUAP] Notificação de Caso de Síndromes Gripais e COVID-19'
            texto = '<h1>Saúde</h1><h2>Notificação de Caso de Síndromes Gripais e COVID-19</h2><p>{}</p>'.format(msg)
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [pessoa.get_vinculo()],
                              categoria='Notificação de Caso de Síndromes Gripais e Covid-19')
            if pessoa.eh_servidor:
                chefes = pessoa.get_relacionamento().funcionario.chefes_na_data(datetime.date.today())
                if chefes:
                    msg = f'O(a) servidor(a) {pessoa.get_vinculo()} fez uma notificação de Síndromes Gripais e COVID-19 no SUAP como {o.situacao}.'
                    texto = '<h1>Saúde</h1><h2>Notificação de Caso de Síndromes Gripais e COVID-19</h2><p>{}</p>'.format(msg)
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [chefes[0].servidor.get_vinculo()],
                                      categoria='Notificação de Caso de Síndromes Gripais e COVID-19')
            elif pessoa.eh_aluno and pessoa.get_relacionamento().curso_campus.coordenador:
                msg = 'O(a) aluno(a) {} fez uma notificação de Síndromes Gripais e COVID-19 no SUAP como {}.'.format(
                    pessoa.get_vinculo(), o.situacao)
                texto = '<h1>Saúde</h1><h2>Notificação de Caso de Síndromes Gripais e Covid-19</h2><p>{}</p>'.format(msg)
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [pessoa.get_relacionamento().curso_campus.coordenador.servidor.get_vinculo()],
                                  categoria='Notificação de Caso de Síndromes Gripais e COVID-19')

        return httprr('/', 'Notificação de Síndromes Gripais e COVID-19 cadastrada com sucesso.')

    return locals()


@rtr()
@permission_required('saude.view_notificacaocovid')
def monitorar_notificacao_covid(request, notificacao_id):
    notificacao = get_object_or_404(NotificacaoCovid, pk=notificacao_id)
    if (notificacao.uo == get_uo(request.user) or request.user.has_perm('saude.add_sintoma')) and notificacao.pode_monitorar():
        title = f'Monitorar Notificação - {notificacao.vinculo}'
        url = request.META.get('HTTP_REFERER', '.')
        form = MonitorarNotificacaoForm(request.POST or None, url=url)
        if form.is_valid():
            o = form.save(False)
            o.notificacao = notificacao
            o.cadastrado_por = request.user.get_vinculo()
            o.save()
            notificacao.monitoramento = form.cleaned_data.get('situacao')
            notificacao.save()
            return httprr(form.cleaned_data.get('url_origem'), 'Notificação de Síndromes Gripais e Covid-19 monitorada com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('saude.view_notificacaocovid')
def ver_monitoramentos_covid(request, notificacao_id):
    notificacao = get_object_or_404(NotificacaoCovid, pk=notificacao_id)
    if notificacao.uo == get_uo(request.user):
        title = f'Monitoramentos da Notificação - {notificacao.vinculo}'
        monitoramentos = MonitoramentoCovid.objects.filter(notificacao=notificacao).order_by('-cadastrado_em')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@group_required(['Servidor', 'Aluno', 'Prestador de Serviço'])
def relatorio_notificacao_covid(request):
    title = 'Relatório de Notificações da Covid-19'
    if request.user.groups.filter(name__in=['Coordenador de Atividades Estudantis Sistêmico', 'Coordenador de Gestão de Pessoas Sistêmico']):
        registros = NotificacaoCovid.objects.all()
        todos_campi = True
    else:
        registros = NotificacaoCovid.objects.filter(uo=get_uo(request.user))
        todos_campi = False
    form = RelatorioNotificacaoCovidForm(request.GET or None, todos_campi=todos_campi, request=request)
    if form.is_valid():
        categoria = form.cleaned_data.get('categoria')
        uo = form.cleaned_data.get('uo')
        curso = form.cleaned_data.get('curso')
        turma = form.cleaned_data.get('turma')
        setor = form.cleaned_data.get('setor')

        if categoria:
            if categoria == '1':
                registros = registros.filter(vinculo__user__eh_aluno=True)
            elif categoria == '2':
                registros = registros.filter(vinculo__user__eh_servidor=True)
            elif categoria == '3':
                registros = registros.filter(vinculo__user__eh_prestador=True)
        if uo:
            registros = registros.filter(uo=uo)

        if setor:
            servidores_do_setor = Servidor.objects.ativos().filter(setor__in=setor.descendentes)
            registros = registros.filter(
                vinculo__in=servidores_do_setor.values_list('vinculos', flat=True))

        if curso:
            registros = registros.filter(vinculo__in=Aluno.objects.filter(curso_campus=curso).values_list('vinculos', flat=True))

        if turma:
            alunos = turma.get_alunos_matriculados()
            registros = registros.filter(vinculo__in=alunos.values_list('aluno__vinculos', flat=True))

        dados = list()
        dados.append(['Sem monitoramento', registros.filter(monitoramento='Sem monitoramento').count()])
        dados.append(['Suspeito em monitoramento', registros.filter(monitoramento='Suspeito em monitoramento').count()])
        dados.append(['Confirmado em monitoramento', registros.filter(monitoramento='Confirmado em monitoramento').count()])
        dados.append(['Descartado', registros.filter(monitoramento='Descartado').count()])
        dados.append(['Recuperado', registros.filter(monitoramento='Recuperado').count()])
        dados.append(['Óbito', registros.filter(monitoramento='Óbito').count()])

        grafico = BarChart('grafico', title='Quantidade de notificações por Situação',
                           subtitle='Quantidade de notificações por Situação (aguardando monitoramento, suspeito em monitoramento, confirmado em monitoramento, descartado, recuperado ou óbito)', minPointLength=0, data=dados)

        setattr(grafico, 'id', 'grafico')

        pie_chart_lists = [grafico]

    return locals()


@rtr()
@permission_required('saude.pode_verificar_passaportes')
def verificacao_passaporte_vacinal(request):
    title = 'Verificar Passaporte Vacinal'
    form = VerificaPassaporteForm(request.POST or None)
    if form.is_valid():
        nome = form.cleaned_data.get('nome')
        registros = PassaporteVacinalCovid.objects.filter(
            Q(vinculo__pessoa__nome__icontains=nome) | Q(vinculo__user__username__icontains=nome))
    return locals()
