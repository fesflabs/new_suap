/*
    saldo
        data (aaaammdd)
        valor-em-segundos
        valor-distribuido-em-segundos
        valor-a-distribuir-em-segundos
        valor-view
        valor-distribuido-view
        valor-a-distribuir-view

    debito
        data (aaaammdd)
        valor-em-segundos
        valor-view
        valor-compensado-em-segundos
        valor-compensado-view
        valor-restante-view

    saldo-utilizado
        valor-em-segundos
        valor-view
        input hidden name="debito-data_saldo-data" value="valor-em-hora:min"

    saldo-totais
        saldo-total-view
        saldo-total-distribuido-view
        saldo-total-a-distribuir-view
 */

$(document).ready(function(){
    $("li.info").each(function () {
        if ($(this).html().length === 0)
            $(this).remove();
    });
    $("li.error").each(function () {
        if ($(this).html().length === 0)
            $(this).remove();
    });

    $("a.visualizar-situacao-inicial").click(function(){
        visualizar_situacao_inicial();
    });
    $("a.redistribuir-saldo.sem-aproveitar-distribuicao").click(function(){
        redistribuir_saldos();
    });
    $("a.redistribuir-saldo.aproveitar-distribuicao").click(function(){
        redistribuir_saldos(true);
    });
});

function visualizar_situacao_inicial(){
    remover_saldos_utilizados();
    update_totais_saldos_debitos();

    $(".saldo").removeClass("saldo-arrastavel");
    $(".saldo").draggable('destroy');

    $(".debito").removeClass("debito-colavel");
    $(".debito").draggable('destroy');

    $(".help-auto-distribuicao").fadeOut("slow");
    $(".help-situacao-inicial").fadeIn("slow");
    $(".help-redistribuicao-saldos").fadeOut("slow");
}

function redistribuir_saldos(continuar_redistribuicao){
    if (continuar_redistribuicao === true)
        ativar_remocao_saldos_utilizados();
    else
        remover_saldos_utilizados();

    update_totais_saldos_debitos();
    $(".saldo").addClass("saldo-arrastavel");
    $(".debito").addClass("debito-colavel");

    set_eventos_arrastar_e_soltar_saldos();

    $(".help-auto-distribuicao").fadeOut("slow");
    $(".help-situacao-inicial").fadeOut("slow");
    $(".help-redistribuicao-saldos").fadeIn("slow");
}

function remover_saldo_utilizado(el_saldo_utilizado) {
    var valor_saldo_removido_em_segundos = parseInt($(el_saldo_utilizado).find(".valor-em-segundos").html());
    var data_saldo_correspondente = $(el_saldo_utilizado).find("input").attr('name').split('_')[1];  // aaaammdd

    // atualiza total distribuído e total restante do saldo correspondente
    var el_saldo_correspondente = null;
    $(".saldo").each(function(){
        var seletor_saldo = this;
        var data_saldo = $(seletor_saldo).find(".data").html(); // aaaammdd
        if (data_saldo === data_saldo_correspondente){
            var valor_distribuido_em_segundos = parseInt($(seletor_saldo).find(".valor-distribuido-em-segundos").html());
            var novo_valor_distribuido = valor_distribuido_em_segundos - valor_saldo_removido_em_segundos;

            var valor_em_segundos = parseInt($(seletor_saldo).find(".valor-em-segundos").html());
            var novo_valor_a_distribuir = valor_em_segundos - novo_valor_distribuido;

            $(seletor_saldo).find(".valor-distribuido-em-segundos").html(novo_valor_distribuido);
            $(seletor_saldo).find(".valor-a-distribuir-em-segundos").html(novo_valor_a_distribuir);
            $(seletor_saldo).find(".valor-distribuido-view").html(formata_segundos(novo_valor_distribuido));
            if (novo_valor_distribuido != 0) {
                $(seletor_saldo).find(".valor-distribuido-view").parent("dd").parent("dl").removeClass("d-none");
            } else {
                $(seletor_saldo).find(".valor-distribuido-view").parent("dd").parent("dl").addClass("d-none");
            }
            $(seletor_saldo).find(".valor-a-distribuir-view").html(formata_segundos(novo_valor_a_distribuir));

            el_saldo_correspondente = seletor_saldo;

            return false;
        }
    });

    $(el_saldo_utilizado).addClass("saldo-utilizado-remover");
    $(".saldo-utilizado-remover").removeClass("saldo-utilizado");
    $(".saldo-utilizado-remover").each(function(){
        $(this).slideUp("slow", function(){
            $(this).remove();
        });
    });

    update_totais_saldos_debitos();

    if (el_saldo_correspondente !== null){
        $(el_saldo_correspondente).fadeOut("slow", function () {
            $(this).show();
        })
    }
}

