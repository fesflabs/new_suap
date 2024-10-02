__all__ = ['get_tl']


def get_tl():
    """
    Obtem o **ThreadLocals**.

    Returns:
        ThreadLocals.
    """
    from djtools.middleware import threadlocals as tl

    return tl
