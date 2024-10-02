
from django.conf import settings


class DictObj:
    def __init__(self, in_dict: dict):
        assert isinstance(in_dict, dict)
        for key, val in in_dict.items():
            if isinstance(val, (list, tuple)):
                setattr(self, key, [DictObj(x) if isinstance(x, dict) else x for x in val])
            else:
                setattr(self, key, DictObj(val) if isinstance(val, dict) else val)


def extrair_matriculas_no_diario(diario):
    if diario:
        alunos = diario.get_alunos_ativos()
        return alunos.values_list('matricula_periodo__aluno__matricula', flat=True)
    return []


def labvirtual_esta_instalada():
    return 'labvirtual' in settings.INSTALLED_APPS
