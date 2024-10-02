from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from comum.models import User
import datetime

ONLINE_THRESHOLD = getattr(settings, 'ONLINE_THRESHOLD', 60 * 60 * 24)


def get_online_now(self):
    return User.objects.filter(id__in=self.online_now_ids or [])


class OnlineNowMiddleware(MiddlewareMixin):
    def process_request(self, request):
        uids = cache.get('online-now', [])

        online_keys = ['online-%s' % (u,) for u in uids]
        fresh = list(cache.get_many(online_keys).keys())
        online_now_ids = [int(k.replace('online-', '')) for k in fresh]

        if request.user.is_authenticated:
            uid = request.user.id
            if uid in online_now_ids:
                online_now_ids.remove(uid)
            online_now_ids.append(uid)

        request.__class__.online_now_ids = online_now_ids
        request.__class__.online_now = property(get_online_now)

        cache.set('online-%s' % (request.user.pk,), [datetime.datetime.now(), request.get_full_path()], ONLINE_THRESHOLD)
        cache.set('online-now', online_now_ids, ONLINE_THRESHOLD)
