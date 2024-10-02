
function configurar_form(){
    var modulo_1 = $('input[name="modulo_1"]');
    if (modulo_1[0].checked){
        mostrar_elementos_modulo_1();
    } else {
        esconder_elementos_modulo_1();
    }

    var modulo_2 = $('input[name="modulo_2"]');
    if (modulo_2[0].checked){
        mostrar_elementos_modulo_2();
    } else {
        esconder_elementos_modulo_2();
    }

    var modulo_3 = $('input[name="modulo_3"]');
    if (modulo_3[0].checked){
        mostrar_elementos_modulo_3();
    } else {
        esconder_elementos_modulo_3();
    }

    var modulo_4 = $('input[name="modulo_4"]');
    if (modulo_4[0].checked){
        mostrar_elementos_modulo_4();
    } else {
        esconder_elementos_modulo_4();
    }

}


function esconder_elementos_modulo_1(id){
    $( "div.form-row.field-descricao_atividades_1" ).hide()
    $( "div.form-row.field-data_inicio_1" ).hide()
    $( "div.form-row.field-data_fim_1" ).hide()
    $( "div.form-row.field-ch_teorica_semanal_1" ).hide()
    $( "div.form-row.field-ch_pratica_semanal_1" ).hide()

}

function mostrar_elementos_modulo_1(id){
    $( "div.form-row.field-descricao_atividades_1" ).show()
    $( "div.form-row.field-data_inicio_1" ).show()
    $( "div.form-row.field-data_fim_1" ).show()
    $( "div.form-row.field-ch_teorica_semanal_1" ).show()
    $( "div.form-row.field-ch_pratica_semanal_1" ).show()

}

function esconder_elementos_modulo_2(id){
    $( "div.form-row.field-descricao_atividades_2" ).hide()
    $( "div.form-row.field-data_inicio_2" ).hide()
    $( "div.form-row.field-data_fim_2" ).hide()
    $( "div.form-row.field-ch_teorica_semanal_2" ).hide()
    $( "div.form-row.field-ch_pratica_semanal_2" ).hide()

}

function mostrar_elementos_modulo_2(id){
    $( "div.form-row.field-descricao_atividades_2" ).show()
    $( "div.form-row.field-data_inicio_2" ).show()
    $( "div.form-row.field-data_fim_2" ).show()
    $( "div.form-row.field-ch_teorica_semanal_2" ).show()
    $( "div.form-row.field-ch_pratica_semanal_2" ).show()

}

function esconder_elementos_modulo_3(id){
    $( "div.form-row.field-descricao_atividades_3" ).hide()
    $( "div.form-row.field-data_inicio_3" ).hide()
    $( "div.form-row.field-data_fim_3" ).hide()
    $( "div.form-row.field-ch_teorica_semanal_3" ).hide()
    $( "div.form-row.field-ch_pratica_semanal_3" ).hide()

}

function mostrar_elementos_modulo_3(id){
    $( "div.form-row.field-descricao_atividades_3" ).show()
    $( "div.form-row.field-data_inicio_3" ).show()
    $( "div.form-row.field-data_fim_3" ).show()
    $( "div.form-row.field-ch_teorica_semanal_3" ).show()
    $( "div.form-row.field-ch_pratica_semanal_3" ).show()

}

function esconder_elementos_modulo_4(id){
    $( "div.form-row.field-descricao_atividades_4" ).hide()
    $( "div.form-row.field-data_inicio_4" ).hide()
    $( "div.form-row.field-data_fim_4" ).hide()
    $( "div.form-row.field-ch_teorica_semanal_4" ).hide()
    $( "div.form-row.field-ch_pratica_semanal_4" ).hide()

}

function mostrar_elementos_modulo_4(id){
    $( "div.form-row.field-descricao_atividades_4" ).show()
    $( "div.form-row.field-data_inicio_4" ).show()
    $( "div.form-row.field-data_fim_4" ).show()
    $( "div.form-row.field-ch_teorica_semanal_4" ).show()
    $( "div.form-row.field-ch_pratica_semanal_4" ).show()

}



jQuery(document).ready(function(){
    configurar_form();
    $( "input[id^='id_modulo_']" ).change(function(){configurar_form();});
});
