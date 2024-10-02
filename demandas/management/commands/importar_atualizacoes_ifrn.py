# -*- coding: utf-8 -*-
from demandas.models import Atualizacao, Tag
from djtools.management.commands import BaseCommandPlus
from django.contrib.auth.models import Group
import requests
import json
from datetime import datetime


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        count = Atualizacao.objects.count()
        url = 'https://suap.ifrn.edu.br/api/v2/ti/novidades-suap/?limit=&offset={}'.format(count)
        response = requests.get(url)
        data = json.loads(response.content)
        for atualizacao in data['results']:
            print(atualizacao)
            tipo = atualizacao['tipo']
            tags = atualizacao['tags']
            grupos = atualizacao['grupos']
            data = atualizacao['data']
            descricao = atualizacao['descricao']
            pk = atualizacao['id']
            if not Atualizacao.objects.filter(pk=pk).exists():
                obj = Atualizacao()
                obj.pk = pk
                obj.tipo = tipo
                obj.descricao = descricao
                obj.data = datetime.strptime(data, '%Y-%m-%d')
                obj.save()
                for nome in grupos:
                    grupo = Group.objects.get_or_create(nome=nome)[0]
                    obj.grupos.add(grupo)
                for nome in tags:
                    tag = Tag.objects.filter(nome=nome).first()
                    if not tag:
                        tag = Tag.objects.create(nome=nome)
                        obj.tags.add(tag)
