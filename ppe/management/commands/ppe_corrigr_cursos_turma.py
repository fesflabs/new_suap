from djtools.management.commands import BaseCommandPlus
from ppe.models import CursoTurma


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        verbose = str(options.get('verbosity', '0')) != '0'
        qs = CursoTurma.objects.all()
        for curso in qs:
            curso.save()

