import os

from django.conf import settings
from django.conf.urls import include
from django.urls import path
from django.contrib import admin
from django.conf.urls.static import static
from django.contrib.auth import views
from django.views.static import serve

from comum import webservice, views as comum_views
from djtools import utils
from djtools.testutils import running_tests
from djtools.utils import response

admin.autodiscover()

handler403 = 'comum.views.permission_denied'
handler404 = 'comum.views.page_not_found'
handler500 = 'comum.views.handler500'

urlpatterns = [
    path('', comum_views.index),
    path('docs/<str:path>', comum_views.docs, {'tipo': 'tecnica'}),
    path('manuais/<str:path>', comum_views.docs, {'tipo': 'usuario'}),
    path('robots.txt', comum_views.robots)
]

urlpatterns += [path('apagar_chave_sessao/<str:chave>/', response.apagar_chave_sessao)]

urlpatterns += [
    path('autocompletar/<str:app_name>/<str:class_name>/', utils.autocomplete_view),
    path('json/<str:app_name>/<str:class_name>/', utils.json_view),
    path('chained_select/<str:app_name>/<str:class_name>/', utils.chained_select_view),
]

urlpatterns += [
    path('webservice/', webservice.rpc_handler),
    # path('api/docs/', include('rest_framework_swagger.urls')),  # docs dos services
    # path('api/', include(DefaultRouter().urls)),
]


# Include de cada app instalada
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.'):
        if settings.LPS:
            if os.path.exists(os.path.join(settings.BASE_DIR, '{}/lps/{}/urls.py'.format(app, settings.LPS))):
                urlpatterns += [path('%s/' % (app), include('{}.lps.{}.urls'.format(app, settings.LPS)))]
        if os.path.exists(os.path.join(settings.BASE_DIR, '%s/urls.py' % (app))):
            urlpatterns += [path('%s/' % (app), include('%s.urls' % (app)))]
        if os.path.exists(os.path.join(settings.BASE_DIR, '%s/urls_services.py' % app)):
            urlpatterns += [path('api/', include('%s.urls_services' % app))]

urlpatterns += [
    path('accounts/logout/', views.logout_then_login),
    path('accounts/login/', comum_views.login),
    path('admin/login/', comum_views.login),
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]

urlpatterns += [path('ckeditor/', include('ckeditor_uploader.urls'))]

# Login Gov.BR - If habilitar_login_govbr:
urlpatterns += [path('', include('social_django.urls', namespace='social'))]

if 'documento_eletronico' in settings.INSTALLED_APPS:
    from documento_eletronico.views import autenticar_documento as autenticar_documento_eletronico
    from documento_eletronico.views import verificar_documento_externo

    urlpatterns += [path('autenticar-documento/', autenticar_documento_eletronico), path('verificar-documento-externo/', verificar_documento_externo)]

# Isso só funciona em modo DEBUG. Em produção deve haver um mapeamento para STATIC_URL.
if running_tests() or settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT})]
    urlpatterns += [path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT})]

if settings.DEBUG:
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    if 'silk' in settings.INSTALLED_APPS:
        urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
