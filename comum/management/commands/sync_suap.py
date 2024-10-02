from django.conf import settings
from django.core.management import call_command

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        commands = list()

        # Adiciona os comandas básicos ------------------------------
        # ** CORE **

        # === RH ===
        commands.append('importar_siape')

        ############################################################################################################
        # Se for o primeiro dia do mês roda uma importação completa do historico de afastamentos e ferias do servidor
        ############################################################################################################

        commands.append('atualizar_prazos_exercicio_externo')
        commands.append('organizar_historico_setor_siape')
        commands.append('organizar_data_fim_historico_setor')
        commands.append('importar_contracheques')
        commands.append('importar_arquivos_scdp')
        commands.append('importar_funcao_servidor')
        commands.append('atualizar_pessoa_fisica_sub_instances')

        # === Comum ===
        commands.append('sync_emails')
        commands.append('limpar_index_layout')
        commands.append('clearsessions_suap')
        commands.append('clean_tasks')
        commands.append('remover_permissao_usuarios')
        commands.append('indeferir_solicitacoes_reserva_sala')
        commands.append('zip_fotos_funcionarios')

        # === Demais aplicações ===
        if 'ae' in settings.INSTALLED_APPS:
            commands.append('gerar_bolsas_ae')
            commands.append('gerar_bolsas_ae_pesquisa')
            commands.append('gera_faltas_alimentacao')
            commands.append('ofertabolsa_ae_verificar_disponibilidade')

            if 'edu' in settings.INSTALLED_APPS:
                commands.append('edu_inativar_participacao_ae')

        if 'plan_estrategico' in settings.INSTALLED_APPS:
            commands.append('plan_estrategico_coletar_variaveis_edu')
            commands.append('plan_estrategico_coletar_variaveis_gestao')
            commands.append('plan_estrategico_coletar_variaveis_extensao')
            commands.append('plan_estrategico_coletar_variaveis_gestao_pessoas')
            commands.append('plan_estrategico_coletar_variaveis_pesquisa')
            commands.append('plan_estrategico_coletar_variaveis_tesouro_gerencial')
            commands.append('plan_estrategico_coletar_variaveis_pos_periodo')
            commands.append('plan_estrategico_totalizar_indicadores')
            commands.append('notifica_preenchimento_variaveis')
            commands.append('plan_estrategico_atualizar_valores_indicadores')
            commands.append('plan_estrategico_atualizar_valores_trimestrais')

        if 'centralservicos' in settings.INSTALLED_APPS:
            commands.append('centralservicos_notificacoes_diarias')

        if 'clipping' in settings.INSTALLED_APPS:
            commands.append('clipping_importar')

        if 'edu' in settings.INSTALLED_APPS:
            commands.append('edu_importar_dados')
            commands.append('edu_importar_digitais')
            commands.append('edu_importar_fotos')
            commands.append('edu_importar_professores')
            commands.append('edu_fechar_periodo')
            commands.append('edu_notificar_pendencias_secretarios')
            commands.append('edu_processar_pedidos_matricula')
            commands.append('edu_zip_fotos_alunos')

        if 'estagios' in settings.INSTALLED_APPS:
            commands.append('estagios_atualizacoes_notificacoes')
            commands.append('estagios_notificar_paes_a_vencer')

        if 'gerenciador_projetos' in settings.INSTALLED_APPS:
            commands.append('gp_tarefas_recorrentes')

        if 'materiais' in settings.INSTALLED_APPS:
            commands.append('inativar_cotacao')

        if 'rsc' in settings.INSTALLED_APPS:
            commands.append('checa_datas_processos_rsc')

        if 'projetos' in settings.INSTALLED_APPS:
            commands.append('notifica_atrasos_projetos')

        if 'pesquisa' in settings.INSTALLED_APPS:
            commands.append('notifica_atrasos_projetos_pesquisa')
            commands.append('gerencia_prazos_indicacoes_avaliadores')

        if 'documento_eletronico' in settings.INSTALLED_APPS:
            commands.append('delete_revisions_documento_eletronico')

        if 'processo_eletronico' in settings.INSTALLED_APPS:
            commands.append('processo_eletronico_atualizar_status_geral_processo')
            commands.append('processo_eletronico_gerar_numeros')
            commands.append('processo_eletronico_atualizar_permissoes')

        if 'eleicao' in settings.INSTALLED_APPS:
            commands.append('atualizar_publico_eleicoes_em_andamento')

        if 'enquete' in settings.INSTALLED_APPS:
            commands.append('atualizar_publico_enquete_em_andamento')

        if 'eventos' in settings.INSTALLED_APPS:
            commands.append('finalizar_eventos')

        if 'dipositivos_iot' in settings.INSTALLED_APPS:
            commands.append('revogar_autorizacoes_dispositivos')

        if 'gestao' in settings.INSTALLED_APPS:
            commands.append('processar_variaveis')

        if 'tesouro_gerencial' in settings.INSTALLED_APPS:
            commands.append('importar_do_tesouro')

        if 'licenca_capacitacao' in settings.INSTALLED_APPS:
            commands.append('processar_quantitativo_lic_capacitacao')

        if 'catalogo_provedor_servico' in settings.INSTALLED_APPS:
            commands.append('expirar_solicitacoes_incompletas')
            commands.append('enviar_email_aguardando_correcao')

        if 'cnpq' in settings.INSTALLED_APPS:
            commands.append('atualizar_datas_do_servidor')

        if 'erros' in settings.INSTALLED_APPS:
            commands.append('popular_links_gitlab')

        if 'saude' in settings.INSTALLED_APPS:
            commands.append('notificar_passaportes_invalidos')

        if 'demandas' in settings.INSTALLED_APPS:
            commands.append('remover_ambientes_homolog_expirados')

        if 'contratos' in settings.INSTALLED_APPS:
            commands.append('notificar_contratos_sem_garantia_vinculada')

        if 'patrimonio' in settings.INSTALLED_APPS:
            commands.append('patrimonio_depreciar_inventarios')

        for command in commands:
            tipo = type(command)
            if tipo == str:
                call_command(command, interactive=False, raise_exception=False, verbosity=0)
            elif tipo == tuple:
                call_command(command[0], command[1], interactive=False, raise_exception=False, verbosity=0)
