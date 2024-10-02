
/* Syncronize Widgets */

function sync_widgets() {
    var telMaskBehavior = function (val) {
        return val.replace(/\D/g, '').length === 11 ? '(00) 00000-0000' : '(00) 0000-00009';
    };
    var telOptions = {
        onKeyPress: function(val, e, field, options) {
            field.mask(telMaskBehavior.apply({}, arguments), options);
        }
    };

    // BrDataWidget
    $("input.br-data-widget").unmask();
    $("input.br-data-widget").mask("99/99/9999", {placeholder:" "});
	
	// ShotTimeWidget
    $("input.short-time-widget").unmask();
    $("input.short-time-widget").mask("99:99", {placeholder:" "});
    
    // BrDateTimeWidget
    $("input.br-datahora-widget").unmask();
    $("input.br-datahora-widget").mask("99/99/9999 99:99:99", {placeholder:" "});
    
    // BrTelefoneWidget
    $("input.br-phone-number-widget").unmask();
    $("input.br-phone-number-widget").mask(telMaskBehavior, telOptions);
    
    // BrCepWidget
    $("input.br-cep-widget").unmask();
    $("input.br-cep-widget").mask("99999-999", {placeholder:" "});

    // BrCpfWidget
    $("input.br-cpf-widget").unmask();
    $("input.br-cpf-widget").mask("999.999.999-99", {placeholder:" "});
    
    // BrCnpjWidget
    $("input.br-cnpj-widget").unmask();
    $("input.br-cnpj-widget").mask("99.999.999/9999-99", {placeholder:" "});
    
	// BrPlacaVeicularWidget
    $("input.placa-widget").unmask();
    $("input.placa-widget").mask("SSS-9A99", {placeholder:" "});
	$("input.placa-widget").blur(function () {
		this.value = this.value.toUpperCase();
	});
	
	// EmpenhoWidget
    $("input.empenho-widget").unmask();
	//$.mask.definitions['~']='[Nn]';
	//$.mask.definitions['/']='[Ee]';  
    //$("#eyescript").mask("~9.99 ~9.99 999"); 
    $("input.empenho-widget").mask("9999NE999999", {placeholder:" "});
	$("input.empenho-widget").blur(function () {
		this.value = this.value.toUpperCase();
	});
	
	// IntegerWidget
	$("input.integer-widget").unmask('keypress');
	$("input.integer-widget").keypress(function () {
        mask(this, mask_only_numbers);
    });
	
	// AlphaNumericWidget
    $("input.alpha-widget").unmask('keypress');
    $("input.alpha-widget").keypress(function () {
        mask(this, mask_alpha);
    });
	
    // AlphaNumericUpperTextWidget
    $("input.upper-text-widget").unbind('keypress');
    $("input.upper-text-widget").keypress(function () {
        mask(this, mask_upper_text);
    });
	
	// CapitalizeTextWidget
    $("input.capitalize-text-widget").unbind('keypress');
    $("input.capitalize-text-widget").keypress(function () {
        mask(this, mask_camel_case);
    });    
	
    // BrDinheiroWidget
    // $("input.br-dinheiro-widget").mask("000.000.000.000.000,00", {reverse: true, placeholder: '0,00'});
    $("input.br-dinheiro-widget").unbind('keypress');
    $("input.br-dinheiro-widget").keypress(function () {
        mask(this, mask_money); //mask_decimal);
        // mask(this, mask_money);
    });

    // BrDinheiroWidget
    $("input.br-dinheiro-almox-widget").unbind('keypress');
    $("input.br-dinheiro-almox-widget").keypress(function () {
        mask(this, mask_money_almox);
    });

    substitui_prefixo();
}

var v_obj = null;
var v_fun = null;

function mask(o,f){
    v_obj=o;
    v_fun=f;

    if ($(o).attr('data-decimal-places')) {
        setTimeout("execmask()", 1);
        // setTimeout("execmask2($(o).attr('data-decimal-places'))", 1);
    } else {
        setTimeout("execmask()", 1);
    }
}

function execmask(){
    v_obj.value=v_fun(v_obj.value);
}

function execmask2(decimal){
    v_obj.value=v_fun(v_obj.value, decimal);
}

function mask_only_numbers(v){
    return v.replace(/\D/g,"");
}

function mask_upper_text(v){ // by andersonbraulio
    texto = v.replace(/[^a-zA-Z0-9]/g,"");
	textoFormatado = "";

    for (i = 0; i < texto.length; i++) {
        char = texto.charAt(i);
        if (i == 0)
            if (char == ' ')
               textoFormatado = texto.substr(1);
            else
                textoFormatado = char.toUpperCase();
        else
              textoFormatado += char.toUpperCase();
    }
    return textoFormatado;
}

function mask_alpha(v){ // by andersonbraulio
    return v.replace(/[^a-zA-Z0-9]/g,"");
}

