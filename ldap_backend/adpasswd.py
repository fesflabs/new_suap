#!/usr/bin/env python

"""adpasswd.py Command line interface to change Active Directory Passwords via LDAP.
Copyright 2009 Craig Sawyer
email: csawyer@yumaed.org
license: GPLv2 see LICENSE.txt
"""

import ldap

ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)


class InvalidConfigException(Exception):
    pass


class ADInterface(object):
    def __init__(self, host, port, binddn, bindpw, searchdn):
        self.conn = None
        self.config = dict(host=host, port=port, binddn=binddn, bindpw=bindpw, searchdn=searchdn)
        self.connect()

    def connect(self):
        """Connect to AD thru LDAP"""
        connection_string = 'ldaps://{}:{}'.format(self.config['host'], self.config['port'])
        self.conn = ldap.initialize(connection_string)
        self.conn.set_option(ldap.OPT_REFERRALS, 0)
        user = self.config['binddn']
        password = self.config['bindpw']
        self.conn.simple_bind_s(user, password)

    def makepassword(self, pw):
        return [''.join(('"', pw, '"')).encode('utf-16-le')]

    def modify(self, dn, attr, values, mode='replace'):
        return self.conn.modify_s(dn, [(ldap.MOD_REPLACE, attr, values)])

    def findUser(self, name):
        userDN = None
        x = self.conn.search('sAMAccountName=%s' % (name), self.config['searchdn'], attributes=['distinguishedName'])
        # print 'num results:',len(x)
        if len(x) > 1:
            # print 'returned:',x[0].keyvals
            userDN = x[0].keyvals['distinguishedName'][0]
        return userDN

    # Begin API Calls
    def changepass(self, user, passwd):
        """call with string, user and passwd """
        passwd = self.makepassword(passwd)
        user = self.findUser(user)
        if not user:
            raise Exception('Invalid Username, user not found.')
        return self.modify(user, 'unicodePwd', passwd)

    def changepass_by_dn(self, dn, passwd):
        """call with string, user and passwd """
        passwd = self.makepassword(passwd)
        return self.modify(dn, 'unicodePwd', passwd)
