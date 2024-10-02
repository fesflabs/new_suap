class LdapModificationFailed(Exception):
    """The AD Group could not be modified."""
    pass


class LdapGroupDoesNotExist(Exception):
    pass
