function change_hidden_event(selector, callback) {
    var select = $('select[name='+selector+']');
    var oldvalue = select.val();
    setInterval(function () {
        if (select.val() != oldvalue) {
            oldvalue = select.val();
            callback();
        }
    }, 500);
}

jQuery(function () {

    var obj = jQuery('#id_is_seminario_estagio_docente');
    obj.on('change', function () {
        var div = jQuery(this).closest('div.is_seminario_estagio_docente').next();
        if (obj.is(':checked')) {
            div.show();
        }else{
            div.find('select').val('');
            div.hide();
        }
    });
    if (!obj.is(':checked')) {
        var div = obj.closest('div.is_seminario_estagio_docente').next();
        div.find('select').val('');
        div.hide()
    }

    var modular = $('#id_tipo_modulo');
    if (modular.is(':hidden')) {
        modular.parent().hide();
    }
    
    change_hidden_event('componente', function () {
        if ($('select[name=componente]').val() != '') {
            var descricao_componente = $('select[name=componente]').next().children().children().children().html();
            //atribui automaticamente a carga horária presente na descrição do componente ao campo de carga horária teórica'
            jQuery('#id_ch_presencial').val(descricao_componente.split('[')[1].split('/')[0].split(' ')[0]);
        } else {
            jQuery('#id_ch_presencial').val(0);
        }
    });
});