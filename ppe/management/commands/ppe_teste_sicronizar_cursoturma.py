from djtools.management.commands import BaseCommandPlus
from ppe import moodle
from ppe.models import CursoTurma



class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        obj = CursoTurma.objects.get(pk=50)
        moodle.verificar_curso(obj.nome_breve_curso_moodle)





