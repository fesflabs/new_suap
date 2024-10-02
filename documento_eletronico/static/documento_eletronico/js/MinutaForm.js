

$(document).ready(function() {
    if ($("#id_modelo").val()) {
        $("#id_modelo option:not(:selected)").remove();
    } else {
        $("#id_modelo").html('');
    }

    var tipo_documento_id_selected;
    var modelo_documento_id_selected;
    var setor_dono_id_selected;

    // Filtro por tipo de documento.
    $("#id_tipo").on('change', function() {
        tipo_documento_id_selected = $(this).val();
        if (tipo_documento_id_selected) {
            $.get("/documento_eletronico/modelos_tipo_documento/" + tipo_documento_id_selected + "/", function (data) {
                $("#id_modelo").html('');
                $.each(data.modelos, function(i, value) {
                    $("#id_modelo").append($("<option>").text(value.nome).attr("value", value.id));
                });
            });
        }
        $("#id_modelo").trigger('change');
        $("#id_setor_dono").trigger('change');
    });

    // Filtro por modelo do documento.
    $("#id_modelo").on('change', function() {
        modelo_documento_id_selected = $(this).val();
        if (tipo_documento_id_selected && modelo_documento_id_selected) {
            $.get("/documento_eletronico/nivel_acesso_padrao_classificacoes_modelo_documento/" + modelo_documento_id_selected + "/", function (data) {
                var add_input = $("#li_classificacao_add");
                $("#id_classificacao").html('');
                $("#id_nivel_acesso").val(data.nivel_acesso_padrao);
                $.each(data.classificacoes, function(i, value) {
                    html = '<li id="li_classificacao_'+i+'">' +
                    '   <img class="ajaxmultiselect_remove" style="margin-right: 4px;" title="Remover item" onclick="remove_value(this)" src="/static/admin/img/icon-deletelink.svg">' +
                    '       '+value.descricao+'' +
                    '   <input type="hidden" value="'+value.id+'" name="classificacao">' +
                    '</li>';
                    $("#id_classificacao").append(html);
                });
                $("#id_classificacao").append(add_input);
            });
        }
    });

    // Filtro por setor dono do documento.
    $("#id_setor_dono").on('change', function() {
        tipo_documento_id_selected = $("#id_tipo").val();
        setor_dono_id_selected = $(this).val();

        // Caso o tipo de documento e setor dono tenham sido definidos, daí será chamada a rotina que segure o identificador
        // do documento de texto.
        if (tipo_documento_id_selected && setor_dono_id_selected) {
            $.get("/documento_eletronico/gerar_sugestao_identificador_minuta/", function (data) {
                $("#id_identificador_numero").val(data.identificador_numero);
                $("#id_identificador_ano").val(data.identificador_ano);
            });
        } else {
            $("#id_identificador_numero").val('');
            $("#id_identificador_ano").val('');
        }
    });
});

