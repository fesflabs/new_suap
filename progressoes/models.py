import base64
import datetime
import hashlib
from datetime import timedelta
from decimal import Decimal

from dateutil import relativedelta
from django.core.exceptions import ValidationError

from comum import utils
from comum.models import Configuracao
from comum.utils import tl, get_setor
from djtools.db import models
from progressoes import assinatura
from rh.models import PadraoVencimento, Servidor


#
# Representa o processo de progressão do servidor, desde o estado inicial até o final (aprovado ou reprovado)
#
class ProcessoProgressao(models.ModelPlus):
    INTERSTICIO_MESES = 18
    INTERSTICIO_MESES_ESTAGIO_PROBATORIO = 36
    DIAS_ANTECEDENCIA_CALCULAR_NOVAS_PROGRESSOES = 45
    MEDIA_APROVACAO = 6.0

    TIPO_PROGRESSAO_MERITO = 1
    TIPO_ESTAGIO_PROBATORIO = 2
    TIPO_CHOICES = [[TIPO_PROGRESSAO_MERITO, 'Progressão Funcional por Mérito'], [TIPO_ESTAGIO_PROBATORIO, 'Estágio Probatório']]

    STATUS_A_INICIAR = 0
    STATUS_EM_TRAMITE = 1
    STATUS_FINALIZADO = 2
    STATUS_CHOICES = [[STATUS_A_INICIAR, 'A iniciar'], [STATUS_EM_TRAMITE, 'Em trâmite'], [STATUS_FINALIZADO, 'Finalizado']]

    SITUACAO_FINAL_NAO_FINALIZADO = 0
    SITUACAO_FINAL_APROVADO = 1
    SITUACAO_FINAL_REPROVADO = 2

    data_inicio_contagem_progressao = models.DateField('Data Início da Contagem', help_text='Início do período da contagem da progressão.')
    data_fim_contagem_progressao = models.DateField(
        'Data Final da Contagem',
        help_text='Final do período da contagem da progressão. '
        'Essa data será igual a '
        'Data início da contagem + '
        'meses de interstício + '
        'afastamentos no período da contagem (se for o caso).',
    )
    avaliado = models.ForeignKeyPlus('rh.Servidor', null=False, verbose_name='Avaliado', on_delete=models.CASCADE)
    status = models.IntegerField('Status do Processo', choices=STATUS_CHOICES, default=STATUS_A_INICIAR, help_text='Indica a situação atual do processo de progressão.')
    tipo = models.IntegerField('Tipo do Processo', choices=TIPO_CHOICES, default=TIPO_PROGRESSAO_MERITO)

    padrao_anterior = models.ForeignKeyPlus('rh.PadraoVencimento', null=True, on_delete=models.CASCADE, related_name='padrao_anterior', verbose_name='Padrão de Vencimento Atual')
    padrao_novo = models.ForeignKeyPlus('rh.PadraoVencimento', null=True, on_delete=models.CASCADE, related_name='padrao_novo', verbose_name='Padrão de Vencimento Novo')
    media_processo = models.DecimalField('Média do Processo', default=0, decimal_places=2, max_digits=12)

    protocolo = models.ForeignKeyPlus('protocolo.Processo', verbose_name='Protocolo', blank=True, null=True, on_delete=models.SET_NULL)
    processo_eletronico = models.ForeignKeyPlus('processo_eletronico.Processo', verbose_name='Processo Eletrônico', blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return 'Avaliado: {} - Situação: {}'.format(self.avaliado, self.get_status_display())

    def save(self, *args, **kwargs):
        if not self.id:
            # calcula data final da contagem
            self.calcular_data_de_progressao()
        #
        return models.Model.save(self)

    @staticmethod
    def calcular_servidores_a_progredir(salvar_processos=False, data_referencia=datetime.date.today()):
        novos_processos = []
        for servidor in Servidor.objects.ativos_permanentes().all():
            print('Analisando {}'.format(servidor))
            #
            datas_ultimas_progressoes = []
            for pca in servidor.pca_set.all().exclude(servidor__cargo_emprego__grupo_cargo_emprego__categoria='docente'):
                try:
                    posicionamento_referencia = pca.posicionamentopca_set.all().order_by('-data_inicio_posicionamento_pca')[0]
                    datas_ultimas_progressoes.append(posicionamento_referencia.data_inicio_posicionamento_pca)
                except Exception:
                    continue  # vai para o prox pca
            #
            if not datas_ultimas_progressoes:
                datas_ultimas_progressoes.append(servidor.calcula_inicio_exercicio_na_instituicao)
            #
            for data_ultima_progressao in datas_ultimas_progressoes:
                processo_progressao = ProcessoProgressao()
                processo_progressao.data_inicio_contagem_progressao = data_ultima_progressao
                processo_progressao.avaliado = servidor
                # calcula e define a data (final) da progressao
                processo_progressao.calcular_data_de_progressao()
                # prepara o proximo padrao de vencimento (se for o caso)
                proximo_padrao = processo_progressao.calcular_proximo_padrao_vencimento(servidor)
                #
                if proximo_padrao:
                    """
                        O objetivo é avisar (listar) ao RH com antecedência máxima de X dias.
                        A data calculada para progressao deverá está no futuro distante por no máximo X dias
                        a partir de uma determinanda data.

                        Exemplo:

                                                   X dias de antecedencia
                               --------|-----------------------------------------|---------------------
                                A, B   C    D     E                         data (final)         F
                                                                             progressao

                        Nos dias A e B a data de progressao está no futuro por mais de X dias. Então não haverá
                        avisos. No dia C está a exatos X dias e nos dias D e E está a menos de X dias. Nos casos
                        dos dias C, D e E haverá avisos. Por consequência, data de progressoes no passado em
                        relação a uma certa data F também produzirá avisos.
                    """
                    intervalo_entre_data_refer_e_data_progressao = (processo_progressao.data_fim_contagem_progressao - data_referencia).days
                    if intervalo_entre_data_refer_e_data_progressao <= ProcessoProgressao.DIAS_ANTECEDENCIA_CALCULAR_NOVAS_PROGRESSOES:
                        # processo já existe no banco?
                        processo_existe = ProcessoProgressao.objects.filter(
                            avaliado=servidor, data_fim_contagem_progressao=processo_progressao.data_fim_contagem_progressao
                        ).exists()
                        # processo já existe na lista atual?
                        processo_existe = processo_existe or False
                        #
                        if not processo_existe:
                            processo_progressao.status = ProcessoProgressao.STATUS_A_INICIAR
                            #
                            if salvar_processos:
                                # salva no banco o novo processo
                                print('Salvando processo para {}'.format(servidor))
                                processo_progressao.save(force_insert=True)
                            #
                            novos_processos.append(processo_progressao)
        #
        return novos_processos  # salvos ou não

    #
    # Calcula a data que o servidor deverá progredir ou adquerir a estabilidade ao completar 3 anos de efetivo exercicio
    #
    def calcular_data_de_progressao(self):
        # calcula os dias de afastamentos
        dias_afastamentos = self.obtem_afastamentos_numero_dias()

        # adiciona o tempo (meses) sobre a data de inicio
        if self.is_tipo_progressao_merito:
            data = self.add_months(self.data_inicio_contagem_progressao, ProcessoProgressao.INTERSTICIO_MESES)
        else:
            data = self.add_months(self.data_inicio_contagem_progressao, ProcessoProgressao.INTERSTICIO_MESES_ESTAGIO_PROBATORIO)

        # atualiza a data final
        self.data_fim_contagem_progressao = data + timedelta(dias_afastamentos) - timedelta(1)

    def obtem_afastamentos(self):
        """
            exerc corrido = |----------------------------------------| = 18 meses
            afastamentos  =    |xxxx|       |xxxxxxxxxxx|      |xxxxxxxxxxx|
            exerc altern  = |--      -------             ------             ------|

            afastamentos considerados = começar ou terminar dentro
                data inicial >= data inicial da contagem E data inicial <= data final da contagem (versão exerc corrido)
                OU
                data final >= data inicial da contagem E data final <= data final da contagem (versão exerc corrido)
        """
        if not self.data_fim_contagem_progressao:
            data_final_contagem_exercicio_corrido = self.add_months(self.data_inicio_contagem_progressao, ProcessoProgressao.INTERSTICIO_MESES)
        else:
            data_final_contagem_exercicio_corrido = self.data_fim_contagem_progressao
        #
        afastamentos_inicio_no_periodo_corrido = self.avaliado.afastamentos.filter(
            afastamento__interrompe_tempo_servico=True, data_inicio__gte=self.data_inicio_contagem_progressao, data_inicio__lte=data_final_contagem_exercicio_corrido
        )
        #
        afastamentos_termino_no_periodo_corrido = self.avaliado.afastamentos.filter(
            afastamento__interrompe_tempo_servico=True, data_termino__gte=self.data_inicio_contagem_progressao, data_termino__lte=data_final_contagem_exercicio_corrido
        )
        #
        afastamentos_considerados = afastamentos_inicio_no_periodo_corrido | afastamentos_termino_no_periodo_corrido

        #
        # verifica afastamentos que suspendem estágio probatório
        if self.tipo == ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO:
            afastamentos_inicio_no_periodo_corrido_estagio_probatorio = self.avaliado.afastamentos.filter(
                afastamento__suspende_estagio_probatorio=True, data_inicio__gte=self.data_inicio_contagem_progressao, data_inicio__lte=data_final_contagem_exercicio_corrido
            )
            #
            afastamentos_termino_no_periodo_corrido_estagio_probatorio = self.avaliado.afastamentos.filter(
                afastamento__suspende_estagio_probatorio=True, data_termino__gte=self.data_inicio_contagem_progressao, data_termino__lte=data_final_contagem_exercicio_corrido
            )
            # sobrescreve a variável "afastamentos_considerados" adicionando os afastamentos que suspendem estágio probatório
            afastamentos_considerados = afastamentos_inicio_no_periodo_corrido | afastamentos_termino_no_periodo_corrido | afastamentos_inicio_no_periodo_corrido_estagio_probatorio | afastamentos_termino_no_periodo_corrido_estagio_probatorio
        #
        return afastamentos_considerados.distinct()

    def obtem_afastamentos_numero_dias(self):
        afastamentos = self.obtem_afastamentos()
        #
        total_dias_afastado = 0
        for afastamento in afastamentos:
            if afastamento.data_termino:
                total_dias_afastado += (afastamento.data_termino - afastamento.data_inicio).days + 1
        #
        return total_dias_afastado

    def calcular_proximo_padrao_vencimento(self, servidor):
        #
        # define os padrões de vencimento (anterior e NOVO) verticais envolvidos na progressão
        #

        #
        # padrão anterior/atual
        #
        categoria_servidor = servidor.categoria
        classe_nivel_posicao = servidor.cargo_classe.codigo + servidor.nivel_padrao  # ex: E101
        classe = classe_nivel_posicao[0:1]  # E
        posicao_vertical = classe_nivel_posicao[2:4]  # 01
        padrao_anterior = PadraoVencimento.objects.filter(categoria=categoria_servidor, classe=classe, posicao_vertical=posicao_vertical)
        #
        if padrao_anterior.exists():
            padrao_anterior = padrao_anterior[0]  # a primeira instancia do queryset
        else:
            padrao_anterior = PadraoVencimento()  # cria o padrao de vencimento e grava no banco
            padrao_anterior.categoria = categoria_servidor
            padrao_anterior.classe = classe
            padrao_anterior.posicao_vertical = posicao_vertical
            padrao_anterior.save(force_insert=True)
        #
        self.padrao_anterior = padrao_anterior

        #
        # próximo padrão
        #
        posicao_vertical_proxima = int(posicao_vertical) + 1
        #
        if posicao_vertical_proxima > 16:  # 16 no máximo
            return None  # não há próximo padrão de vencimento na vertical - já chegou no topo da carreira \o/ \o/ \o/
        #
        posicao_vertical_proxima = ("{}".format(posicao_vertical_proxima)).rjust(2, "0")
        #
        padrao_novo = PadraoVencimento.objects.filter(categoria=categoria_servidor, classe=classe, posicao_vertical=posicao_vertical_proxima)
        #
        if padrao_novo.exists():
            padrao_novo = padrao_novo[0]  # a primeira instancia do queryset
        else:
            padrao_novo = PadraoVencimento()  # cria o padrao de vencimento e grava no banco
            padrao_novo.categoria = categoria_servidor
            padrao_novo.classe = classe
            padrao_novo.posicao_vertical = posicao_vertical_proxima
            padrao_novo.save(force_insert=True)
        #
        self.padrao_novo = padrao_novo

        return padrao_novo  # "subindo" para o novo padrão

    def calcular_media_processo(self, salvar=True):
        #
        # calcula a média do processo numa escala de desempenho de 0 a 10
        #

        # períodos
        periodos = self.processoprogressaoperiodo_set.all()
        periodos_somatorio_pesos = 0
        periodos_somatorio_media = 0
        for periodo in periodos:
            peso_periodo = periodo.obter_peso_periodo()
            periodos_somatorio_pesos += peso_periodo
            periodos_somatorio_media += periodo.media_periodo * peso_periodo
        #
        media = 0
        if periodos_somatorio_pesos > 0:
            media = periodos_somatorio_media / periodos_somatorio_pesos
        #
        # Arredondando a média (https://bugs.python.org/issue39124)
        media = round(Decimal(f'{media}'), 2)
        if salvar:
            self.media_processo = media
            self.save()
        #
        return media

    def obter_situacao_final_processo(self):
        if self.status == ProcessoProgressao.STATUS_FINALIZADO:
            if self.media_processo >= ProcessoProgressao.MEDIA_APROVACAO:
                return ProcessoProgressao.SITUACAO_FINAL_APROVADO
            else:
                return ProcessoProgressao.SITUACAO_FINAL_REPROVADO
        else:
            return ProcessoProgressao.SITUACAO_FINAL_NAO_FINALIZADO

    def obter_situacao_final_processo_as_text(self):
        situacao_final = self.obter_situacao_final_processo()
        if situacao_final == ProcessoProgressao.SITUACAO_FINAL_APROVADO:
            return 'Aprovado'
        elif situacao_final == ProcessoProgressao.SITUACAO_FINAL_REPROVADO:
            return 'Reprovado'
        elif situacao_final == ProcessoProgressao.SITUACAO_FINAL_NAO_FINALIZADO:
            return 'Não finalizado'
        else:
            return ''

    def obter_vinculos_avaliadores(self, incluir_avaliado=True):
        vinculos = []
        avaliadores_ids = []
        periodos = self.processoprogressaoperiodo_set.all()
        for periodo in periodos:
            for avaliador in periodo.obter_avaliadores(incluir_avaliado):
                if not (avaliador.id in avaliadores_ids):
                    vinculos.append(avaliador.get_vinculo())
                    avaliadores_ids.append(avaliador.id)
        return vinculos

    def obter_avaliacoes(self):
        meus_periodos_ids = ProcessoProgressaoPeriodo.objects.filter(processo_progressao=self).values_list('id', flat=True)
        return ProcessoProgressaoAvaliacao.objects.filter(periodo__in=meus_periodos_ids)

    def validar_periodos(self):
        """
            return (False, mensagens_de_erro) OU (True, "")
        """
        #
        # valida os padrões anterior e novo
        if self.padrao_anterior and self.padrao_novo and self.padrao_anterior == self.padrao_novo:
            return False, 'Os padrões de vencimento \'{}\' (anterior) e \'{}\' (novo) devem ser diferentes.'.format(self.padrao_anterior, self.padrao_novo)

        #
        # recalcula a data final do processo
        data_fim_contagem_progressao_anterior = self.data_fim_contagem_progressao
        self.calcular_data_de_progressao()
        data_fim_contagem_progressao_estava_errada = data_fim_contagem_progressao_anterior != self.data_fim_contagem_progressao
        if data_fim_contagem_progressao_estava_errada:
            self.save()  # salva a data final que foi recalculada

        avaliado_historico_setor_suap = self.avaliado.historico_setor_suap(data_inicio=self.data_inicio_contagem_progressao, data_fim=self.data_fim_contagem_progressao)
        avaliado_historico_setor_siape = self.avaliado.historico_setor_siape(data_inicio=self.data_inicio_contagem_progressao, data_fim=self.data_fim_contagem_progressao)
        avaliado_historico_funcao = self.avaliado.historico_funcao(data_inicio=self.data_inicio_contagem_progressao, data_fim=self.data_fim_contagem_progressao)

        #
        # cria lista com os ids dos setores
        avaliado_historico_setores_ids = set(
            list(avaliado_historico_setor_suap.values_list('setor', flat=True))
            + list(avaliado_historico_setor_siape.values_list('setor_exercicio', flat=True))
            + list(avaliado_historico_funcao.values_list('setor', flat=True))
        )

        periodos = []
        avaliadores_cadastrados = True
        avaliador_chefe_cadastrado_igual_a_1 = True
        avaliado_setores_invalidos = []
        menor_data = None
        maior_data = None
        for periodo in self.processoprogressaoperiodo_set.all():
            periodos += ((periodo.data_inicio, periodo.data_fim),)
            avaliadores_cadastrados = avaliadores_cadastrados and periodo.obter_avaliadores()
            avaliador_chefe_cadastrado_igual_a_1 = avaliador_chefe_cadastrado_igual_a_1 and len(periodo.obter_avaliadores_chefe()) == 1

            if periodo.setor.id not in avaliado_historico_setores_ids:
                avaliado_setores_invalidos.append("Setor '{}' não está no histórico de setores e funções. ".format(periodo.setor))

            if not menor_data:
                menor_data = periodo.data_inicio
            if not maior_data:
                maior_data = periodo.data_fim

            if periodo.data_inicio < menor_data:
                menor_data = periodo.data_inicio
            if periodo.data_fim > maior_data:
                maior_data = periodo.data_fim
        #
        # enquadra os períodos de afastamentos
        ha_afastamentos = False
        for afastamento in self.obtem_afastamentos():
            if not menor_data:
                menor_data = afastamento.data_inicio
            if not maior_data:
                maior_data = afastamento.data_termino

            if afastamento.data_inicio < menor_data:
                menor_data = afastamento.data_inicio
            if afastamento.data_termino and afastamento.data_termino > maior_data:
                maior_data = afastamento.data_termino

            ha_afastamentos = True

        periodos_ok, periodos_mensagem = False, "Nenhum período cadastrado."

        if periodos:
            if not avaliadores_cadastrados:
                periodos_ok, periodos_mensagem = False, "Nenhum avaliador foi selecionado ou há períodos sem avaliadores."

            elif avaliadores_cadastrados and not avaliador_chefe_cadastrado_igual_a_1:
                periodos_ok, periodos_mensagem = False, "Há períodos sem avaliador chefe selecionado ou com mais de um avaliador chefe."

            elif avaliado_setores_invalidos:
                periodos_ok, periodos_mensagem = False, "".join(avaliado_setores_invalidos)

            elif self.data_inicio_contagem_progressao < menor_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período não coberto: {} a {}.".format(self.data_inicio_contagem_progressao.strftime('%d/%m/%Y'), (menor_data - timedelta(1)).strftime('%d/%m/%Y')),
                )

            elif self.data_inicio_contagem_progressao > menor_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período inválido: {} a {}.".format(menor_data.strftime('%d/%m/%Y'), (self.data_inicio_contagem_progressao - timedelta(1)).strftime('%d/%m/%Y')),
                )

            elif self.data_fim_contagem_progressao > maior_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período não coberto: {} a {}.".format((maior_data + timedelta(1)).strftime('%d/%m/%Y'), self.data_fim_contagem_progressao.strftime('%d/%m/%Y')),
                )

            elif self.data_fim_contagem_progressao < maior_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período inválido: {} a {}.".format((self.data_fim_contagem_progressao + timedelta(1)).strftime('%d/%m/%Y'), maior_data.strftime('%d/%m/%Y')),
                )

            else:
                #
                # a última esperança de um True e nenhuma mensagem de erro (rsrs)
                periodos_ok, periodos_mensagem = utils.periodos_sucessivos(periodos)
                periodos_mensagem = "".join(periodos_mensagem)

                if not periodos_ok and ha_afastamentos:
                    periodos_mensagem += " Nesse processo há períodos de afastamentos " "(verifique os períodos de avaliação e faça os ajustes necessários)."

        if not periodos_ok and data_fim_contagem_progressao_estava_errada:
            periodos_mensagem += (
                " A data final da contagem foi recalculada e modificada de {} para {} "
                "(verifique os períodos de avaliação e faça os ajustes necessários).".format(
                    data_fim_contagem_progressao_anterior.strftime('%d/%m/%Y'), self.data_fim_contagem_progressao.strftime('%d/%m/%Y')
                )
            )

        return periodos_ok, periodos_mensagem

    @staticmethod
    def obter_processos_a_iniciar():
        return ProcessoProgressao.objects.filter(status=ProcessoProgressao.STATUS_A_INICIAR)

    @staticmethod
    def obter_processos_por_avaliado(servidor_avaliado):
        return ProcessoProgressao.objects.filter(avaliado=servidor_avaliado)

    @staticmethod
    def obter_processos_por_avaliador(servidor_avaliador):
        return ProcessoProgressao.objects.filter(processoprogressaoperiodo__processoprogressaoavaliacao__avaliador=servidor_avaliador)

    @staticmethod
    def obter_processos_a_finalizar():
        return ProcessoProgressao.objects.filter(status=ProcessoProgressao.STATUS_EM_TRAMITE).exclude(
            processoprogressaoperiodo__processoprogressaoavaliacao__status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_PENDENTE
        )

    @property
    def pode_finalizar(self):
        if self.status == ProcessoProgressao.STATUS_EM_TRAMITE:
            avaliacoes_processo = self.obter_avaliacoes()
            for avaliacao in avaliacoes_processo:
                if avaliacao.is_pendente:
                    return False
            return True
        else:
            return False

    def finalizar_processo(self):
        #
        # analisa os periodos
        #
        for periodo in self.processoprogressaoperiodo_set.all():
            #
            # valida a integridade e as assinaturas das avaliações do período
            #
            assinaturas_realizadas = 0
            assinaturas_requeridas = 0
            for avaliacao in periodo.processoprogressaoavaliacao_set.all():
                #
                # integridade do dados
                if not avaliacao.dados_integros:
                    return False, "A avaliação '{}' não está com dados íntegros e deve ser respondida novamente.".format(avaliacao)
                #
                # assinaturas
                realizadas, requeridas = avaliacao.assinaturas_realizadas_requeridas()
                assinaturas_realizadas += realizadas
                assinaturas_requeridas += requeridas
            #
            if assinaturas_realizadas != assinaturas_requeridas:
                return False, "Há {} assinatura(s) pendente(s).".format(assinaturas_requeridas - assinaturas_realizadas)
            #
            # valida a media do periodo
            #
            media = periodo.calcular_media_periodo(salvar=False)
            media_salva = periodo.media_periodo
            if media != media_salva:
                return False, "O período '{}' está com média inválida. Acesse a opção 'Recalcular Médias'.".format(periodo)
        #
        # valida a media do processo
        #
        media = self.calcular_media_processo(salvar=False)
        media_salva = self.media_processo
        if media != media_salva:
            return False, "O processo está com média final inválida. Acesse a opção 'Recalcular Médias'."
        #
        # recalcula a data final da contagem
        #
        data_fim_contagem_progressao_anterior = self.data_fim_contagem_progressao
        self.calcular_data_de_progressao()
        data_fim_contagem_progressao_estava_errada = data_fim_contagem_progressao_anterior != self.data_fim_contagem_progressao
        if data_fim_contagem_progressao_estava_errada:
            self.save()  # salva a data final que foi recalculada
            return (
                False,
                "A data final da contagem foi recalculada e modificada de {} para {}. "
                "Se for o caso, o trâmite do processo deve ser cancelado para que os ajustes nos "
                "períodos de avaliação sejam realizados. Em seguida, o processo deve ser colocado "
                "novamente em trâmite e, por fim, finalizado.".format(
                    data_fim_contagem_progressao_anterior.strftime('%d/%m/%Y'), self.data_fim_contagem_progressao.strftime('%d/%m/%Y')
                ),
            )
        #
        # chegou nesse ponto, está tudo OK com as avaliações, com as médias dos períodos e do processo e com a
        # data final da contagem
        #
        self.status = ProcessoProgressao.STATUS_FINALIZADO
        self.save()
        return True, "O processo foi finalizado."

    def add_months(self, sourcedate, months):
        return sourcedate + relativedelta.relativedelta(months=months)

    @property
    def is_a_iniciar(self):
        return self.status == ProcessoProgressao.STATUS_A_INICIAR

    @property
    def is_em_tramite(self):
        return self.status == ProcessoProgressao.STATUS_EM_TRAMITE

    @property
    def is_finalizado(self):
        return self.status == ProcessoProgressao.STATUS_FINALIZADO

    @property
    def is_aprovado(self):
        return self.obter_situacao_final_processo() == ProcessoProgressao.SITUACAO_FINAL_APROVADO

    @property
    def is_reprovado(self):
        return self.obter_situacao_final_processo() == ProcessoProgressao.SITUACAO_FINAL_REPROVADO

    @property
    def is_tipo_progressao_merito(self):
        return self.tipo == ProcessoProgressao.TIPO_PROGRESSAO_MERITO

    @property
    def is_tipo_estagio_probatorio(self):
        return self.tipo == ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO

    ##
    # calcula o setor do primeiro trâmite a partir do setor do servidor avaliado
    @staticmethod
    def calcular_setor_primeiro_tramite(setor_avaliado):
        #
        # demanda 961 - https://suap.ifrn.edu.br/demandas/visualizar/961
        uo = setor_avaliado.uo
        if uo.eh_reitoria:
            sigla_primeiro_tramite_reitoria = Configuracao.get_valor_por_chave('progressoes', 'sigla_setor_primeiro_tramite_reitoria')
            # se reitoria, setor primeiro trâmite é codepe
            return uo.setor_set.filter(sigla=sigla_primeiro_tramite_reitoria).first()
        else:
            # senão, setor é cogpe, asgpe ou diape.
            siglas_primeiro_tramite_campus = Configuracao.get_valor_por_chave('progressoes', 'sigla_setor_primeiro_tramite_campus').split(',')
            for sigla in siglas_primeiro_tramite_campus:
                setor = uo.setor_set.filter(sigla__icontains=sigla.strip()).first()
                if setor:
                    return setor
        raise ValidationError('Configuração de primeiro trâmite do processo inexistente ou mau configurada. Por favor '
                              'entrar em contato com o administraor do sistema para realizar essa configuração')

    def gerar_protocolo(self):
        from protocolo.models import Processo as ProtocoloFisico, Tramite

        try:
            setor_primeiro_tramite = self.calcular_setor_primeiro_tramite(self.avaliado.setor)

            setor_gerador_protocolo = get_setor()
            user_gerador_protocolo = tl.get_user()

            # cria o protocolo físico
            protocolo = ProtocoloFisico()
            protocolo.assunto = '{}'.format(self.get_tipo_display())
            protocolo.vinculo_cadastro = user_gerador_protocolo.get_vinculo()
            protocolo.set_interessado(self.avaliado)
            protocolo.tipo = ProtocoloFisico.TIPO_REQUERIMENTO
            protocolo.numero_documento = "-"
            protocolo.palavras_chave = "Avaliação de Desempenho, {}".format(self.get_tipo_display())
            protocolo.save()

            tramite = Tramite()
            tramite.processo = protocolo
            tramite.tipo_encaminhamento = Tramite.TIPO_ENCAMINHAMENTO_INTERNO
            tramite.orgao_interno_encaminhamento = setor_gerador_protocolo
            tramite.orgao_interno_recebimento = setor_primeiro_tramite
            tramite.pessoa_encaminhamento = user_gerador_protocolo.get_profile()
            tramite.data_encaminhamento = datetime.datetime.now()
            tramite.ordem = 1
            tramite.save()

            self.protocolo = protocolo
            self.save()
        except Exception as erro:
            raise Exception('{}'.format(erro))

    def gerar_processo_eletronico(self, avaliacoes_file):
        from processo_eletronico.models import TipoProcesso, Processo as ProcessoEletronico, Documento, TipoDocumento, TipoConferencia

        try:
            # configurações SUAP
            pk_tipo_processo = Configuracao.get_valor_por_chave("progressoes", "processo_eletronico_tipo_processo")
            pk_tipo_documento = Configuracao.get_valor_por_chave("progressoes", "processo_eletronico_tipo_documento")
            pk_tipo_conferencia = Configuracao.get_valor_por_chave("progressoes", "processo_eletronico_tipo_conferencia")

            if not pk_tipo_processo:
                raise Exception('Configuração SUAP ausente: ' '"Aplicação Progressoes > Tipo de processo (Processo Eletrônico)"')

            if not pk_tipo_documento:
                raise Exception('Configuração SUAP ausente: ' '"Aplicação Progressoes > Tipo de documento (Processo Eletrônico)"')

            if not pk_tipo_conferencia:
                raise Exception('Configuração SUAP ausente: ' '"Aplicação Progressoes > Tipo de conferência (Processo Eletrônico)"')

            setor_primeiro_tramite = self.calcular_setor_primeiro_tramite(self.avaliado.setor)
            tipo_processo = TipoProcesso.objects.get(pk=pk_tipo_processo)
            tipo_documento = TipoDocumento.objects.get(pk=pk_tipo_documento)
            tipo_conferencia = TipoConferencia.objects.get(pk=pk_tipo_conferencia)

            user_gerador_processo_eletronico = tl.get_user()

            processo_tramite = {'tipo_processo': tipo_processo, 'assunto': '{}'.format(self.get_tipo_display()), 'setor_destino': setor_primeiro_tramite}

            processo_documento_avaliacoes = {
                'tipo': tipo_documento,
                'tipo_conferencia': tipo_conferencia,
                'assunto': 'Avaliação de Desempenho',
                'nivel_acesso': Documento.NIVEL_ACESSO_PUBLICO,
                'arquivo': avaliacoes_file,
            }

            self.processo_eletronico = ProcessoEletronico.cadastrar_processo(
                user=user_gerador_processo_eletronico,
                processo_tramite=processo_tramite,
                papel=user_gerador_processo_eletronico.get_relacionamento().papeis_ativos.first(),
                documentos_texto=[],
                documentos_digitalizados=[processo_documento_avaliacoes],
                interessados=[self.avaliado],
            )

            if not self.processo_eletronico:
                raise Exception('Erro ao gerar o processo eletrônico.')

            self.save()
            avaliacoes_file.close()
        except Exception as erro:
            raise Exception('{}'.format(erro))

    class Meta:
        ordering = ('-data_inicio_contagem_progressao',)
        verbose_name = 'Processo de Progressão/Estágio Probatório'
        verbose_name_plural = 'Processos de Progressão/Estágio Probatório'
        permissions = (
            ('pode_ver_todos_os_processos', 'Pode visualizar todos os processos'),
            ('pode_ver_apenas_processos_do_seu_campus', 'Pode visualizar apenas os processos do seu campus'),
        )


