# -*- coding: utf-8 -*
from django.urls import path

from . import views

urlpatterns = [
    path('search/<int:pk>/', views.search),
    path('show_object/<str:username>/', views.show_object),
    path('sync_user/<str:username>/', views.sync_user),
    path('change_password/<str:username>/', views.change_password),
    path('escolher_email/<str:tipo>/', views.escolher_email),
    path('redirecionar_google_classroom/', views.redirecionar_google_classroom),
    path('logout_google_classroom/', views.logout_google_classroom),
    path('ldap_group/change/<str:group_name>/', views.ldap_group_change_view, name='ldap-group-change'),
    path('ldap_group/add_member/<str:gid>/<int:uid>', views.ldap_add_member_view, name='ldap-group-add-member'),
    path('ldap_group/remover_member/<str:gid>/<int:uid>', views.ldap_remove_member_view, name='ldap-group-remove-member')
]
