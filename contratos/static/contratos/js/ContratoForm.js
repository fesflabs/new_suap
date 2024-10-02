$(document).ready(function(){
	if ($("#id_tempo_indeterminado").prop("checked"))
		$('label[for=id_data_fim], input#id_data_fim').hide();

	$("#id_tempo_indeterminado").click(function () {
		var is_checked = $(this).prop("checked");
		if (is_checked) {
			$('label[for=id_data_fim], input#id_data_fim').fadeOut();
        }
		else
			$('label[for=id_data_fim], input#id_data_fim').fadeIn();
            $("#id_data_fim").focus();
    })

})