#
# Representa um período no qual o servidor é avaliado
#
class ProcessoProgressaoPeriodo(models.ModelPlus):
    processo_progressao = models.ForeignKeyPlus('progressoes.ProcessoProgressao', blank=True, null=False, verbose_name='Processo de Progressão', on_delete=models.CASCADE)
    avaliacao_modelo = models.ForeignKeyPlus('progressoes.AvaliacaoModelo', blank=False, null=False, verbose_name='Modelo de Avaliação', on_delete=models.CASCADE)
    setor = models.ForeignKeyPlus('rh.Setor')
    data_inicio = models.DateFieldPlus('Data Inicial')
    data_fim = models.DateFieldPlus('Data Final')
    media_periodo = models.DecimalFieldPlus(default=0, decimal_places=2, max_digits=12)

    def __str__(self):
        return '{} à {} - {}'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'), self.setor)

    @property
    def funcao_gratificada(self):
        return self.avaliacao_modelo.funcao_gratificada

    def calcular_media_periodo(self, salvar=True):
        #
        # calcula a media do período numa escala de desempenho de 0 a 10
        #

        # avaliacoes do periodo
        avaliacoes_periodo = self.processoprogressaoavaliacao_set.all()
        # totais tipos de avaliadores
        auto = 0
        chefe = 0
        equipe = 0

        equipe_qtd = 0

        for avaliacao in avaliacoes_periodo:
            if avaliacao.tipo_avaliador == ProcessoProgressaoAvaliacao.TIPO_AVALIADOR_AUTO:
                auto += avaliacao.media_avaliacao
            elif avaliacao.tipo_avaliador == ProcessoProgressaoAvaliacao.TIPO_AVALIADOR_EQUIPE:
                equipe += avaliacao.media_avaliacao
                equipe_qtd += 1
            elif avaliacao.tipo_avaliador == ProcessoProgressaoAvaliacao.TIPO_AVALIADOR_CHEFE:
                chefe += avaliacao.media_avaliacao

        if equipe_qtd > 0:
            media_par = equipe / equipe_qtd
        else:
            media_par = 0
        #
        if media_par == 0 and equipe_qtd == 0:
            soma_pesos = 2  # se não há avaliações de membros da equipe, soma dos pesos = 2
            if self.processo_progressao.is_tipo_estagio_probatorio:
                soma_pesos = 1  # uma única avaliação do chefe
            media = (auto * 1 + chefe * 1) / soma_pesos
        else:
            # nesse ponto, é possível que media_par = 0, pois é possível que todos os membros da equipe tenham
            # dado nota ZERO em todas as questões das avaliações e, mesmo nesse caso, a soma dos pesos deverá ser 4
            media = (auto * 1 + chefe * 1 + media_par * 2) / 4
        #
        # Arredondando a média (https://bugs.python.org/issue39124)
        media = round(Decimal(f'{media}'), 2)
        if salvar:
            self.media_periodo = media
            self.save()
        #
        self.processo_progressao.calcular_media_processo(salvar=salvar)
        #
        return media

    def obter_peso_periodo(self):
        delta = self.data_fim - self.data_inicio
        return abs(delta.days)

    def obter_avaliadores(self, incluir_avaliado=True):
        avaliadores = []
        for avaliacao in self.processoprogressaoavaliacao_set.all():
            if avaliacao.avaliador == self.processo_progressao.avaliado and not incluir_avaliado:
                continue
            if avaliacao.avaliador not in avaliadores:
                avaliadores.append(avaliacao.avaliador)
        return avaliadores

    def tem_avaliador_chefe(self):
        return self.obter_avaliadores_chefe().exists()

    def obter_avaliadores_chefe(self):
        return self.processoprogressaoavaliacao_set.filter(tipo_avaliador=ProcessoProgressaoAvaliacao.TIPO_AVALIADOR_CHEFE)

    class Meta:
        ordering = ('data_inicio',)
        verbose_name = 'Período Avaliado'
        verbose_name_plural = 'Períodos Avaliados'


