# -*- coding: utf-8 -*

from django.contrib.auth.models import Group
from django.apps import apps

from comum.tests import SuapTestCase
from rh.models import PessoaFisica, GrupoCargoEmprego, CargoEmprego
from saude.models import (
    Prontuario,
    Vinculo,
    Atendimento,
    SinaisVitais,
    Antropometria,
    AcuidadeVisual,
    AntecedentesFamiliares,
    ProcessoSaudeDoenca,
    HabitosDeVida,
    DesenvolvimentoPessoal,
    InformacaoAdicional,
    PercepcaoSaudeBucal,
    ExameFisico,
    Doenca,
    SituacaoAtendimento,
    Odontograma,
    SituacaoClinica,
)
from edu.models import Aluno, SituacaoMatricula
from comum.models import Ano
import datetime

Permission = apps.get_model('auth', 'permission')
User = apps.get_model('auth', 'user')


class SaudeTestCase(SuapTestCase):
    def setUp(self):
        super(SaudeTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Saúde Sistêmico'))
        self.servidor_a.user.save()

        grupo_teste = GrupoCargoEmprego.objects.create(codigo='10', nome='Grupos Testes', sigla='TESTES', categoria='tecnico_administrativo', excluido=False)
        self.cargo_tec_enf = CargoEmprego.objects.create(codigo='701233', nome='TECNICO EM ENFERMAGEM', grupo_cargo_emprego=grupo_teste, sigla_escolaridade='NI')

        self.cargo_odontologo = CargoEmprego.objects.create(codigo='701064', nome='ODONTOLOGO', grupo_cargo_emprego=grupo_teste, sigla_escolaridade='NS')

        self.cargo_medico = CargoEmprego.objects.create(codigo='701047', nome='MEDICO-AREA', grupo_cargo_emprego=grupo_teste, sigla_escolaridade='NS')

        self.servidor_d.user.groups.add(Group.objects.get(name='Técnico em Enfermagem'))
        self.servidor_d.user.save()
        self.client.login(username=self.servidor_d.user.username, password='123')
        self.doenca_a = Doenca.objects.create(nome='Doença A', ativo=True)
        self.doenca_b = Doenca.objects.create(nome='Doença B', ativo=True)
        SituacaoClinica.objects.get_or_create(descricao="Cárie", categoria="red", preenchimento="1", cpod="C")

    def acessar_como_sistemico(self):
        self.logout()
        successful = self.client.login(user=self.servidor_a.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_tec_enfermagem(self):
        self.logout()
        self.servidor_d.cargo_emprego = self.cargo_tec_enf
        self.servidor_d.save()
        successful = self.client.login(user=self.servidor_d.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_odontologo(self):
        self.logout()
        self.servidor_d.cargo_emprego = self.cargo_odontologo
        self.servidor_d.save()
        successful = self.client.login(user=self.servidor_d.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_medico(self):
        self.logout()
        self.servidor_d.cargo_emprego = self.cargo_medico
        self.servidor_d.save()
        successful = self.client.login(user=self.servidor_d.user)
        self.assertEqual(successful, True)
        return self.client.user

    def test_cadastrar_avaliacao_biomedica(self):
        self.acessar_como_sistemico()
        p_fisica = PessoaFisica.objects.get_or_create(nome='Carlos Breno Pereira Silva', defaults={'cpf': '359.221.769-00'})[0]

        ano = Ano.objects.get_or_create(ano=2016)[0]
        situacao = SituacaoMatricula.objects.get_or_create(descricao='Matriculado', ativo=True)[0]
        aluno = Aluno.objects.create(pessoa_fisica=p_fisica, ano_letivo=ano, periodo_letivo=1, situacao=situacao, ano_let_prev_conclusao=datetime.datetime.now().year)
        prontuario = Prontuario.get_prontuario(aluno.get_vinculo())
        count = Atendimento.objects.all().count()
        vinculo = Vinculo.get_vinculos(p_fisica)[0]
        url = '/saude/abrir_atendimento/1/{}/{}/{}/'.format(prontuario.id, vinculo.vinculo, vinculo.id)
        response = self.client.get(url)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/1/', status_code=302)
        self.assertEqual(Atendimento.objects.all().count(), count + 1)

        self.acessar_como_tec_enfermagem()
        atendimento = Atendimento.objects.latest('id')

        url = '/saude/adicionar_sinaisvitais/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Sinais Vitais', status_code=200)
        count = SinaisVitais.objects.all().count()
        input = dict(pressao_sistolica=120, pressao_diastolica=80, pulsacao=45, temperatura_categoria=SinaisVitais.HIPOTERMIA, respiracao_categoria=SinaisVitais.BRADIPNEICO)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_sinais_vitais'.format(atendimento.id), status_code=302)
        self.assertEqual(SinaisVitais.objects.all().count(), count + 1)

        url = '/saude/adicionar_antropometria/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Antropometria', status_code=200)
        count = Antropometria.objects.all().count()
        input = dict(estatura=170, peso=80, sentimento_relacao_corpo='Muito satisfeito(a)', periodo_sem_comida='Nunca')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_antropometria'.format(atendimento.id), status_code=302)
        self.assertEqual(Antropometria.objects.all().count(), count + 1)

        url = '/saude/adicionar_acuidadevisual/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Acuidade Visual', status_code=200)
        count = AcuidadeVisual.objects.all().count()
        input = dict(olho_esquerdo='20/20', olho_direito='10/20')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_acuidade_visual'.format(atendimento.id), status_code=302)
        self.assertEqual(AcuidadeVisual.objects.all().count(), count + 1)

        url = '/saude/adicionar_antecedentesfamiliares/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Antecedentes Familiares', status_code=200)
        count = AntecedentesFamiliares.objects.all().count()
        input = dict(agravos_primeiro_grau=self.doenca_a.id, agravos_segundo_grau=self.doenca_b.id)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_antecedentes'.format(atendimento.id), status_code=302)
        self.assertEqual(AntecedentesFamiliares.objects.all().count(), count + 1)

        url = '/saude/adicionar_processosaudedoenca/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Processo Saúde-Doença', status_code=200)
        count = ProcessoSaudeDoenca.objects.all().count()
        input = dict(fez_cirurgia=True, que_cirurgia='Cirurgia de retirada de apêndice')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_antecedentes'.format(atendimento.id), status_code=302)
        self.assertEqual(ProcessoSaudeDoenca.objects.all().count(), count + 1)

        url = '/saude/adicionar_habitosdevida/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Hábitos de Vida', status_code=200)
        count = HabitosDeVida.objects.all().count()
        input = dict(
            dificuldade_dormir=True,
            atividade_fisica=True,
            qual_atividade='corrida',
            frequencia_semanal=3,
            duracao_atividade=3,
            fuma=True,
            frequencia_fumo=2.0,
            usa_drogas=False,
            bebe=True,
            frequencia_bebida=2,
            horas_sono=2,
            refeicoes_por_dia=4,
            vida_sexual_ativa=False,
            uso_internet=False,
            tempo_uso_internet=3,
        )
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_habitosdevida'.format(atendimento.id), status_code=302)
        self.assertEqual(HabitosDeVida.objects.all().count(), count + 1)

        url = '/saude/adicionar_desenvolvimentopessoal/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Desenvolvimento Pessoal', status_code=200)
        count = DesenvolvimentoPessoal.objects.all().count()
        input = dict(problema_aprendizado=True, qual_problema_aprendizado='Dificuldade em aprender')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_desenvolvimentopessoal'.format(atendimento.id), status_code=302)
        self.assertEqual(DesenvolvimentoPessoal.objects.all().count(), count + 1)

        url = '/saude/adicionar_informacao_adicional/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Informação Adicional', status_code=200)
        count = InformacaoAdicional.objects.all().count()
        input = dict(informacao='Texto com a informação adicional.')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_informacaoadicional'.format(atendimento.id), status_code=302)
        self.assertEqual(InformacaoAdicional.objects.all().count(), count + 1)

        self.acessar_como_odontologo()
        url = '/saude/adicionar_percepcaosaudebucal/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Percepção Bucal', status_code=200)
        count = PercepcaoSaudeBucal.objects.all().count()
        input = dict(qtd_vezes_fio_dental_ultima_semana=2)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_percepcaosaudebucal'.format(atendimento.id), status_code=302)
        self.assertEqual(PercepcaoSaudeBucal.objects.all().count(), count + 1)

        url = '/saude/adicionar_odontograma/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Odontograma', status_code=200)
        count = Odontograma.objects.all().count()
        situacao_clinica = SituacaoClinica.objects.all()[0]
        input = dict(situacao_clinica=situacao_clinica.pk)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_odontograma'.format(atendimento.id), status_code=302)
        self.assertEqual(Odontograma.objects.all().count(), count)

        self.acessar_como_medico()
        url = '/saude/adicionar_examefisico/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Exame Físico', status_code=200)
        count = ExameFisico.objects.all().count()
        input = dict(ectoscopia_alterada=True, alteracao_ectoscopia='Descrição da alteração')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/avaliacao_biomedica/{}/?tab=aba_examefisico'.format(atendimento.id), status_code=302)
        self.assertEqual(ExameFisico.objects.all().count(), count + 1)

        url = '/saude/fechar_atendimento/{}/'.format(atendimento.id)
        response = self.client.get(url)
        self.assertContains(response, 'Fechar Atendimento', status_code=200)
        count = Atendimento.objects.filter(situacao=SituacaoAtendimento.FECHADO).count()
        input = dict(obs_fechado='Obs ao fechar o atendimento')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/saude/prontuario/{}/?tab=aba_avaliacao_biomedica'.format(aluno.get_vinculo().id), status_code=302)
        self.assertEquals(Atendimento.objects.filter(situacao=SituacaoAtendimento.FECHADO).count(), count + 1)
