from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from djtools.unaccent_field import UnaccentField


class SuapDatabaseSchemaEditor(DatabaseSchemaEditor):
    def __prepare_database(self):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT exists(select 1 from pg_proc where proname =  \'unaccent\')")
                tem_extensao_unaccent = cursor.fetchall()[0][0]
                if not tem_extensao_unaccent:
                    cursor.execute("CREATE EXTENSION unaccent;")

                cursor.execute("SELECT exists(select 1 from pg_proc where proname like  \'%trgm%\')")
                tem_pg_trgm = cursor.fetchall()[0][0]
                if not tem_pg_trgm:
                    cursor.execute("CREATE EXTENSION pg_trgm;")

                cursor.execute("SELECT exists(select 1 from pg_proc where proname =  \'f_unaccent\')")
                tem_f_unaccent = cursor.fetchall()[0][0]
                if not tem_f_unaccent:
                    cursor.execute(
                        """
                        CREATE OR REPLACE FUNCTION f_unaccent(text)
                          RETURNS text AS
                        $func$
                        SELECT unaccent('unaccent', upper($1))
                        $func$  LANGUAGE sql IMMUTABLE SET search_path = public, pg_temp;
                    """
                    )
        except Exception:
            raise

    def _create_unaccent_index_sql(self, model, field):
        db_type = field.db_type(connection=self.connection)
        # if db_type is not None and (field.db_index or field.unique):
        if db_type is not None:
            if '[' in db_type:
                return None
            if isinstance(field, UnaccentField):
                self.__prepare_database()
                statement = self._create_index_sql(model, fields=[field], suffix='_unaccent_gin')
                statement.template = "CREATE INDEX %(name)s ON %(table)s USING GIN (f_unaccent(%(columns)s) gin_trgm_ops) %(extra)s"
                return statement
            else:
                return None
        return None

    def _create_unaccent_index_btree_sql(self, model, field):
        db_type = field.db_type(connection=self.connection)
        # if db_type is not None and (field.db_index or field.unique):
        if db_type is not None:
            if '[' in db_type:
                return None
            if isinstance(field, UnaccentField):
                self.__prepare_database()
                statement = self._create_index_sql(model, fields=[field], suffix='_unaccent_btree')
                statement.template = "CREATE INDEX %(name)s ON %(table)s USING BTREE (f_unaccent(%(columns)s)) %(extra)s"
                return statement
            else:
                return None
        return None

    # override method
    def _constraint_names(self, model, column_names=None, unique=None, primary_key=None, index=None, foreign_key=None, check=None, type_=None, exclude=None):
        result = super()._constraint_names(model, column_names, unique, primary_key, index, foreign_key, check, type_, exclude)

        # tratamento específico para o índice f_unaccent
        with self.connection.cursor() as cursor:
            constraints = self.connection.introspection.get_constraints(cursor, model._meta.db_table)
        for name, infodict in constraints.items():
            if infodict['definition'] and f'f_unaccent(({column_names[0]})' in infodict['definition']:
                result.append(name)
        # print("\n_constraint_names", result)
        return result

    # override method
    def _model_indexes_sql(self, model):
        # retorna uma lista de instruções sql nativa do django para criação de índices
        output = super()._model_indexes_sql(model)

        # tratamento específico para o índice f_unaccent
        unaccent_fields = [field for field in model._meta.local_fields if isinstance(field, UnaccentField)]
        if unaccent_fields:
            # retorna a instrução sql para criar o índice f_unaccent do tipo btree e gin
            output = []
            for unaccent_field in unaccent_fields:
                sql = self._create_unaccent_index_sql(model, unaccent_field)
                output.append(sql)
            for unaccent_field in unaccent_fields:
                sql = self._create_unaccent_index_btree_sql(model, unaccent_field)
                output.append(sql)
        # print('_model_indexes_sql', output)
        return output

    # override method
    def _alter_field(self, model, old_field, new_field, old_type, new_type, old_db_params, new_db_params, strict=False):
        super()._alter_field(model, old_field, new_field, old_type, new_type, old_db_params, new_db_params, strict)

        # print('\n_alter_field...')
        # Remove os índices antigos e cria o índice para a função f_unaccent se alterou o campo para UnaccentField
        if not isinstance(old_field, UnaccentField) and isinstance(new_field, UnaccentField):
            # remove todos os índices do campo old_field.column
            # print('1...')
            index_names = self._constraint_names(model, [old_field.column], index=True)
            # print('1 %s' % index_names)
            for index_name in index_names:
                # print('Removendo índice: %s' %index_name)
                self.execute(self._delete_constraint_sql(self.sql_delete_index, model, index_name))

            # cria o índice unaccent do tipo gin
            unaccent_index_statement = self._create_unaccent_index_sql(model, new_field)
            if unaccent_index_statement is not None:
                # print('Criando índice f_unaccent gin: %s' %unaccent_index_statement)
                self.execute(unaccent_index_statement)
            # cria o índice unaccent do tipo btree
            unaccent_index_statement = self._create_unaccent_index_btree_sql(model, new_field)
            if unaccent_index_statement is not None:
                # print('Criando índice f_unaccent btree: %s' %unaccent_index_statement)
                self.execute(unaccent_index_statement)

        # Remove os índices antigos caso db_index tenha mudado de true para false e somente se for uma instância da classe UnaccentField
        if isinstance(new_field, UnaccentField) and (old_field.db_index and not new_field.db_index):
            # remove todos os índices _unaccent
            # print('2...')
            index_names = self._constraint_names(model, [old_field.column], index=True)
            # print('2 %s' % index_names)
            for index_name in index_names:
                # print('Removendo índice: %s' %index_name)
                self.execute(self._delete_constraint_sql(self.sql_delete_index, model, index_name))

        # Remove os índices antigos caso o campo tenha alterado de UnaccentField para outro field
        if isinstance(old_field, UnaccentField) and not isinstance(new_field, UnaccentField):
            # print('3...')

            # remove todos os índices _unaccent
            index_names = self._constraint_names(model, [old_field.column], index=True)
            # print('3 %s' % index_names)
            for index_name in index_names:
                # print('Removendo índice: %s' %index_name)
                self.execute(self._delete_constraint_sql(self.sql_delete_index, model, index_name))

            # caso db_index seja true, deve-se criar os índices para o novo field
            if new_field.db_index or old_field.unique:
                # print('3.1..')
                index_name = self._create_index_sql(model, fields=[new_field])
                # print('Criando índice %s' % index_name)
                self.execute(index_name)

                like_index_statement = self._create_like_index_sql(model, new_field)
                # print('Criando índice %s' % like_index_statement)
                if like_index_statement is not None:
                    self.execute(like_index_statement)

        # cria o índice unaccent caso db_index tenha mudado de false para true e somente se for uma instância da classe UnaccentField
        if (
            isinstance(old_field, UnaccentField)
            and isinstance(new_field, UnaccentField)
            and (not old_field.db_index and new_field.db_index)
            or (not old_field.unique and new_field.unique)
        ):
            # print('5...')
            index_unaccent_already_exists = False
            # remove todos os índices que não seja para f_unaccent
            index_names = self._constraint_names(model, [old_field.column], index=True)
            # print('5 %s' % index_names)
            for index_name in index_names:
                if not 'unaccent' in index_name:
                    # print('Removendo índice: %s' %index_name)
                    self.execute(self._delete_constraint_sql(self.sql_delete_index, model, index_name))
                else:
                    index_unaccent_already_exists = True

            # Se já existir índice para função f_unaccent, não precisa criar novamente.
            if not index_unaccent_already_exists:
                # cria o índice unaccent do tipo gin
                unaccent_index_statement = self._create_unaccent_index_sql(model, new_field)
                if unaccent_index_statement is not None:
                    # print('Criando índice f_unaccent do tipo gin: %s' %unaccent_index_statement)
                    self.execute(unaccent_index_statement)
                # cria o índice unaccent do tipo btree
                unaccent_index_statement = self._create_unaccent_index_btree_sql(model, new_field)
                if unaccent_index_statement is not None:
                    # print('Criando índice para f_unaccent do tipo btree: %s' %unaccent_index_statement)
                    self.execute(unaccent_index_statement)