function remover_saldos_utilizados(){
    $(".saldo-utilizado").addClass("saldo-utilizado-remover");
    $(".saldo-utilizado-remover").removeClass("saldo-utilizado");
    $(".saldo-utilizado-remover").each(function(){
        $(this).slideUp("slow", function(){
            $(this).remove();
        });
    });
    $(".saldo").each(function(){
        var valor_em_segundos = parseInt($(this).find(".valor-em-segundos").html());
        //
        $(this).find(".valor-distribuido-em-segundos").html(0);
        $(this).find(".valor-a-distribuir-em-segundos").html(valor_em_segundos);
        //
        $(this).find(".valor-distribuido-view").html(formata_segundos(0));
        $(this).find(".valor-distribuido-view").parent("dd").parent("dl").addClass("d-none");
        $(this).find(".valor-a-distribuir-view").fadeOut(function(){
            $(this).html(formata_segundos(valor_em_segundos));
            $(this).show();
        });
    });
    $(".saldo").parent().find(".saldo-totalmente-utilizado").hide();
}

function ativar_remocao_saldos_utilizados() {
    $(".saldo-utilizado").find("img.remover-saldo-utilizado").remove();
    $(".saldo-utilizado").find("p").prepend(
        "<img class='remover-saldo-utilizado' src='/static/admin/img/icon-deletelink.svg' title='Remover' style='float: right;'>"
    );
    set_eventos_remover_saldo_utilizado();
}

function update_totais_saldos_debitos() {
    /////////////////////////////
    // SALDOS
    var saldo_total = 0;
    var saldo_total_distribuido = 0;
    var saldo_total_a_distribuir = 0;
    //
    $(".saldo").each(function(){
        saldo_total += parseInt($(this).find(".valor-em-segundos").html());
        saldo_total_distribuido += parseInt($(this).find(".valor-distribuido-em-segundos").html());
        var total_a_distribuir = parseInt($(this).find(".valor-a-distribuir-em-segundos").html());
        saldo_total_a_distribuir += total_a_distribuir;
        //
        // infos ref ao saldo (no final)
        $(this).parent().find(".info").each(function () {
            $(this).parent().append(this); // apenas "empurra" para o final
        });
        var el_msg_saldo_totalmente_utilizado = $(this).parent().find(".info.saldo-totalmente-utilizado");
        if (total_a_distribuir <= 0){
            $(this).parent().append(el_msg_saldo_totalmente_utilizado);  // será a última "na marra"
            $(el_msg_saldo_totalmente_utilizado).show();
            $(this).addClass("success").removeClass("alert");
        } else {
            $(el_msg_saldo_totalmente_utilizado).hide();
            $(this).removeClass("success").addClass("alert");
        }
    });
    //
    $(".saldo-totais .saldo-total-view").fadeOut("slow", function(){
        $(this).html(formata_segundos(saldo_total));
        $(this).show();
    });
    $(".saldo-totais .saldo-total-distribuido-view").fadeOut("slow", function(){
        if (saldo_total_distribuido != 0) {
            $(this).addClass("true");
        } else {
            $(this).removeClass("true");
        }
        $(this).html(formata_segundos(saldo_total_distribuido));
        $(this).show();
    });
    $(".saldo-totais .saldo-total-a-distribuir-view").fadeOut("slow", function(){
        if (saldo_total_a_distribuir != 0) {
            $(this).addClass("false");
        } else {
            $(this).removeClass("false");
        }
        $(this).html(formata_segundos(saldo_total_a_distribuir));
        $(this).show();
    });

    /////////////////////////////
    // DÉBITOS
    var debito_total = 0;
    var debito_total_compensado = 0;
    //
    $(".debito").each(function(){
        var valor_debito = parseInt($(this).find(".valor-em-segundos").html());
        var compensado = 0;
        $(this).parent().find(".saldo-utilizado").each(function(){
            compensado += parseInt($(this).find(".valor-em-segundos").html());
        });
        var valor_restante = valor_debito - compensado;
        if (valor_restante < 0)
            valor_restante = 0;
        $(this).find(".valor-compensado-em-segundos").html(compensado);
        if (compensado != 0) {
            $(this).find(".valor-compensado-view").parent("dd").parent("dl").removeClass("d-none")
        } else {
            $(this).find(".valor-compensado-view").parent("dd").parent("dl").addClass("d-none");
        }
        $(this).find(".valor-compensado-view").html(formata_segundos(compensado));
        $(this).find(".valor-restante-view").html(formata_segundos(valor_restante));
        //
        // infos ref ao débito (no final)
        $(this).parent().find(".info").each(function () {
            $(this).parent().append(this); // apenas "empurra" para o final
        });
        var el_msg_debito_totalmente_compensado = $(this).parent().find(".info.debito-totalmente-compensado");
        if (valor_debito - compensado <= 0){
            $(this).parent().append(el_msg_debito_totalmente_compensado);  // será a última "na marra"
            $(el_msg_debito_totalmente_compensado).show();
            $(this).addClass("success").removeClass("error");
        } else {
            $(el_msg_debito_totalmente_compensado).hide();
            $(this).removeClass("success").addClass("error");
        }
        debito_total += valor_debito;
        debito_total_compensado += compensado;
    });
    var debito_total_restante = debito_total - debito_total_compensado;
    if (debito_total_restante < 0)
        debito_total_restante = 0;
    //
    $(".saldo-totais .debito-total-view").fadeOut("slow", function(){
        $(this).html(formata_segundos(debito_total));
        $(this).show();
    });
    $(".saldo-totais .debito-total-restante-view").fadeOut("slow", function(){
        if (debito_total_restante != 0) {
            $(this).addClass("false");
        } else {
            $(this).removeClass("false");
        }
        $(this).html(formata_segundos(debito_total_restante));
        $(this).show();
    });
}

