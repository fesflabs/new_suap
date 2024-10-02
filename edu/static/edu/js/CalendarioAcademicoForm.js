function checar_etapas() {
    if (document.getElementById('id_qtd_etapas_1').checked || document.getElementById('id_qtd_etapas_2').checked) {
        $('#id_data_inicio_etapa_2').parent().parent().parent().show();
    } else {
        $('#id_data_inicio_etapa_2').parent().parent().parent().hide();

        $('#id_data_inicio_etapa_2').val('');
        $('#id_data_fim_etapa_2').val('');
    }

    if (document.getElementById('id_qtd_etapas_2').checked) {
        $('#id_data_inicio_etapa_3').parent().parent().parent().show();
        $('#id_data_inicio_etapa_4').parent().parent().parent().show();
    } else {
        $('#id_data_inicio_etapa_3').parent().parent().parent().hide();
        $('#id_data_inicio_etapa_4').parent().parent().parent().hide();

        $('#id_data_inicio_etapa_3').val('');
        $('#id_data_fim_etapa_3').val('');

        $('#id_data_inicio_etapa_4').val('');
        $('#id_data_fim_etapa_4').val('');
    }
}


jQuery(function () {

    $('#id_qtd_etapas_0').click(function () {
        checar_etapas();
    });
    $('#id_qtd_etapas_1').click(function () {
        checar_etapas();
    });
    $('#id_qtd_etapas_2').click(function () {
        checar_etapas();
    });
    checar_etapas();


});