#
# Representa uma avaliação/questionário
#
class AvaliacaoModelo(models.ModelPlus):
    nome = models.CharField('Descrição do Modelo', max_length=255, unique=True)
    funcao_gratificada = models.BooleanField('Modelo para Servidores com Função Gratificada', default=False, help_text='Não se aplica ao estágio probatório')
    itens_avaliados = models.ManyToManyField('progressoes.AvaliacaoModeloCriterio', verbose_name='Critérios Avaliados')
    tipo = models.IntegerField('Tipo do Processo', choices=ProcessoProgressao.TIPO_CHOICES, default=ProcessoProgressao.TIPO_PROGRESSAO_MERITO)

    class Meta:
        verbose_name = 'Modelo/Ficha de Avaliação'
        verbose_name_plural = 'Modelos/Fichas de Avaliação'

    def __str__(self):
        return '{}'.format(self.nome)

    def get_absolute_url(self):
        return '/progressoes/avaliacao_modelo_visualizar/{}/'.format(self.pk)


#
# Representa um critério (questão) que pode ser usado em um ou mais modelos/fichas de avaliação
#
class AvaliacaoModeloCriterio(models.ModelPlus):
    SEARCH_FIELDS = ['descricao_questao']

    descricao_questao = models.TextField('Descrição do Critério/Questão', unique=True)
    nota_minima = models.PositiveIntegerField('Nota Mínima', help_text='Nota mínima que pode ser dada ao critério/questão', default=0, null=True)
    nota_maxima = models.PositiveIntegerField('Nota Máxima', help_text='Nota máxima que pode ser dada ao critério/questão', default=10, null=True)
    passo_nota = models.FloatField('Intervalo entre Notas', help_text='Passo da nota', default=1.0, null=True)

    def __str__(self):
        return self.descricao_questao

    def clean(self):
        if self.id:  # editando ...
            criterio = AvaliacaoModeloCriterio.objects.get(pk=self.id)
            #
            # "lugares" onde o critério é usado (acrescentar mais lugares quando necessário)
            #
            modelos_avaliacao = AvaliacaoModelo.objects.filter(itens_avaliados__id=criterio.id)
            notas_progressoes = AvaliacaoCriterioNota.objects.filter(criterio_avaliado__id=criterio.id)
            estah_sendo_usado = modelos_avaliacao.exists() or notas_progressoes.exists()
            #
            if estah_sendo_usado and self.descricao_questao != criterio.descricao_questao:
                raise ValidationError(
                    'Não é permitida a alteração da descrição deste critério/questão, '
                    'pois o mesmo já foi selecionado/usado em algumas situações '
                    '(modelos de avaliação ou avaliações realizadas).'
                )

    class Meta:
        verbose_name = 'Critério de Avaliação'
        verbose_name_plural = 'Critérios de Avaliação'
        ordering = ('descricao_questao',)


