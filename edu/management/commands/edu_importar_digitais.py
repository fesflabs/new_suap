from sentry_sdk import capture_exception

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        from edu.siabi_digitais import DAO
        try:
            dao = DAO()
            dao.atualizar_digitais(verbose=1)
        except Exception as error:
            capture_exception(error)
