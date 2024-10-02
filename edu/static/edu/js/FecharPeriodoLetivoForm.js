function checar_tipo_fechamento() {
    $('select[name="aluno"]').parent().parent().hide();
    $('select[name="curso"]').parent().parent().hide();
    $('select[name="turma"]').parent().parent().hide();
    $('select[name="diario"]').parent().parent().hide();

    if ($('#id_tipo_0')[0].checked) {
        $('select[name="aluno"]').parent().parent().show();
    }

    if ($('#id_tipo_1')[0].checked) {
        $('select[name="turma"]').parent().parent().show();
    }

    if ($('#id_tipo_2')[0].checked) {
        $('select[name="curso"]').parent().parent().show();
    }

    if ($('#id_tipo_3')[0].checked) {
        $('select[name="diario"]').parent().parent().show();
    }
}


jQuery(function () {

    $('#id_tipo_0').click(function () {
        checar_tipo_fechamento();
    });
    $('#id_tipo_1').click(function () {
        checar_tipo_fechamento();
    });
    $('#id_tipo_2').click(function () {
        checar_tipo_fechamento();
    });
    $('#id_tipo_3').click(function () {
        checar_tipo_fechamento();
    });

    checar_tipo_fechamento();
});
