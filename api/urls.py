# coding: utf-8

from django.urls import path

from . import views

urlpatterns = [
    path('', views.index),
    path('docs/', views.index)
]
