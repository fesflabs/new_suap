from unicodedata import normalize

__all__ = ['getattr_coalesce', 'get_app_name', 'to_ascii', 'get_qualified_model_name']


def getattr_coalesce(obj: object, attribute: str, default: object = None):
    for attr in attribute.split('.'):
        obj = getattr(obj, attr, None)
        if not obj:
            break
    return obj if obj is not None else default


def get_app_name(function):
    """
    Obtem a aplicação de uma função.

    Args:
        function (Function): função.

    Returns:
         String com o nome da aplicação que contem a função.
    """
    function_path = function.__module__.split('.')
    if 'lps' in function_path:  # the function was defined in the lps module
        return function_path[0]
    elif len(function_path) == 2:  # function is on the project
        return function_path[0]
    return function_path[1]


def to_ascii(txt):
    """
    Converte texto passado para o padrão ASCII.

    Args:
        txt (string): texto a ser convertido.

    Return:
        String codificado no padrão ASCII.
    """
    if not isinstance(txt, str):
        txt = str(txt)
    if isinstance(txt, str):
        txt = txt
    return normalize('NFKD', txt).encode('ASCII', 'ignore').decode('utf-8')


def get_qualified_model_name(model):
    """
    Obtem uma string qualificada do nome do Modelo
    Args:
        mnodel (Model): modelo.

    Returns:
        String no formato 'app_label.Modelo'
    """
    return f'{model._meta.app_label}.{model._meta.model_name}'
