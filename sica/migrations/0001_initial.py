# Generated by Django 1.11.23 on 2019-08-14 15:13


from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('edu', '0003_aluno_candidato_vaga')]

    operations = [
        migrations.CreateModel(
            name='Componente',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Código')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Nome')),
                ('sigla', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Sigla')),
            ],
            options={'verbose_name': 'Componente', 'verbose_name_plural': 'Componentes'},
        ),
        migrations.CreateModel(
            name='ComponenteCurricular',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('periodo', models.IntegerField(choices=[[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7]], verbose_name='Período')),
                ('qtd_creditos', models.IntegerField(blank=True, null=True, verbose_name='Qtd. Aulas Semanais')),
                ('carga_horaria', models.IntegerField(blank=True, null=True, verbose_name='C.H.')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        choices=[('Formação Geral', 'Formação Geral'), ('Formação Específica', 'Formação Específica')],
                        default='Formação Geral',
                        max_length=255,
                        verbose_name='Tipo',
                    ),
                ),
                ('opcional', models.BooleanField(default=False, blank=True, verbose_name='Opcional')),
                ('desde', models.IntegerField(blank=True, null=True, verbose_name='A partir de')),
                ('ate', models.IntegerField(blank=True, null=True, verbose_name='Até')),
                ('componente', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='sica.Componente', verbose_name='Componente')),
                ('equivalencias', djtools.db.models.ManyToManyFieldPlus(blank=True, to='sica.ComponenteCurricular', verbose_name='Equivalências')),
            ],
            options={'verbose_name': 'Componente', 'verbose_name_plural': 'Componentes'},
        ),
        migrations.CreateModel(
            name='Historico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'comprovou_experiencia_proficional',
                    models.BooleanField(
                        default=False, help_text='Marque essa opção caso o aluno tenha recorrido à portal 426/94 - DG/ETFRN', verbose_name='Comprovou Experiência Profisional'
                    ),
                ),
                ('carga_horaria_estagio', models.IntegerField(blank=True, null=True, verbose_name='C.H. de Estágio')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
                ('componentes_curriculares', models.ManyToManyField(to='sica.ComponenteCurricular', verbose_name='Componentes Curriculares')),
            ],
            options={'verbose_name': 'Histórico', 'verbose_name_plural': 'Históricos'},
        ),
        migrations.CreateModel(
            name='Matriz',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Nome')),
                ('codigo', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Código')),
                ('carga_horaria', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Carga-Horária Obrigatória')),
                ('carga_horaria_estagio', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Carga-Horária de Estágio')),
                ('reconhecimento', models.TextField(blank=True, null=True, verbose_name='Reconhecimento')),
            ],
            options={'verbose_name': 'Matriz', 'verbose_name_plural': 'Matrizes'},
        ),
        migrations.CreateModel(
            name='RegistroHistorico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        choices=[('Formação Geral', 'Formação Geral'), ('Formação Específica', 'Formação Específica')],
                        default='Formação Geral',
                        max_length=255,
                        verbose_name='Tipo',
                    ),
                ),
                ('ano', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Ano')),
                ('periodo', djtools.db.models.CharFieldPlus(choices=[['1', '1'], ['2', '2']], max_length=255, null=True, verbose_name='Período')),
                ('turma', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Turma')),
                ('nota', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Nota')),
                ('qtd_faltas', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Faltas')),
                ('carga_horaria', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='C.H.')),
                (
                    'situacao',
                    djtools.db.models.CharFieldPlus(blank=True, choices=[['', ''], ['M', 'M'], ['A', 'A'], ['X', 'X']], max_length=255, null=True, verbose_name='Situação'),
                ),
                ('periodo_matriz', models.IntegerField(choices=[[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8], [9, 9]], null=True, verbose_name='Nível')),
                ('opcional', models.BooleanField(default=False, blank=True, verbose_name='Opcional')),
                ('componente', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='sica.Componente', verbose_name='Componente')),
                ('historico', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='sica.Historico', verbose_name='Histórico')),
            ],
            options={'verbose_name': 'Registro de Histórico', 'verbose_name_plural': 'Registros de Histórico'},
        ),
        migrations.AddField(
            model_name='historico', name='matriz', field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='sica.Matriz', verbose_name='Matriz')
        ),
        migrations.AddField(
            model_name='componentecurricular', name='matriz', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='sica.Matriz', verbose_name='Matriz')
        ),
    ]
