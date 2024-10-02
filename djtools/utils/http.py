__all__ = ['is_ajax', 'get_client_ip']


def is_ajax(request):
    return (hasattr(request, 'headers') and request.headers.get('x-requested-with') == 'XMLHttpRequest') or (hasattr(request, 'META') and request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest')


def get_client_ip(request):
    """
    Obtem o **IP** do cliente que realizou uma requisição.

    Args:
        request (HttpREquest): objeto request.

    Returns:
        String com o IP do cliente.
    """
    for attr in ('HTTP_X_REAL_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'):
        if request.META.get(attr):
            return request.META.get(attr)
