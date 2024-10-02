# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from rh.models import PessoaExterna
import tqdm


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for pessoa in tqdm.tqdm(PessoaExterna.objects.filter(vinculos__isnull=True)):
            pessoa.save()
