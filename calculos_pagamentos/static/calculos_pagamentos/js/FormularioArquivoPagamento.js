
jQuery(document).ready(function(){

    function redirecionamento(){
        setTimeout(function () {
            document.location.href = jQuery('#id_pos_url').prop('value');
        }, 2000);
    }

    var observer = new MutationObserver(function (mutations) {
        redirecionamento();
    });

    var botao_enviar = $('input[name*="arquivopagamento_form"]')[0];

    // IFMA/Tássio: Ligando o observador ao elemento e o configurando
    observer.observe(botao_enviar, {
        attributes: true,
        attributeFilter: ['value']
    });

});