from comum.tests import SuapTestCase
from processo_eletronico.models import TipoProcesso, Processo


class TestCadastroTipoProcesso(SuapTestCase):
    '''
    Teste para criacao de Tipo de Processo
    '''
    @staticmethod
    def criar_tipo_processo():
        tipo_processo, _ = TipoProcesso.objects.get_or_create(
            nome='Inclusão de dependente',
            nivel_acesso_default=Processo.NIVEL_ACESSO_PUBLICO
        )
        super().assertIsInstance(tipo_processo, TipoProcesso)

    def setUp(self):
        self.criar_tipo_processo()
        super().setUp()
