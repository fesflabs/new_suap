# -*- coding: utf-8 -*-
from django.apps import apps
from django.conf import settings
from django.db import transaction


def on_transaction_commit(func):
    def inner(*args, **kwargs):
        transaction.on_commit(lambda: func(*args, **kwargs))

    return inner


def procotolo_eletronico_post_save(sender, instance, created, **kwargs):
    # NUP 17
    if not created and 'protocolo' in settings.INSTALLED_APPS and not instance.numero_protocolo_fisico:
        with transaction.atomic():
            Processo = apps.get_model("processo_eletronico", "Processo")
            ProcessoNup17 = apps.get_model("protocolo", "Processo")
            assunto = instance.assunto
            if len(assunto) > 100:
                assunto = assunto[:95] + '... .'

            interessado = instance.interessados.first()
            interessado_nome = interessado.nome
            interessado_documento = interessado.get_cpf_ou_cnpj() or ""
            interessado_pf = hasattr(interessado, 'pessoafisica')
            interessado_email = interessado.email or interessado.email_secundario
            interessado_telefone = interessado.pessoatelefone_set.first() and interessado.pessoatelefone_set.first().numero or ''

            processo_nup_17 = ProcessoNup17.objects.filter(numero_processo_eletronico=instance.numero_protocolo).first()
            if processo_nup_17:
                # Atualizando o processo "irmão" no módulo antigo (Protocolo), caso exista alguma diferença.
                if (
                    processo_nup_17.uo != instance.setor_criacao.uo
                    or processo_nup_17.interessado_nome != interessado_nome
                    or processo_nup_17.interessado_documento != interessado_documento
                    or processo_nup_17.interessado_pf != interessado_pf
                    or processo_nup_17.interessado_email != interessado_email
                    or processo_nup_17.interessado_telefone != interessado_telefone
                    or processo_nup_17.assunto != assunto
                    or processo_nup_17.tipo != ProcessoNup17.TIPO_REQUERIMENTO
                    or processo_nup_17.setor_origem != instance.setor_criacao
                ):
                    processo_nup_17.uo = instance.setor_criacao.uo
                    processo_nup_17.interessado_nome = interessado_nome
                    processo_nup_17.interessado_documento = interessado_documento
                    processo_nup_17.interessado_pf = interessado_pf
                    processo_nup_17.interessado_email = interessado_email
                    processo_nup_17.interessado_telefone = interessado_telefone
                    processo_nup_17.assunto = assunto
                    processo_nup_17.tipo = ProcessoNup17.TIPO_REQUERIMENTO
                    processo_nup_17.setor_origem = instance.setor_criacao

                    # Ativando flag temporário que permite somente a edição de um processo do módulo de Protocolo
                    # caso seja uma comando disparado internamente pelo módulo de Processo Eletrônico.
                    processo_nup_17.operacao_via_modulo_processo_eletronico = True
                    processo_nup_17.save()
            else:
                # Criando o processo "irmão" do módulo antigo (Protocolo)
                processo_nup_17 = ProcessoNup17.objects.create(
                    uo=instance.setor_criacao.uo,
                    interessado_nome=interessado_nome,
                    interessado_documento=interessado_documento,
                    interessado_pf=interessado_pf,
                    interessado_email=interessado_email,
                    interessado_telefone=interessado_telefone,
                    assunto=assunto,
                    tipo=ProcessoNup17.TIPO_REQUERIMENTO,
                    setor_origem=instance.setor_criacao,
                    vinculo_cadastro=instance.usuario_gerador.get_vinculo(),
                    numero_processo_eletronico=instance.numero_protocolo,
                )

            # Atualizando o processo do módulo novo (Processo Eletrônico) para referenciar o processo do
            # módulo antigo (Protocolo).
            Processo.objects.filter(pk=instance.id).update(numero_protocolo_fisico=processo_nup_17.numero_processo)
            instance.numero_protocolo_fisico = processo_nup_17.numero_processo
            instance.save()


def verifica_status_solicitacao_juntada(sender, instance, **kwargs):
    if instance.pk is None and instance.solicitacao_juntada.expirou:
        raise Exception("A solicitacação de juntada expirou.")
