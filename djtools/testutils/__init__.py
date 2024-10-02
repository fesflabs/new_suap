# -*- coding: utf-8 -*-


def running_tests():
    """
    Verifica a execução, atual, está sendo a partir dos testes.

    Returns:
         True se a execução for a partir dos testes.
    """
    import sys

    return 'test_suap' in sys.argv or 'test' in sys.argv or 'test_behave' in sys.argv
