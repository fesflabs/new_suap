function mostrar_dados_aacc(tipo) {
    if (!tipo.val()) {
        jQuery('#id_dados_aacc').html('');
        return;
    }
    var url = '/edu/dados_atividade_complementar_ajax/' + jQuery('#id_aluno').val() + '/' + tipo.val() + '/';
    jQuery.ajax({
        type: 'GET',
        url: url,
        success: function (data) {
            jQuery('#id_dados_aacc').html(data);
        }
    });
};

function listar_tipos() {
    valor_anterior = jQuery('#id_tipo').val();
    jQuery('#id_dados_aacc').html('');
    var vinculacao = jQuery('[id^=id_vinculacao_0]:checked').val() || jQuery('[id^=id_vinculacao_1]:checked').val();
    var url = '/edu/listar_atividades_complementares_ajax/' + jQuery('#id_aluno').val() + '/' + vinculacao;
    jQuery.ajax({
        type: "GET",
        url: url,
        success: function (retorno) {
            var options = jQuery("#id_tipo");
            options.empty();
            options.append(jQuery("<option />").val('').text('--------'));
            jQuery.each(retorno, function () {
                options.append(jQuery("<option />").val(this[0]).text(this[1]));
            });

            jQuery('#id_tipo').val(valor_anterior);
        }
    });
};

jQuery(document).ready(function () {
    var tipo = jQuery('[id^=id_tipo]');
    tipo.on('change', function () {
        mostrar_dados_aacc(jQuery(this));
    });

    if (tipo.val() === '') {
        listar_tipos();
    }
    mostrar_dados_aacc(tipo);
    jQuery('.form-row.tipo').append('<div id="id_dados_aacc"></div>');

    listar_tipos();

    jQuery('.vinculacao').on('change', 'input[name=vinculacao]', function () {
        listar_tipos();
    });
});