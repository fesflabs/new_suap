$(document).ready(function(){
	if($('input:radio[name=tipo_assinatura]:checked').val()=="senha"){
		$("input[name=senha]").parent().parent().show();

	}
	else if($('input:radio[name=tipo_assinatura]:checked').val()=="token"){
		$("input[name=senha]").parent().parent().hide();
	}
	else{
	    $("input[name=senha]").parent().parent().hide();
		$("input[name=senha]").parent().parent().hide();
    }


	$("#id_tipo_assinatura_0").click(function(){
		$("input[name=senha]").parent().parent().show();
	});
	$("#id_tipo_assinatura_1").click(function(){
		$("input[name=senha]").parent().parent().hide();

	});
});