# coding: utf-8

import setproctitle
from datetime import datetime

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

proctitle_prefix = getattr(settings, 'PROCTITLE_PREFIX', '[django]')


class ChangeProcessNameMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user:
            username = hasattr(request, 'user') and request.user.id and request.user.username or 'anonymous'
        elif request.auth and request.auth.application:
            username = '{}'.format(request.auth.token or request.auth.application.client_id) or request.auth.application.user.username

        request.start_time = datetime.now()
        setproctitle.setproctitle('RUNNING {} {} (since {}) USER: {}'.format(proctitle_prefix, request.get_full_path(), request.start_time, username))

    def process_response(self, request, response):
        if request.user:
            username = hasattr(request, 'user') and request.user.id and request.user.username or 'anonymous'
        elif request.auth and request.auth.application:
            username = '{}'.format(request.auth.token or request.auth.application.client_id) or request.auth.application.user.username

        if hasattr(request, 'start_time'):  # HttpResponseRedirect does not have `start_time` attr
            response_time = (datetime.now() - request.start_time).total_seconds()
        else:
            response_time = 0
        setproctitle.setproctitle('FINISHED {} {} (in {}s) LAST USER: {}'.format(proctitle_prefix, request.get_full_path(), response_time, username))
        return response