function set_eventos_arrastar_e_soltar_saldos(){
    $(".saldo-arrastavel").draggable({
        cursor: "move",
        opacity: 0.9,
        revert: "invalid",
        helper: "clone",
        start: function(event, ui) {
            var data_saldo = $(ui.helper).find(".data").html(); // aaaammdd
            var data_saldo_em_d_m_a = get_dia_mes_ano(data_saldo);
            $(ui.helper).prepend(
                "<p class='datas_envolvidas'>" +
                "<strong>" +
                data_saldo_em_d_m_a[0] + "/" + data_saldo_em_d_m_a[1] + "/" + data_saldo_em_d_m_a[2] +
                "</strong>" +
                "</p>"
            );
        },
        drag: function(event, ui) {
            $(ui.helper).css("width", $(ui.helper.context).css("width"));
            $(ui.helper).css("border", "1px dashed #000");
        },
        stop: function(event, ui) {
        }
    });

    $(".debito-colavel").droppable({
        greedy: true,  // não propaga para os parents
        tolerance: "pointer", // a ponta do mouse
        over: function(event, ui) { // sobrevoando o débito ...
            var seletor_debito = this;
            var seletor_saldo = ui.draggable;

            if (is_pode_soltar_saldo(seletor_saldo, seletor_debito)){
                $(seletor_debito).addClass("debito-pode-utilizar-o-saldo");
            }
        },
        out: function(event, ui) { // saindo de cima do débito, sem soltar ...
            var seletor_debito = this;
            $(seletor_debito).removeClass("debito-pode-utilizar-o-saldo");
        },
        drop: function(event, ui) { // soltando em cima do débito ...
            var seletor_debito = this;
            var seletor_saldo = ui.draggable;
            $(ui.helper).remove();
            //
            $(seletor_debito).removeClass("debito-pode-utilizar-o-saldo");
            //
            if (is_pode_soltar_saldo(seletor_saldo, seletor_debito)){
                var data_debito = $(seletor_debito).find(".data").html(); // aaaammdd
                var data_saldo = $(seletor_saldo).find(".data").html(); // aaaammdd
                //
                var valor_debito = parseInt($(seletor_debito).find(".valor-em-segundos").html());
                var valor_debito_compensado = parseInt($(seletor_debito).find(".valor-compensado-em-segundos").html());
                var valor_debito_restante = valor_debito - valor_debito_compensado;
                var valor_saldo_restante = parseInt($(seletor_saldo).find(".valor-a-distribuir-em-segundos").html());
                //
                var valor_utilizado_pelo_debito = valor_debito_restante;
                if (valor_saldo_restante < valor_debito_restante)
                    valor_utilizado_pelo_debito = valor_saldo_restante;
                //
                var valor_utilizado_pelo_debito_em_h_m_s = get_hora_min_seg(valor_utilizado_pelo_debito);
                var data_saldo_em_d_m_a = get_dia_mes_ano(data_saldo);
                var input_name = data_debito + "_" + data_saldo; // aaaammdd_aaaammdd
                //
                // insere um elemento "saldo-utilizado", incluindo o field input ref. ao informe de compensação
                $(seletor_debito).parent().append("" +
                    "<li class='extra saldo-utilizado'>" +
                    "<span class='valor-em-segundos' hidden='hidden'>" + valor_utilizado_pelo_debito + "</span>" +
                    "<p>" +
                    "<img class='remover-saldo-utilizado' src='/static/admin/img/icon-deletelink.svg' title='Remover' style='float: right;'>" +
                    "Saldo utilizado: <strong>" +
                    "<span class='valor-view'>" + formata_segundos(valor_utilizado_pelo_debito) + "</span>" +
                    "</strong> " +
                    "em " + data_saldo_em_d_m_a[0] + "/" + data_saldo_em_d_m_a[1] + "/" + data_saldo_em_d_m_a[2] +
                    "</p>" +
                    "<input type='hidden' " +
                    "       name='" + input_name + "' " +
                    "       value='" + valor_utilizado_pelo_debito_em_h_m_s[0] + ":" + valor_utilizado_pelo_debito_em_h_m_s[1] + ":" + valor_utilizado_pelo_debito_em_h_m_s[2] +"'/>" +
                    "</li>");
                //
                var saldo_valor_total = parseInt($(seletor_saldo).find(".valor-em-segundos").html());
                var saldo_valor_distribuido =
                    parseInt($(seletor_saldo).find(".valor-distribuido-em-segundos").html()) + valor_utilizado_pelo_debito;
                var saldo_valor_a_distribuir = saldo_valor_total - saldo_valor_distribuido;
                $(seletor_saldo).find(".valor-distribuido-em-segundos").html(saldo_valor_distribuido);
                $(seletor_saldo).find(".valor-a-distribuir-em-segundos").html(saldo_valor_a_distribuir);
                $(seletor_saldo).find(".valor-distribuido-view").html(formata_segundos(saldo_valor_distribuido));
                if (saldo_valor_distribuido != 0) {
                    $(seletor_saldo).find(".valor-distribuido-view").parent("dd").parent("dl").removeClass("d-none");
                } else {
                    $(seletor_saldo).find(".valor-distribuido-view").parent("dd").parent("dl").addClass("d-none");
                }
                $(seletor_saldo).find(".valor-a-distribuir-view").html(formata_segundos(saldo_valor_a_distribuir));
                //
                set_eventos_remover_saldo_utilizado();
                //
                update_totais_saldos_debitos();
            }
        }
    });
}

function set_eventos_remover_saldo_utilizado() {
    $(".remover-saldo-utilizado").off('click');
    $(".remover-saldo-utilizado").on('click', function(){
        remover_saldo_utilizado($(this).parent().parent());
    });
}

function is_pode_soltar_saldo(seletor_saldo, seletor_debito){
    var valor_debito = parseInt($(seletor_debito).find(".valor-em-segundos").html());
    var valor_debito_compensado = parseInt($(seletor_debito).find(".valor-compensado-em-segundos").html());
    var valor_debito_restante = valor_debito - valor_debito_compensado;
    //
    var valor_saldo_restante = parseInt($(seletor_saldo).find(".valor-a-distribuir-em-segundos").html());
    //
    // deve haver saldo disponível e débito a compensar
    return valor_saldo_restante > 0 && valor_debito_restante > 0;
}
