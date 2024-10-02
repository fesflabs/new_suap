from edu.models.logs import LogModel
from djtools.db import models
from comum.utils import tl

class HistoricoRelatorioPpe(LogModel):
    TIPO_TRABALHADOR_EDUCANDO = 1
    TIPO_TRABALHO_CONCLUSAO_CURSO = 2
    TIPO_CHOICES = [[TIPO_TRABALHADOR_EDUCANDO, 'Trabalhador Educando'], ]

    URL_CHOICES = [[TIPO_TRABALHADOR_EDUCANDO, '/edu/relatorio/'], ]

    user = models.CurrentUserField()
    descricao = models.CharFieldPlus()
    query_string = models.TextField()
    tipo = models.PositiveIntegerField(choices=TIPO_CHOICES)

    class Meta:
        verbose_name = 'Histórico de Relatório'
        verbose_name_plural = 'Histórico de Relatórios'

    def get_url_sem_parametro(self):
        return self.URL_CHOICES[self.tipo - 1][1]

    def get_url(self):
        url = '{}?{}'.format(self.get_url_sem_parametro(), bytes.fromhex(self.query_string).decode("utf-8"))
        return url

    def delete(self, *args, **kwargs):
        if self.user == tl.get_user():
            super().delete(*args, **kwargs)
        else:
            raise Exception('Usuário não tem permissão para excluir')