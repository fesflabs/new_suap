from django.db.backends.postgresql import base
from djtools.db.backends.postgresql.schema import SuapDatabaseSchemaEditor


class DatabaseWrapper(base.DatabaseWrapper):
    SchemaEditorClass = SuapDatabaseSchemaEditor
