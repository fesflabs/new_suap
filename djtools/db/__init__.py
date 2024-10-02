# -*- coding: utf-8 -*-
# pylint: skip-file

import psycopg2
from django.db import transaction


def get_connection(conn):
    if not conn:
        from django.db import connection
    else:
        connection = psycopg2.connect(**conn)
    return connection


@transaction.atomic
def get_dict(query_string, args=None, show_info=False, conn=None):
    connection = get_connection(conn)
    cursor = connection.cursor()
    try:
        cursor.execute(query_string, args or None)
    except Exception as e:
        connection.rollback()
        raise e
    col_names = [desc[0] for desc in cursor.description]
    result = []
    for row in cursor.fetchall():
        row_dict = dict(list(zip(col_names, row)))
        result.append(row_dict)
    if not show_info:
        return result
    else:
        time = connection.queries and connection.queries[-1]['time'] or '?'
        return dict(cols=col_names, time=time, result=result, total_rows=len(result))


def get_dict_dict(query_string, key, conn=None):
    """ Return a dict of dict.
        Ex:
        >>> sql = ''SELECT field1, field2 FROM table''
        >>> get_dict_dict(sql, field1) 
        {'key1': {'field1': 'key1', 'field2': 'value'},
         'key2': {'field1': 'key2', 'field2': 'value'}}
    """
    dict = get_dict(query_string, conn)
    dict_dict = {}
    for d in dict:
        dict_dict[d[key]] = d

    return dict_dict


@transaction.atomic
def get_list(query_string, conn=None, args=None):
    connection = get_connection(conn)
    cursor = connection.cursor()
    try:
        cursor.execute(query_string, args or None)
    except Exception as e:
        connection._rollback()
        raise e
    result = []
    for row in cursor.fetchall():
        result.append(list(row))

    # If each row returns one value, let`s flat this
    # ((1,), (2,)) -> (1, 2)
    if result and len(result[0]) == 1:
        result = [row[0] for row in result]

    return result


@transaction.atomic
def get_list_extra(query_string, conn=None):
    connection = get_connection(conn)
    cursor = connection.cursor()
    try:
        cursor.execute(query_string)
    except Exception as e:
        connection.rollback()
        raise e
    colnames = [desc[0] for desc in cursor.description]
    result = []
    for row in cursor.fetchall():
        result.append(row)

    # If each row returns one value, let`s flat this
    # ((1,), (2,)) -> (1, 2)
    if result and len(result[0]) == 1:
        result = [row[0] for row in result]

    return dict(rows=result, colnames=colnames)


# Util functions


def has_column(table_name, column_name, conn=None):
    try:
        sql = """select 1 
                        from pg_catalog.pg_attribute a 
                        where a.attrelid = (select oid 
                                                    from pg_catalog.pg_class 
                                                    where relname = '%s') 
                            and a.attname = '%s';""" % (
            table_name,
            column_name,
        )
        r = get_list(sql, conn=conn)[0]
        return bool(r)
    except Exception:
        return False


def has_columntype(table_name, column_name, column_type, conn=None):
    try:
        sql = """select 1 
                        from pg_catalog.pg_attribute a 
                        where a.attrelid = (select oid 
                                                    from pg_catalog.pg_class 
                                                    where relname = '%s') 
                            and a.attname = '%s' 
                            and pg_catalog.format_type(a.atttypid, a.atttypmod) = '%s';""" % (
            table_name,
            column_name,
            column_type,
        )
        r = get_list(sql, conn=conn)[0]
        return bool(r)
    except Exception:
        return False


def has_constraint(constraint_name, conn=None):
    try:
        sql = """SELECT 1 FROM pg_constraint WHERE conname = '%s'""" % (constraint_name)
        r = get_list(sql, conn=conn)[0]
        return bool(r)
    except Exception:
        return False


def has_index(table_name, index_name, conn=None):
    try:
        sql = """SELECT 1 FROM pg_indexes WHERE tablename = '%s' and indexname like '%s%%'""" % (table_name, index_name)
        r = get_list(sql, conn=conn)[0]
        return bool(r)
    except Exception:
        return False


def has_constrainttype(constraint_name, rel_table, conn=None):
    try:
        sql = """Select 1 FROM pg_constraint r
                    Inner Join pg_catalog.pg_class T on t.oid = r.conrelid 
                    Inner Join pg_catalog.pg_class X on X.oid = r.confrelid
                    Where conname = '%s' and X.relname = '%s';""" % (
            constraint_name,
            rel_table,
        )
        r = get_list(sql, conn=conn)[0]
        return bool(r)
    except Exception:
        return False


def get_table_columns(table_name, conn=None):
    connection = get_connection(conn)
    cursor = connection.cursor()
    cursor.execute('select * from %s where 1 = 2' % table_name)
    return [desc[0] for desc in cursor.description]


def get_table_column_size(table_name, column_name, conn=None):
    connection = get_connection(conn)
    cursor = connection.cursor()
    cursor.execute('select * from %s where 1 = 2' % table_name)
    for desc in cursor.description:
        if desc[0] == column_name:
            return str(desc[3])
    return ''


def is_null_column(table_name, column_name, conn=None):
    """ Return True if table_name.column_name allows null values, False otherwise """
    sql = """select attnotnull   
                        from pg_catalog.pg_attribute a 
                        where a.attrelid = (select oid 
                                                    from pg_catalog.pg_class 
                                                    where relname = '%s') 
                            and a.attname = '%s';""" % (
        table_name,
        column_name,
    )
    r = get_list(sql, conn=conn)[0]
    return not bool(r)


def table_exists(table_name, conn=None):
    r = get_list("select count(*) from information_schema.tables where table_name " "= '%s'" % table_name, conn=conn)
    return bool(r[0])


def drop_table(table_name, conn=None):
    if table_exists(table_name):
        connection = get_connection(conn)
        cursor = connection.cursor()
        cursor.execute("drop table %s" % table_name)
        connection._commit()


def sequence_is_owned_by(sequence, column, conn=None):
    """ Return True if the sequence is owned by the column, False otherwise.
        The column param must be the table.colum format
    """
    tablename = column.split('.')[0]
    attname = column.split('.')[1]
    sql = " SELECT pg_get_serial_sequence('%s', '%s')" % (tablename, attname)
    r = get_list(sql, conn=conn)
    s = None
    if r[0]:
        s = r[0]
        s = s.split('.')[1]
    return s == sequence
