close_fancybox = function () {
    jQuery.fancybox.close();
    window.location.reload();
}

close_fancybox_noreload = function (message, tag) {
    jQuery.fancybox.close();
    showFeedbackMessage(message, tag);
}

replaceAddAnotherLinks = function () {
    let links = jQuery('body:not(.popup_) .popup');
    for (let i = 0; i < links.length; i++) {
        let link = links[i];
        link.onclick = function (e) {
            e.preventDefault();
            openLinkInPopup(link);
        };
    }
}

openLinkInPopup = function(link) {
    /*
        Atributos "data" específicos do link:
         - "data-reload-on-close": "true" ou "false"
         - "data-callback-after-close": "nome da função js"
    */
    if (link.host !== window.location.host) {
        // cross domain
        // redireciona para o outro domínio indicado no link
        window.location = link.href;
        return;
    }

    let first_char = '?';
    if (link.href.indexOf('?') > 0) {
        first_char = '&';
    }
    let url = link.href + first_char + '_popup=1';

    fancybox_events = {};
    // atributo "data-reload-on-close" do link
    var reloadOnClose = $(link).data('reload-on-close');

    if (reloadOnClose == "true" || reloadOnClose == true) {
        // frontend: seta o evento "beforeClose"
        fancybox_events.beforeClose = function() {
            document.location.reload();
            return false;
        }
    } else if (reloadOnClose == "false" || reloadOnClose == false) {
        // backend: instrui para fechamento via "close_fancybox_noreload"
        url += '&_popup_close_noreload=1'
    }

    // atributo "data-callback-after-close" do link
    var callBackAfterClose = $(link).data('callback-after-close');

    if (callBackAfterClose !== undefined) {
        // frontend: seta o evento "afterClose"
        fancybox_events.afterClose = function() {
            try {
                document[callBackAfterClose]();
            } catch (e) {
                try {
                    window[callBackAfterClose]();
                } catch (e) {
                }
            }
        }
    }
    $.fancybox.open({
        src  : url,
        type : 'iframe',
        beforeClose: fancybox_events.beforeClose,
        afterClose: fancybox_events.afterClose,
        afterShow : function( instance, current ) {
            let links = jQuery('a', jQuery(current.$iframe).contents());
            links.each(function(e){
                let href = $(this).attr('href');
                if(typeof href === 'string' || href instanceof String){
                    if(href.indexOf('?') === -1){
                        href = href + '?_popup=1';
                    } else {
                        href = href + '&_popup=1'
                    }
                    $(this).attr('href', href);
                }
            });
        },
    });
}

showFeedbackMessage = function(message, tag) {
    clearFeedbackMessage();
    if (message !== undefined && (message+"").trim().length > 0)
        $("body").prepend('<p class="msg '+tag+'" id="feedback_message">'+message+'</p>');
}

clearFeedbackMessage = function() {
    $("#feedback_message").remove();
}

jQuery(document).ready(function () {
    replaceAddAnotherLinks();
});
