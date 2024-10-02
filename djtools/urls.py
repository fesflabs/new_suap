# -*- coding: utf-8 -*-

from django.urls import path

from djtools import views

urlpatterns = [
    path('give_permission/', views.give_permission),
    path('delete_object/<str:app>/<str:model>/<int:pk>/', views.delete_object),
    path('breadcrumbs_reset/<str:menu_item_id>/<path:url>', views.breadcrumbs_reset),
    path('notificar_grupo/<int:pk_grupo>/', views.notificar_grupo),
    path('permissions/<str:app>/', views.permissions),
    path('help_view/<str:app>/<str:view>/', views.help_view),
    path('popup_choice_field/<str:name>/', views.popup_choice_field),
    path('popup_choice_field/<str:name>/<str:ids>/', views.popup_choice_field),
    path('popup_multiple_choice_field/<str:name>/', views.popup_multiple_choice_field),
    path('popup_multiple_choice_field/<str:name>/<str:ids>/', views.popup_multiple_choice_field),
    path('process/<uuid:pid>/', views.process),
    path('process/<uuid:pid>/<int:interval>/', views.process),
    path('process_progress/<str:pid>/', views.process_progress),
    path('process_download/<str:pid>/<int:file_type>/', views.process_download),
    path('user_info/<uuid:user_uuid>/', views.user_info),
    path('profile_info/<uuid:profile_uuid>/', views.profile_info),
    path('view_email/', views.view_email),
    path('process2/<uuid:uuid_task>/', views.process2),
    path('process_progress2/<int:download>/<uuid:uuid_task>/', views.process_progress2),
    path('view_task/<int:pk>/', views.view_task),
    path('consultar_cep/<str:cep>/', views.consultar_cep),
    path('consulta_cep_govbr/<str:cep>/', views.consulta_cep_govbr),
    path('two_factor_authentication/', views.two_factor_authentication),
    path('private_media/', views.private_media),
]
