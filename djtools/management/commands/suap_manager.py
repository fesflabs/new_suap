# -*- coding: utf-8 -*-
from pprint import pprint

from django.apps import apps
from django.conf import settings
from django.db.models import ForeignKey

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        parser.add_argument('--app_list', help='App label for processing.')
        parser.add_argument('--with_references', help='Show models referêncies for dependencies.')

    def handle(self, *args, **options):
        dependencias = dict()

        app_list = settings.INSTALLED_APPS_SUAP
        with_references = False

        if options['app_list']:
            app_list = options['app_list'].split(',')

        if options['with_references']:
            with_references = True

        for installed_app in app_list:
            app_set = set()
            if with_references:
                print(('-' * 60))
                print(('App:', installed_app))
                print(('-' * 60))
            for nome, Klass in list(apps.all_models[installed_app].items()):
                title = False
                # Processa os local_fields
                for field in Klass._meta.local_fields:
                    if issubclass(field.__class__, ForeignKey):
                        related_app = field.related_model._meta.app_label
                        if installed_app != related_app:
                            if with_references:
                                if not title:
                                    if with_references:
                                        print(('\nModel:', nome))
                                        print(('=' * 40))
                                        title = True
                                print(('  > field: %s (%s)' % (field.name, related_app)))
                            app_set.add(related_app)
                # Processa os local_many_to_many
                for field in Klass._meta.local_many_to_many:
                    related_app = field.related_model._meta.app_label
                    if installed_app != related_app:
                        if with_references:
                            print(('  > field: %s (%s)' % (field.name, related_app)))
                        app_set.add(related_app)
            dependencias[installed_app] = app_set

        if not with_references:
            pprint(dependencias)