#
# Representa uma avaliação realizada
#
class ProcessoProgressaoAvaliacao(models.ModelPlus):
    TIPO_AVALIADOR_CHEFE = 0
    TIPO_AVALIADOR_EQUIPE = 1
    TIPO_AVALIADOR_AUTO = 2
    TIPO_AVALIADOR_CHOICES = [[TIPO_AVALIADOR_CHEFE, 'Chefe Imediato'], [TIPO_AVALIADOR_EQUIPE, 'Membro da Equipe'], [TIPO_AVALIADOR_AUTO, 'Auto-Avaliação']]

    STATUS_AVALIACAO_PENDENTE = 0
    STATUS_AVALIACAO_AVALIADA = 1
    STATUS_AVALIACAO_CHOICES = [[STATUS_AVALIACAO_PENDENTE, 'Pendente'], [STATUS_AVALIACAO_AVALIADA, 'Avaliada']]

    periodo = models.ForeignKeyPlus('progressoes.ProcessoProgressaoPeriodo', on_delete=models.CASCADE)
    avaliador = models.ForeignKeyPlus('rh.Servidor', on_delete=models.CASCADE)
    tipo_avaliador = models.IntegerField(choices=TIPO_AVALIADOR_CHOICES)
    status_avaliacao = models.IntegerField('Situação do Período', choices=STATUS_AVALIACAO_CHOICES, default=STATUS_AVALIACAO_PENDENTE)
    data_avaliacao = models.DateField('Data da Avaliação', null=True)
    total_pontos = models.FloatField(default=0.0)
    comentario_avaliador = models.TextField(blank=True)
    comentario_avaliado = models.TextField(blank=True)
    comentario_rh = models.TextField(blank=True)
    hash_string = models.TextField('String formadora do Hash', blank=True)
    hash_valor = models.CharFieldPlus('Hash', blank=True)

    assinatura_avaliador = models.TextField('Assinatura do Avaliador', blank=True, null=True, default="")
    data_assinatura_avaliador = models.DateField('Data de Assinatura do Avaliador', null=True, default=None)
    assinatura_avaliado = models.TextField('Assinatura do Avaliado', blank=True, null=True, default="")
    data_assinatura_avaliado = models.DateField('Data de Assinatura do Avaliador', null=True, default=None)

    # um período pode ter 1 ou mais avaliadores com papel de "chefe imediato", os quais podem assinar
    # as avaliações do período como "chefe imediato", por isso a necessidade de armazenar qual chefe
    # imediato assinou a avaliação para que a assinatura seja verificada no futuro
    assinatura_chefe_imediato = models.TextField('Assinatura do Chefe Imediato', blank=True, null=True, default="")
    data_assinatura_chefe_imediato = models.DateField('Data de Assinatura do Chefe Imediato', null=True, default=None)
    chefe_imediato_assinante = models.ForeignKeyPlus('rh.Servidor', null=True, blank=True, related_name="chefe_imediato_assinante", on_delete=models.CASCADE)

    #
    # origem do atributo: servidor foi escolhido como avaliador de um processo e notificado via SUAP/email.
    # em seguida o RH remove esse avaliador do processo e o mesmo fica sem saber o que ocorreu. O atributo
    # será usado para verificar se há necessidade ou não de notificar o avaliador caso ele venha ser excluído
    # do processo (se numero_liberacoes > 0, notifica o avaliador, pois o mesmo já tinha conhecimento que participava
    # do processo)
    #
    numero_liberacoes = models.IntegerField(editable=False, default=0)

    def __str__(self):
        return 'Avaliador: {} ({}) - Status: {}'.format(self.avaliador, self.get_tipo_avaliador_display(), self.get_status_avaliacao_display())

    def obter_itens_avaliados(self):
        # itens avaliados
        itens_avaliados = []

        # modelo de avaliacao
        modelo_avaliacao = self.periodo.avaliacao_modelo

        # notas salvas
        notas_salvas = AvaliacaoCriterioNota.objects.filter(avaliacao=self)

        # criterios do modelo
        for criterio in modelo_avaliacao.itens_avaliados.all():
            # procura a nota
            nota = notas_salvas.filter(criterio_avaliado=criterio)
            if nota.exists():
                criterio_nota = nota[0]
            else:
                if self.status_avaliacao == ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA:
                    continue  # a questão não existia quando a avaliação foi respondida e não poderá fazer parte da lista

                # criterio sem nota salva
                criterio_nota = AvaliacaoCriterioNota()
                criterio_nota.criterio_avaliado = criterio
                criterio_nota.avaliacao = self
            itens_avaliados.append(criterio_nota)

        # todas as notas salvas estão na listagem?
        for nota_salva in notas_salvas:
            if nota_salva not in itens_avaliados:
                itens_avaliados.append(nota_salva)  # uma nota salva associado a um critério que não está mais no modelo
        #
        return itens_avaliados

    @property
    def processo(self):
        return self.periodo.processo_progressao

    @property
    def is_pendente(self):
        return self.status_avaliacao == self.STATUS_AVALIACAO_PENDENTE

    @property
    def is_avaliada(self):
        return self.status_avaliacao == self.STATUS_AVALIACAO_AVALIADA

    def obter_total_pontos(self):
        notas_avaliacao = AvaliacaoCriterioNota.objects.filter(avaliacao=self)
        soma = 0
        for nota in notas_avaliacao:
            soma = soma + nota.nota
        return soma

    def obter_hash_string(self):
        #
        # o avaliador tem influencia sobre os seguintes dados da avaliacao:
        #    - data de avaliacao (definida quando salva as notas da avaliação)
        #    - total de pontos (reflexo das notas que atribuiu)
        #    - seus comentários
        #
        avaliador = self.avaliador
        try:
            hash_string = '{}|{}|{}|{}|{}'.format(avaliador.id, avaliador.username, self.data_avaliacao.strftime('%d/%m/%Y'), self.total_pontos, self.comentario_avaliador)
            return hash_string
        except Exception:
            return ""

    @classmethod
    def obter_hash_valor(cls, hash_string):
        return hashlib.sha1(hash_string.encode("utf8")).hexdigest()

    @property
    def dados_integros(self):
        #
        # verifica se os dados informados pelo avaliador estão íntegros
        #
        hash_string = self.obter_hash_string()
        hash_valor = ProcessoProgressaoAvaliacao.obter_hash_valor(hash_string)
        return (self.hash_string == hash_string) and (self.hash_valor == hash_valor)

    #
    # realivar a avaliacao, editando as notas
    #
    def reavaliar(self):
        self.status_avaliacao = self.STATUS_AVALIACAO_PENDENTE
        self.data_avaliacao = None
        self.total_pontos = 0.0
        self.hash_string = ""
        self.hash_valor = ""
        self.assinatura_avaliado = ""
        self.assinatura_avaliador = ""
        self.assinatura_chefe_imediato = ""
        self.chefe_imediato_assinante = None
        self.data_assinatura_avaliado = None
        self.data_assinatura_avaliador = None
        self.data_assinatura_chefe_imediato = None
        self.save()

    @property
    def media_avaliacao(self):
        #
        # média da avaliação (SEMPRE calculada) numa escala de desempenho de 0 a 10
        #
        # média = (total de pontos * 100 / total de pontos possíveis)/10
        #
        try:
            total_pontos_possiveis = 0
            for criterio in self.obter_itens_avaliados():
                nota_maxima_criterio = criterio.criterio_avaliado.nota_maxima
                total_pontos_possiveis += nota_maxima_criterio
            #
            media = (self.total_pontos * 100 / total_pontos_possiveis) / 10
            media = round(media, 2)
        except Exception:
            media = 0.00
        #
        return media

    @property
    def id_encoded(self):
        # ex: "100:::101:::100:::102:::100"  id da avaliação = 100
        id_avaliacao = "{}:::{}:::{}:::{}:::{}".format(
            self.id, self.periodo.processo_progressao.id, self.id, self.avaliador.id, self.id  # id da avaliacao  # id do processo  # id da avaliacao  # id do avaliador
        )  # id da avaliacao
        # codifica em base64
        id_avaliacao = base64.b64encode(id_avaliacao.encode("utf8")).decode("utf8")
        # url safe
        id_avaliacao = id_avaliacao.replace("+", "-")
        id_avaliacao = id_avaliacao.replace("/", "_")
        id_avaliacao = id_avaliacao.replace("=", "aeLqsUliFL")
        #
        return id_avaliacao

    @staticmethod
    def id_decoded(id_encoded):
        try:
            id_avaliacao = id_encoded
            # url safe
            id_avaliacao = id_avaliacao.replace("-", "+")
            id_avaliacao = id_avaliacao.replace("_", "/")
            id_avaliacao = id_avaliacao.replace("aeLqsUliFL", "=")
            #
            ids_avaliacao = base64.b64decode(id_avaliacao.encode("utf8")).decode("utf8").split(":::")
            id_avaliacao_1 = ids_avaliacao[0]  # id da avaliacao na posição 1
            id_avaliacao_2 = ids_avaliacao[2]  # id da avaliacao na posição 3
            id_avaliacao_3 = ids_avaliacao[4]  # id da avaliacao na posição 5
            #
            if not (id_avaliacao_1 == id_avaliacao_2 == id_avaliacao_3):
                id_avaliacao = -1
            else:
                id_avaliacao = id_avaliacao_1
            #
            return id_avaliacao
        except Exception:
            return -1

    @property
    def assinatura_avaliado_is_pendente(self):
        return self.status_avaliacao == self.STATUS_AVALIACAO_AVALIADA and not self.assinatura_avaliado

    @property
    def assinatura_avaliador_is_pendente(self):
        return self.status_avaliacao == self.STATUS_AVALIACAO_AVALIADA and not self.assinatura_avaliador

    @property
    def assinatura_chefe_is_pendente(self):
        return self.status_avaliacao == self.STATUS_AVALIACAO_AVALIADA and not self.assinatura_chefe_imediato

    def assinaturas_realizadas_requeridas(self):
        assinaturas_realizadas = 0
        assinaturas_requeridas = 0
        #
        if self.is_avaliada:
            if self.periodo.processo_progressao.is_tipo_progressao_merito:
                assinaturas_requeridas = 3  # 3 assinaturas por avaliação
                if not self.assinatura_avaliado_is_pendente:
                    assinaturas_realizadas += 1
                if not self.assinatura_avaliador_is_pendente:
                    assinaturas_realizadas += 1
                if not self.assinatura_chefe_is_pendente:
                    assinaturas_realizadas += 1
            else:
                assinaturas_requeridas = 1  # 1 assinatura por avaliação
                if not self.assinatura_chefe_is_pendente:
                    assinaturas_realizadas += 1

        #
        return [assinaturas_realizadas, assinaturas_requeridas]  # num assinaturas realizadas/num assinaturas requeridas

    @staticmethod
    def avaliacoes_como_avaliado(avaliado):
        return ProcessoProgressaoAvaliacao.objects.all().filter(periodo__processo_progressao__avaliado=avaliado)

    @staticmethod
    def avaliacoes_como_avaliador(avaliador):
        return ProcessoProgressaoAvaliacao.objects.all().filter(avaliador=avaliador)

    @staticmethod
    def avaliacoes_como_chefe(chefe, distinct=False):
        ids_periodos_de_avaliacoes_como_chefe = (
            ProcessoProgressaoAvaliacao.objects.all().filter(tipo_avaliador=ProcessoProgressaoAvaliacao.TIPO_AVALIADOR_CHEFE, avaliador=chefe).values_list('periodo', flat=True)
        )
        avaliacoes_responsabilidade_chefe = ProcessoProgressaoAvaliacao.objects.filter(periodo__in=ids_periodos_de_avaliacoes_como_chefe)
        return avaliacoes_responsabilidade_chefe

    @staticmethod
    def avaliacoes_pendentes_a_avaliar(avaliador=None, qs_avaliacoes_como_avaliador=None):
        if avaliador is None and qs_avaliacoes_como_avaliador is None:
            return ValueError
        #
        if not qs_avaliacoes_como_avaliador:
            qs_avaliacoes_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliador(avaliador)
        #
        return qs_avaliacoes_como_avaliador.filter(status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_PENDENTE)

    @staticmethod
    def avaliacoes_avaliadas(avaliador=None, qs_avaliacoes_como_avaliador=None):
        if avaliador is None and qs_avaliacoes_como_avaliador is None:
            return ValueError
        #
        if not qs_avaliacoes_como_avaliador:
            qs_avaliacoes_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliador(avaliador)
        #
        return qs_avaliacoes_como_avaliador.filter(status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA)

    @staticmethod
    def avaliacoes_pendentes_a_assinar_como_avaliado(avaliado=None, qs_avaliacoes_como_avaliado=None):
        if avaliado is None and qs_avaliacoes_como_avaliado is None:
            return ValueError
        #
        if not qs_avaliacoes_como_avaliado:
            qs_avaliacoes_como_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliado(avaliado).filter(
                periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE
            )
        #
        return qs_avaliacoes_como_avaliado.filter(
            periodo__processo_progressao__tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO,
            status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA,
            assinatura_avaliado="",
        )

    @staticmethod
    def avaliacoes_pendentes_a_assinar_como_avaliador(avaliador=None, qs_avaliacoes_como_avaliador=None):
        if avaliador is None and qs_avaliacoes_como_avaliador is None:
            return ValueError
        #
        if not qs_avaliacoes_como_avaliador:
            qs_avaliacoes_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliador(avaliador).filter(
                periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE
            )
        #
        return qs_avaliacoes_como_avaliador.filter(
            periodo__processo_progressao__tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO,
            status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA,
            assinatura_avaliador="",
        )

    @staticmethod
    def avaliacoes_pendentes_a_assinar_como_chefe(chefe=None, qs_avaliacoes_como_chefe=None, distinct=False):
        if chefe is None and qs_avaliacoes_como_chefe is None:
            return ValueError
        #
        if not qs_avaliacoes_como_chefe:
            qs_avaliacoes_como_chefe = ProcessoProgressaoAvaliacao.avaliacoes_como_chefe(chefe, False).filter(
                periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE
            )
        #
        lista = qs_avaliacoes_como_chefe.filter(status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA, assinatura_chefe_imediato="")
        if distinct:
            lista = lista.distinct()
        return lista

    @staticmethod
    def avaliacoes_assinadas_como_avaliado(avaliado=None, qs_avaliacoes_como_avaliado=None):
        if avaliado is None and qs_avaliacoes_como_avaliado is None:
            return ValueError
        #
        if not qs_avaliacoes_como_avaliado:
            qs_avaliacoes_como_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliado(avaliado)
        #
        return qs_avaliacoes_como_avaliado.filter(status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA).exclude(assinatura_avaliado="")

    @staticmethod
    def avaliacoes_assinadas_como_avaliador(avaliador=None, qs_avaliacoes_como_avaliador=None):
        if avaliador is None and qs_avaliacoes_como_avaliador is None:
            return ValueError
        #
        if not qs_avaliacoes_como_avaliador:
            qs_avaliacoes_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliador(avaliador)
        #
        return qs_avaliacoes_como_avaliador.filter(status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA).exclude(assinatura_avaliador="")

    @staticmethod
    def avaliacoes_assinadas_como_chefe(chefe=None, qs_avaliacoes_como_chefe=None, distinct=False):
        if chefe is None and qs_avaliacoes_como_chefe is None:
            return ValueError
        #
        if not qs_avaliacoes_como_chefe:
            qs_avaliacoes_como_chefe = ProcessoProgressaoAvaliacao.avaliacoes_como_chefe(chefe, distinct)
        #
        lista = qs_avaliacoes_como_chefe.filter(status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_AVALIADA).exclude(assinatura_chefe_imediato="")
        if distinct:
            lista = lista.distinct()
        return lista

    def get_assinatura_avaliado_as_html(self):
        if self.assinatura_avaliado:
            return assinatura.quebra_assinatura(self.assinatura_avaliado, 100, assinatura.QUEBRA_LINHA_HTML)
        else:
            return ''

    def get_assinatura_avaliador_as_html(self):
        if self.assinatura_avaliador:
            return assinatura.quebra_assinatura(self.assinatura_avaliador, 100, assinatura.QUEBRA_LINHA_HTML)
        else:
            return ''

    def get_assinatura_chefe_imediato_as_html(self):
        if self.assinatura_chefe_imediato:
            return assinatura.quebra_assinatura(self.assinatura_chefe_imediato, 100, assinatura.QUEBRA_LINHA_HTML)
        else:
            return ''

    class Meta:
        ordering = ('-status_avaliacao', 'avaliador__nome')
        verbose_name = 'Ficha de Avaliação'
        verbose_name_plural = 'Fichas de Avaliações'


#
# Representa uma nota dada em uma avaliacao
#
class AvaliacaoCriterioNota(models.ModelPlus):
    avaliacao = models.ForeignKeyPlus('progressoes.ProcessoProgressaoAvaliacao', on_delete=models.CASCADE)
    criterio_avaliado = models.ForeignKeyPlus('progressoes.AvaliacaoModeloCriterio', on_delete=models.CASCADE)
    nota = models.FloatField()

    def __str__(self):
        return '{} ({})'.format(self.criterio_avaliado, self.nota)

    class Meta:
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
