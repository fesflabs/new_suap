$(document).ready(function(){
	$("#id_dia_solicitacao").parent().parent().hide();
	tipo_refeicao_escolhido = $('#id_tipo_refeicao_escolhido').val();
	if (tipo_refeicao_escolhido){
		recarrega();
	}

});


function recarrega(){

	tipo_refeicao_escolhido = $('#id_tipo_refeicao_escolhido').val();


	$.ajax({
		method: "GET",
		url: "/ae/busca_tipo_refeicao/",
		data: { "tipo_refeicao_escolhido": tipo_refeicao_escolhido },
		success: function(result, textStatus, jqXHR) {

			$("#id_dia_solicitacao").parent().parent().show();

		},
		error: function() {

			$("#id_dia_solicitacao").parent().parent().hide();


		}
	});

	event.preventDefault();
	}
