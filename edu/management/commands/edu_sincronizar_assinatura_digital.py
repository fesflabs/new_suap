from edu.models import AssinaturaDigital
from edu.diploma_digital.rap import AssinadorDigital
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        return
        assinador = AssinadorDigital(debug=True)
        for assinatura_digital in AssinaturaDigital.objects.filter(concluida=False, data_revogacao__isnull=True):
            try:
                assinador.sincronizar(assinatura_digital)
            except BaseException:
                print('Erro ao sincronizar assinatura digital #{}'.format(assinatura_digital.id))
