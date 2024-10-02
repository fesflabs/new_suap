$(document).ready(function(){

	if ($('#id_vinculado_nepp').is(':checked')) {
            $('#id_nucleo_extensao').parent().parent().show();
    } else {
        $('#id_nucleo_extensao').parent().parent().hide();
	}

	exibir_esconder_campo();
    $("#id_vinculado_nepp").on('change', function () {
        exibir_esconder_campo();
    });

    function exibir_esconder_campo() {

       if ($('#id_vinculado_nepp').is(':checked')) {
            $('#id_nucleo_extensao').parent().parent().show();
       } else {
            $('#id_nucleo_extensao').val("");
            $('#id_nucleo_extensao').parent().parent().hide();
       }

    }
});



