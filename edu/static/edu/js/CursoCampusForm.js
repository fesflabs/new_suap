function checar_area_e_eixo() {
    if ($('#id_modalidade').val()) {
        if ($('#id_modalidade').val() > 4 && $('#id_modalidade').val() < 9) {
            //Curso tecnológicos ou FIC
            $('#id_eixo').parent().parent().parent().show();
            $('#id_area_capes').parent().parent().parent().hide();
            $('#id_area_capes').val('');
            $('#id_area').parent().parent().parent().hide();
            $('#id_area').val('');
        } else if ($('#id_modalidade').val() == 9 || $('#id_modalidade').val() == 10 || $('#id_modalidade').val() == 16) {
            $('#id_area_capes').parent().parent().parent().show();
            $('#id_area').parent().parent().parent().hide();
            $('#id_area').val('');
            $('#id_eixo').parent().parent().parent().hide();
            $('#id_eixo').val('');
        } else {
            $('#id_area').parent().parent().parent().show();
            $('#id_area_capes').parent().parent().parent().hide();
            $('#id_area_capes').val('');
            $('#id_eixo').parent().parent().parent().hide();
            $('#id_eixo').val('');
        }
    }
}

jQuery(function () {
    $('#id_modalidade').change(function () {
        checar_area_e_eixo();
    });

    $('#id_area_capes').parent().parent().parent().hide();
    $('#id_area').parent().parent().parent().hide();
    $('#id_eixo').parent().parent().parent().hide();
    checar_area_e_eixo();

    $('#id_descricao').keyup(function () {
        checar_descricao();
    });

});