function mask_camel_case(v){ // by andersonbraulio
    texto = v.replace(/[^a-zA-ZÁ-Ûá-û0-9.\'\s\-]/g,"");
	textoFormatado = "";

	for (i = 0; i < texto.length; i++) {
        char = texto.charAt(i);
		if (i == 0) {
	        if (char == ' ')
	           textoFormatado = texto.substr(1);
	        else
	            textoFormatado = char.toUpperCase();
		} else {
		  prevChar = textoFormatado.charAt(i-1);
		  if (prevChar == ' ')
		      textoFormatado = texto.substr(0,i).concat(char.toUpperCase());
		  else
		      textoFormatado += char.toLowerCase();
		}
	}
	return textoFormatado;
}

function mask_float(v){
	textoNumerico = v.replace(/\D/g,"");
    textoNumerico = textoNumerico.replace(/^0/,"");
   
	if (textoNumerico.length == 1) {
		return "0." + textoNumerico;
	} else
	if (textoNumerico.length == 2) {
		return textoNumerico[0] + "." + textoNumerico[1];
	} else 
	if (textoNumerico.length == 3){
		return textoNumerico.slice(0,2) + "." + textoNumerico.slice(2);
	} else {
		return textoNumerico.slice(0,3) + "." + textoNumerico.slice(3);
	}
}

function mask_money(v){ // by paivatulio
    negativo = ''
    if (v[0] == '-') {
        negativo = '-'
    }
    textoNumerico = v.replace(/\D/g,"");
    if(v!=0) textoNumerico = textoNumerico.replace(/^0/,"");
	textoFormatado = "";
	
	if (textoNumerico.length == 1) {
		return negativo + "0,0"+textoNumerico;
	} else
	if (textoNumerico.length == 2) {
		return negativo + "0,"+textoNumerico;
	} else {
        for (i=0; i<textoNumerico.length; i++) {
            if (i == textoNumerico.length - 2) {
                textoFormatado += ",";
            }
            if ((i!= 0 && textoNumerico.length-i >= 5) && ((textoNumerico.length-i+1) % 3 == 0)) {
                textoFormatado += ".";
            }
            textoFormatado += textoNumerico.charAt(i);
        }
	    return negativo + textoFormatado;
	}
}

function mask_money_almox(v){ // mascara para 3 casas decimais
    negativo = ''
    if (v[0] == '-') {
        negativo = '-'
    }
    textoNumerico = v.replace(/\D/g,"");
    if(v!=0) textoNumerico = textoNumerico.replace(/^0/,"");
	textoFormatado = "";

	if (textoNumerico.length == 1) {
		return negativo + "0,0"+textoNumerico;
	} else if (textoNumerico.length == 2) {
        return negativo + "0,0" + textoNumerico;
    }else if (textoNumerico.length == 3) {
		return negativo + "0,"+textoNumerico;
	} else {
        for (i=0; i<textoNumerico.length; i++) {
            if (i == textoNumerico.length - 3) {
                textoFormatado += ",";
            }
            if ((i!= 0 && textoNumerico.length-i >= 6) && ((textoNumerico.length-i) % 3 == 0)) {
                textoFormatado += ".";
            }
            textoFormatado += textoNumerico.charAt(i);
        }
	    return negativo + textoFormatado;
	}
}

function mask_nota(element, decimal){
    v = element.value;
    v = v.replace(/\D/g, '');
    if (decimal == 1){
        if(v == 10){
            element.setAttribute("maxlength", "4")    
        }else{
            element.setAttribute("maxlength", "2")
        }
        v = v.replace(/^(\d+)(\d{1})$/, '$1,$2'); 
    }
    else if (decimal == 2){
        if(v == 100){
            element.setAttribute("maxlength", "5")    
        }else{
            element.setAttribute("maxlength", "4")
        }
        if(v.length == 2){
            v = v.replace(/^(\d+)(\d{1})$/, '$1,$2'); 
        }else{
            v = v.replace(/^(\d+)(\d{2})$/, '$1,$2'); 
        }
    }
    element.value = v;
}

function substitui_prefixo(){
    // Substitui os __prefix__ dos autocompletes no django-inline-formset
    var objs = $('input[id$=-TOTAL_FORMS]:last');                                 // total de formulários inline criados
    objs.each(function(index, obj){
        var form_name = $(obj).attr('name');                                      // nome do formulário
        form_name = form_name.replace('-TOTAL_FORMS', '');                        // prefixo do formulário sem o -TOTAL_FORMS
        var last_value = $(obj).attr('value') - 1;                                // último incremento do formulário
        var last_form = $('#'+form_name+'-'+last_value+':last');                  // recupera o último formulário adicionado
        last_form.children('fieldset').each(function(iindex, iobj){
            var newFormHtml = $(iobj).html()                                      // substitui todos os __prefix__ pelo
                .replace(new RegExp('__prefix__', 'g'), last_value)               // último incremento do formulário
                .replace(new RegExp('<\\\\/script>', 'g'), '</script>');
            $(iobj).html(newFormHtml);

            $(iobj).find('span.select2').each(function (windex, wobj) { // resolve o bug do autocompletar ao chamar o
                $(wobj).last().remove(); // select2 novamente e esconde o componente excedente
            });
        });
    });
}


function mask_decimal(v, d) {
    negativo = ''

    if (v[0] == '-') {
        negativo = '-'
    }
}

$(document).ready(function(){
   sync_widgets(); 
});

$(window).on("load", function(){
    $(".add-row a").click(function(){
        sync_widgets();
    });
});