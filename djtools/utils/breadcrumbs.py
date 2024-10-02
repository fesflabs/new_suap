__all__ = ['breadcrumbs_add', 'breadcrumbs_previous_url']


def breadcrumbs_add(request, ctx):
    """
    Adiciona um item ao breadcrumbs.

    Args:
        request (HttpRequest): objeto request;
        ctx (dict): dicionário contendo o contexto guardado na sessão.
    """
    bc = request.session.get('bc', [['Início', '/']])
    title = str(ctx.get('title', ''))
    if not title:  # Não tem title definido, tenta montar baseado na URL
        path_splited = request.path.split('/')
        path_splited.reverse()
        for i in path_splited:
            if i and not i.isdigit():
                title = i.replace('_', ' ').capitalize()
                break
    if request.path == '/':
        bc = [['Início', '/']]

    # Removendo os breadcrumbs que já passaram do título
    found_title = False
    i = 0
    for key, val in bc:
        i += 1
        try:
            if found_title:
                bc.pop()
            if title == key:
                found_title = True
                bc.pop(i)
        except Exception:
            continue
    if not [title, request.get_full_path()] in bc:
        bc.append([title, request.get_full_path()])
    request.session['bc'] = bc
    ctx['breadcrumbs'] = bc


def breadcrumbs_previous_url(request):
    """
    Obtem a **URL** anterior no breadcrumbs.

    Args:
        request (HttpRequest): objeto request.

    Returns:
         String contendo a **URL** solicitada.

    Note:
        É esperado que no objeto request contenha a chave 'bc'.
    """
    if 'bc' in request.session:
        bc = request.session['bc']
        if len(bc) > 1:
            return bc[-2][1]
        return bc[-1][1]
    elif request.user.is_anonymous:
        return f'/accounts/login/?next={request.path}'
    return request.path
