# -*- coding: utf-8 -*-

from ponto.models import Maquina
from rh.models import Setor, UnidadeOrganizacional, PessoaJuridica, Servidor, GrupoCargoEmprego, CargoEmprego


def carga_comum():

    # Setor
    s1 = Setor.objects.create(sigla='RAIZ', nome='Instituição')
    s2 = Setor.objects.create(sigla='C1', nome='Campus 1', superior=s1)
    s3 = Setor.objects.create(sigla='C1RH', nome='C1RH', superior=s2)
    s4 = Setor.objects.create(sigla='C1TI', nome='C1TI', superior=s2)
    s5 = Setor.objects.create(sigla='C2', nome='Campus 2', superior=s1)
    s6 = Setor.objects.create(sigla='C2RH', nome='C2RH', superior=s5)
    s7 = Setor.objects.create(sigla='C2TI', nome='C2TI', superior=s5)
    s8 = Setor.objects.create(sigla='C3', nome='Campus 3', superior=s1)
    s9 = Setor.objects.create(sigla='C3RH', nome='C3RH', superior=s8)
    s10 = Setor.objects.create(sigla='C3TI', nome='C3TI', superior=s8)

    # UnidadeOrganizacional
    UnidadeOrganizacional.objects.suap().create(padrao=True, setor=s1)
    UnidadeOrganizacional.objects.suap().create(setor=s5)
    UnidadeOrganizacional.objects.suap().create(setor=s8)
    # Grupo Cargo-Emprego
    grupo_cargo_emprego = GrupoCargoEmprego.objects.get_or_create(codigo='01', nome='Grupo X', sigla='X', categoria='tecnico_administrativo', excluido=False)
    # Cargo
    CargoEmprego.objects.get_or_create(codigo='01', nome='Cargo A', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='01', excluido=False)
    cargo_b = CargoEmprego.objects.get_or_create(codigo='02', nome='Cargo B', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='01', excluido=False)
    # Servidor
    Servidor.objects.create(matricula=1, username=1, nome='Queijo do setor C1RH', setor_lotacao=s3, cpf='111.111.111-11', cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=2, username=2, nome='Paulo do setor C1RH', setor_lotacao=s3, cpf='222.222.222-22', cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=3, username=3, nome='Samanta do setor C1TI', setor_lotacao=s4, cpf='333.333.333-33', cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=4, username=4, nome='Ricardo do setor C1TI', setor_lotacao=s4, cpf='444.444.444-44', cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=5, username=5, nome='Dennel do setor C2RH', setor_lotacao=s6, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=6, username=6, nome='Jéssica do setor C2RH', setor_lotacao=s6, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=7, username=7, nome='Marcelo do setor C2TI', setor_lotacao=s7, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=8, username=8, nome='Felipe do setor C2TI', setor_lotacao=s7, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=9, username=9, nome='Fernanda do setor C3RH', setor_lotacao=s9, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=10, username=10, nome='Caroline do setor C3RH', setor_lotacao=s9, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=11, username=11, nome='José do setor C3TI', setor_lotacao=s10, cargo_emprego=cargo_b)
    Servidor.objects.create(matricula=12, username=12, nome='João do setor C3TI', setor_lotacao=s10, cargo_emprego=cargo_b)

    # Maquina
    Maquina.objects.create(ip='127.0.0.1', descricao='Localhost', cliente_ponto=True)

    # PessoaJuridica
    PessoaJuridica.objects.create(nome='Fornecedor 1', cnpj='11111111/1111-11')
    PessoaJuridica.objects.create(nome='Fornecedor 2', cnpj='22222222/2222-22')
