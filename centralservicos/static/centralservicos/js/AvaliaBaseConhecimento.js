$( document ).ready(function() {
    $('a[name=avaliar]').on('click', function(event) {
        event.preventDefault();
        var id = $(this).attr("data-id");
        $.ajax({
            url: $(this).attr('href'),
            type: "POST",
            success: function(data) {
                $('#media_avaliacao_' + id).html(data.media_avaliacoes);
                $('#qtd_avaliacoes_' + id).html(data.qtd_avaliacoes);
                if (data.avaliou_todas_perguntas) {
                    $('#general_box_' + id).removeClass("error");
                    $('#general_box_' + id + ' .primary-info').find("span.status.status-alert").hide();
                    $('#general_box_' + id).find(".custom-checkbox").removeClass("disabled");
                    $('#general_box_' + id).find(".custom-checkbox input").removeAttr("disabled");
                }
            }
        });
        $(this).parent().find("span").addClass("disabled");
        $(this).find("span").removeClass("disabled");
        $(this).prevAll().find("span").removeClass("disabled");
    });


    $('select#id_respostapadrao').on('change', function(){
        $('#id_observacao').val($(this).val());
    });

});
