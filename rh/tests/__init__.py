# -*- coding: utf-8 -*-
# pylint: skip-file
# flake8: noqa
from .test_importador import ImportadorTest
from .test_mapa_tempo_servico import MapaTempoServicoTest
from .test_templates import IndexBoxTest


import doctest

doctest.testmod()
