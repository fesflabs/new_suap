$(document).ready(function () {
    exibir_esconder_campo();
    $("#id_perda_peso").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_ganho_peso").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_fez_cirurgia").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_hemorragia").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_alergia_alimentos").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_doencas_previas").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_alergia_medicamentos").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_usa_medicamentos").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_transtorno_psiquiatrico").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_psiquiatra").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_lesoes_ortopedicas").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_atividade_fisica").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_fuma").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_bebe").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_usa_drogas").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_problema_auditivo").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_problema_aprendizado").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_ectoscopia_alterada").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_acv_alterado").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_ar_alterado").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_abdome_alterado").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_mmi_alterados").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_mms_alterados").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_outras_alteracoes").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_vida_sexual_ativa").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_foi_dentista_anteriormente").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_dificuldades").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_uso_internet").on('change', function () {
        exibir_esconder_campo();
    });

    $("#id_motivo_chegada").on('change', function () {
        exibir_esconder_campo();
    });

    $("input[type='checkbox']").click(function () {
        exibir_esconder_campo();
    });

});


function exibir_esconder_campo() {
    // Antropometria
    if ($('#id_perda_peso').is(':checked')) {
        $('#id_quanto_perdeu').parent().parent().show();
    } else {
        $('#id_quanto_perdeu').parent().parent().hide();
    }
    if ($('#id_ganho_peso').is(':checked')) {
        $('#id_quanto_ganhou').parent().parent().show();
    } else {
        $('#id_quanto_ganhou').parent().parent().hide();
    }

    // ProcessoSaudeDoenca
    if ($('#id_fez_cirurgia').is(':checked')) {
        $('#id_que_cirurgia').parent().parent().show();
    } else {
        $('#id_que_cirurgia').parent().parent().hide();
    }
    if ($('#id_hemorragia').is(':checked')) {
        $('#id_tempo_hemorragia').parent().show();
    } else {
        $('#id_tempo_hemorragia').parent().hide();
    }
    if ($('#id_alergia_alimentos').is(':checked')) {
        $('#id_que_alimentos').parent().show();
    } else {
        $('#id_que_alimentos').parent().hide();
    }
    if ($('#id_alergia_alimentos').is(':checked')) {
        $('#id_que_alimentos').parent().show();
    } else {
        $('#id_que_alimentos').parent().hide();
    }
    if ($('#id_alergia_medicamentos').is(':checked')) {
        $('#id_que_medicamentos').parent().show();
    } else {
        $('#id_que_medicamentos').parent().hide();
    }
    if ($('#id_doencas_previas').is(':checked')) {
        $('#id_que_doencas_previas').parent().show();
    } else {
        $('#id_que_doencas_previas').parent().hide();
    }
    if ($('#id_usa_medicamentos').is(':checked')) {
        $('#id_usa_que_medicamentos').parent().show();
    } else {
        $('#id_usa_que_medicamentos').parent().hide();
    }
    if ($('#id_lesoes_ortopedicas').is(':checked')) {
        $('#id_quais_lesoes_ortopedicas').parent().show();
    } else {
        $('#id_quais_lesoes_ortopedicas').parent().hide();
    }
    if ($('#id_transtorno_psiquiatrico').is(':checked')) {
        $('#id_qual_transtorno_psiquiatrico').parent().show();
    } else {
        $('#id_qual_transtorno_psiquiatrico').parent().hide();
    }
    if ($('#id_psiquiatra').is(':checked')) {
        $('#id_duracao_psiquiatria').parent().parent().show();
    } else {
        $('#id_duracao_psiquiatria').parent().parent().hide();
    }

    // DesenvolvimentoPessoal
    if ($('#id_problema_auditivo').is(':checked')) {
        $('#id_qual_problema').parent().show();
    } else {
        $('#id_qual_problema').parent().hide();
    }
    if ($('#id_problema_aprendizado').is(':checked')) {
        $('#id_qual_problema_aprendizado').parent().show();
        $('#id_origem_problema').parent().show();
    } else {
        $('#id_qual_problema_aprendizado').parent().hide();
        $('#id_origem_problema').parent().hide();
    }

    // ExameFisico
    if ($('#id_ectoscopia_alterada').is(':checked')) {
        $('#id_alteracao_ectoscopia').parent().show();
    } else {
        $('#id_alteracao_ectoscopia').parent().hide();
    }
    if ($('#id_acv_alterado').is(':checked')) {
        $('#id_alteracao_acv').parent().show();
    } else {
        $('#id_alteracao_acv').parent().hide();
    }
    if ($('#id_ar_alterado').is(':checked')) {
        $('#id_alteracao_ar').parent().show();
    } else {
        $('#id_alteracao_ar').parent().hide();
    }
    if ($('#id_abdome_alterado').is(':checked')) {
        $('#id_alteracao_abdome').parent().show();
    } else {
        $('#id_alteracao_abdome').parent().hide();
    }
    if ($('#id_mmi_alterados').is(':checked')) {
        $('#id_alteracao_mmi').parent().show();
    } else {
        $('#id_alteracao_mmi').parent().hide();
    }
    if ($('#id_mms_alterados').is(':checked')) {
        $('#id_alteracao_mms').parent().show();
    } else {
        $('#id_alteracao_mms').parent().hide();
    }
    if ($('#id_outras_alteracoes').is(':checked')) {
        $('#id_outras_alteracoes_descricao').parent().show();
    } else {
        $('#id_outras_alteracoes_descricao').parent().hide();
    }

    // HabitosDeVida
    if ($('#id_atividade_fisica').is(':checked')) {
        $('#id_qual_atividade').parent().show();
        $('#id_frequencia_semanal').parent().parent().show();
    } else {
        $('#id_qual_atividade').parent().hide();
        $('#id_frequencia_semanal').parent().parent().hide();
    }
    if ($('#id_usa_drogas').is(':checked')) {
        $('#id_que_drogas').parent().parent().show();
    } else {
        $('#id_que_drogas').parent().parent().hide();
    }
    if ($('#id_bebe').is(':checked')) {
        $('#id_frequencia_bebida').parent().show();
    } else {
        $('#id_frequencia_bebida').parent().hide();
    }
    if ($('#id_fuma').is(':checked')) {
        $('#id_frequencia_fumo').parent().show();
    } else {
        $('#id_frequencia_fumo').parent().hide();
    }
    if ($('#id_vida_sexual_ativa').is(':checked')) {
        $('#id_metodo_contraceptivo').parent().show();
        $('#id_qual_metodo_contraceptivo').parent().show();
    } else {
        $('#id_metodo_contraceptivo').parent().hide();
        $('#id_qual_metodo_contraceptivo').parent().hide();
    }
    if ($('#id_uso_internet').is(':checked')) {
        $('#id_tempo_uso_internet').parent().show();
        $('#id_objetivo_uso_internet').parent().show();
    } else {
        $('#id_tempo_uso_internet').parent().hide();
        $('#id_objetivo_uso_internet').parent().hide();
    }

    // PercepcaoSaudeBucal
    if ($('#id_foi_dentista_anteriormente').is(':checked')) {
        $('#id_tempo_ultima_vez_dentista').parent().show();
    } else {
        $('#id_tempo_ultima_vez_dentista').parent().hide();
    }
    if ($('#id_dificuldades').is(':checked')) {
        $('#id_grau_dificuldade_sorrir').parent().parent().show();
        $('#id_grau_dificuldade_falar').parent().parent().show();
        $('#id_grau_dificuldade_comer').parent().parent().show();
        $('#id_grau_dificuldade_relacionar').parent().parent().show();
        $('#id_grau_dificuldade_manter_humor').parent().parent().show();
        $('#id_grau_dificuldade_estudar').parent().parent().show();
        $('#id_grau_dificuldade_trabalhar').parent().parent().show();
        $('#id_grau_dificuldade_higienizar').parent().parent().show();
        $('#id_grau_dificuldade_dormir').parent().parent().show();
    } else {
        $('#id_grau_dificuldade_sorrir').parent().parent().hide();
        $('#id_grau_dificuldade_falar').parent().parent().hide();
        $('#id_grau_dificuldade_comer').parent().parent().hide();
        $('#id_grau_dificuldade_relacionar').parent().parent().hide();
        $('#id_grau_dificuldade_manter_humor').parent().parent().hide();
        $('#id_grau_dificuldade_estudar').parent().parent().hide();
        $('#id_grau_dificuldade_trabalhar').parent().parent().hide();
        $('#id_grau_dificuldade_higienizar').parent().parent().hide();
        $('#id_grau_dificuldade_dormir').parent().parent().hide();
    }

    if ($('#id_motivo_chegada').val() == 7) {
        $('#id_descricao_encaminhamento_externo').parent().parent().show();

    }
    else {
        $('#id_descricao_encaminhamento_externo').parent().parent().hide();
        $('#id_descricao_encaminhamento_externo').val('');

    }


    var valores_marcados = [];
    $('input:checkbox[name=queixa_principal]:checked').each(function () {
        valores_marcados.push($(this).val());
    });
    if (valores_marcados.includes('24')) {
        $('#id_descricao_queixa_outros').parent().parent().show();
    } else {
        $('#id_descricao_queixa_outros').parent().parent().hide();
    }


    var valores_marcados = [];
    $('input:checkbox[name=queixa_identificada]:checked').each(function () {
        valores_marcados.push($(this).val());
    });
    if (valores_marcados.includes('24')) {
        $('#id_descricao_queixa_identificada_outros').parent().parent().show();
    } else {
        $('#id_descricao_queixa_identificada_outros').parent().parent().hide();
    }




}

