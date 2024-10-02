# coding: utf-8

from rest_framework.permissions import BasePermission

from djtools.testutils import running_tests


def application_from_request(request):
    return request.auth and getattr(request.auth, 'application', None) or None


class TokenFromTrustedApp(BasePermission):
    def has_permission(self, request, view):
        if running_tests():
            return True
        application = application_from_request(request)
        return application and application.skip_authorization
