$(function() {
    $(".coluna").sortable({
        connectWith: ".coluna",
        handle: ".portlet-header",
        cancel: ".portlet-toggle",
        placeholder: "portlet-placeholder ui-corner-all",
        beforeStop: function( event, ui ) {
            item = ui.item[0];
            coluna = '3';
            cont_item = $(item).prevAll().length;

            if ($(item.parentElement).hasClass('coluna-esquerda')) {
                coluna = '1';
            } else {
                if ($(item.parentElement).hasClass('coluna-centro')) {
                    coluna = '2';
                }
            }

            $.ajax({
                type: "POST",
                url: "/comum/index/layout/",
                data: {titulo: $(item).find('.portlet-header').find('.titulo')[0].getAttribute("data-quadro"), coluna: coluna, ordem: cont_item}
            });
        }
    });
    $(".esconder-quadro").click(function(){
        $.ajax({
            type: "POST",
            url: "/comum/index/esconder_quadro/",
            data: {titulo: $(this).data('quadro')}
        });
        $(this).parent().parent().hide();
    });
});