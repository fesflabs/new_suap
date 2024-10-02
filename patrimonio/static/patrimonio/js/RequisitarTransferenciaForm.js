$(document).ready(function(){

	if($("input[name=tipo_transferencia]:checked").val() == undefined){
		$("#id_tipo_transferencia_0").attr('checked', true);
	}

	if($("input[name=tipo_transferencia]:checked").val() == "inventarios"){
		$(".form-row.inventarios").show();
		$(".form-row.rotulo").hide();
		$(".form-row.sala").hide();
	}
	else if($("input[name=tipo_transferencia]:checked").val() == "carga"){
		$(".form-row.inventarios").hide();
		$(".form-row.rotulo").hide();
		$(".form-row.sala").hide();
	}
	else if($("input[name=tipo_transferencia]:checked").val() == "rotulo"){
		$(".form-row.inventarios").hide();
		$(".form-row.rotulo").show();
		$(".form-row.sala").hide();
	}
	else if($("input[name=tipo_transferencia]:checked").val() == "sala"){
		$(".form-row.inventarios").hide();
		$(".form-row.rotulo").hide();
		$(".form-row.sala").show();
	}

	// Inventários
	$("#id_tipo_transferencia_0").change(function(){
		$(".form-row.inventarios").show();
		$(".form-row.rotulo").hide();
		$(".form-row.sala").hide();
	});

	// Toda a carga do servidor de origem
	$("#id_tipo_transferencia_1").change(function(){
		$(".form-row.inventarios").hide();
		$(".form-row.rotulo").hide();
		$(".form-row.sala").hide();
	});

	// Rótulos
	$("#id_tipo_transferencia_2").change(function(){
		$(".form-row.inventarios").hide();
		$(".form-row.rotulo").show();
		$(".form-row.sala").hide();
	});

	// Salas
	$("#id_tipo_transferencia_3").change(function(){
		$(".form-row.inventarios").hide();
		$(".form-row.rotulo").hide();
		$(".form-row.sala").show();
	});
})

