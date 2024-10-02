from social_django.middleware import SocialAuthExceptionMiddleware


class CustomSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    def raise_exception(self, request, exception):
        return False
