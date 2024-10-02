function checar_criterio_avaliacao() {
    if (document.getElementById('id_criterio_avaliacao_0').checked) {
        $('#id_media_aprovacao_sem_prova_final').parent().parent().show();
        $('#id_media_evitar_reprovacao_direta').parent().parent().show();
        $('#id_media_aprovacao_avaliacao_final').parent().parent().show();
    } else {
        $('#id_media_aprovacao_sem_prova_final').parent().parent().hide();
        $('#id_media_evitar_reprovacao_direta').parent().parent().hide();
        $('#id_media_aprovacao_avaliacao_final').parent().parent().hide();

        $('#id_media_aprovacao_sem_prova_final').val('');
        $('#id_media_evitar_reprovacao_direta').val('');
        $('#id_media_aprovacao_avaliacao_final').val('');

    }
}

function checar_tipo_avaliacao() {
    if (document.getElementById('id_tipo_avaliacao_2').checked) {
        $('#id_proitec').parent().parent().show();
    } else {
        $('#id_proitec').parent().parent().hide();
        $('#id_proitec').prop('checked', false);
    }

    if (document.getElementById('id_tipo_avaliacao_1').checked || document.getElementById('id_tipo_avaliacao_3').checked) {
        $('#id_limite_reprovacao').parent().parent().show();
    } else {
        $('#id_limite_reprovacao').parent().parent().hide();
        $('#id_limite_reprovacao').val('');
    }

    if (document.getElementById('id_tipo_avaliacao_0').checked) {
        $('#id_qtd_minima_disciplinas').parent().parent().show();
        $('#id_numero_disciplinas_superior_periodo').parent().parent().show();
        $('#id_qtd_max_periodos_subsequentes').parent().parent().show();
        $('#id_numero_max_cancelamento_disciplina').parent().parent().show();
    } else {
        $('#id_qtd_minima_disciplinas').parent().parent().hide();
        $('#id_numero_disciplinas_superior_periodo').parent().parent().hide();
        $('#id_qtd_max_periodos_subsequentes').parent().parent().hide();
        $('#id_numero_max_cancelamento_disciplina').parent().parent().hide();

        $('#id_qtd_minima_disciplinas').val('');
        $('#id_numero_disciplinas_superior_periodo').val('');
        $('#id_qtd_max_periodos_subsequentes').val('');
        $('#id_numero_max_cancelamento_disciplina').val('');
    }
}

jQuery(function () {

    $('#id_tipo_avaliacao_0').click(function () {
        checar_tipo_avaliacao();
    });
    $('#id_tipo_avaliacao_1').click(function () {
        checar_tipo_avaliacao();
    });
    $('#id_tipo_avaliacao_2').click(function () {
        checar_tipo_avaliacao();
    });
    $('#id_tipo_avaliacao_3').click(function () {
        checar_tipo_avaliacao();
    });


    $('#id_criterio_avaliacao_0').click(function () {
        checar_criterio_avaliacao();
    });
    $('#id_criterio_avaliacao_1').click(function () {
        checar_criterio_avaliacao();
    });

    checar_tipo_avaliacao();
    checar_criterio_avaliacao();
});
