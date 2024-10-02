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


    change_hidden_event('componente', function () {
        if ($('select[name=componente]').val() != '') {
            var descricao_componente = $('select[name=componente]').next().children().children().children().html();
            //atribui automaticamente a carga horária presente na descrição do componente ao campo de carga horária teórica'
            //jQuery('#id_ch_presencial').val(descricao_componente.split('[')[1].split('/')[0].split(' ')[0]);
        } else {
            //jQuery('#id_ch_presencial').val(0);
        }
    });
});