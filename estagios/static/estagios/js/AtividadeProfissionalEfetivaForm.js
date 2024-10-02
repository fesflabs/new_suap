function configurar_form(){
    var radios = $('input[name="situacao_atividade"]')

    if(radios.length && radios[1].checked){
        exibir();
    } else{
        esconder();
    }
}

function exibir(){
    $( "fieldset" ).last().show();
}
function esconder(){
    $( "fieldset" ).last().hide();
}
jQuery(document).ready(function(){
    configurar_form();
    $('input[name="situacao_atividade"]').change(function(){configurar_form();});
});
