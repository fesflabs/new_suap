from djtools.management.commands import BaseCommandPlus
from datetime import timedelta, datetime
from estagios.models import PraticaProfissional


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        # Notificando o pessoal sobre os Planos de Atividades de Estágio (PAEs) que estão para vencer.
        #
        # A notificação deve ser enviada a: Alunos, Supervisores e Orientadores envolvidos no Estágio,
        # bem como aos Coordenadores de Estágio do campus correspondente.
        #
        # Esse envio deve ocorrer a 15 dias do vencimento do PAE, que se vence em 6 meses, contados
        # a partir de sua data de início.
        # Isso equivale a 5 meses e meio de vigência, algo em torno de 167 dias.

        cinco_meses_e_meio = timedelta(days=167)
        seis_meses = timedelta(days=180)
        data_inicio_estagios_a_vencer = datetime.now().date() - cinco_meses_e_meio
        data_limite = data_inicio_estagios_a_vencer + seis_meses

        estagios = PraticaProfissional.objects.filter(tipo=PraticaProfissional.TIPO_ESTAGIO, data_inicio=data_inicio_estagios_a_vencer)
        for estagio in estagios:
            try:
                estagio.notificar_aluno_necessidade_atualizacao_pae(data_limite)
                estagio.notificar_supervisor_aluno_necessidade_atualizacao_pae(data_limite)
                estagio.notificar_orientador_necessidade_atualizacao_pae(data_limite)
                estagio.notificar_coordenadores_extensao_necessidade_atualizacao_pae(data_limite)
            except Exception:
                print(f'Erro ao notificar sobre vencimento do Plano de Atividades do estágio: {estagio.pk}')
