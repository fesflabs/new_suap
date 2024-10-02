
jQuery(document).ready(function ()
{
    if (CKEDITOR.status != 'loaded')
    {
        CKEDITOR.on('loaded', plugin_save);
    }
    else
    {
        plugin_save(null);
    }
});

function plugin_save(evt)
{
    CKEDITOR.plugins.registered['save'] = {
        init: function (editor) {
            let command = editor.addCommand('save', {
                modes: { wysiwyg: 1, source: 1 },
                readOnly: 1,
                exec: function (editor)
                {
                      salvar_tags(editor)
                }
            });
            editor.ui.addButton('Save', {label: 'Salvar', command: 'save'});
        }
    }
}

var salvar_div = function (editor)
{
    count = editor.id.match(/\d+/)[0];
    let id_div = 'cke_ruler_wrap' + count;
    let valueInput = document.getElementById(id_div);
    if (valueInput)
    {
        let left = valueInput.getAttribute('data-left');
        let right = valueInput.getAttribute('data-right');
        let main_body = editor.document.getBody();
        let element = main_body.getLast();
        let html_content = null;
        let suap_div = '<div id="suap-ckeditor"' + ' style="padding:' + valueInput.getAttribute('padding') +
            '" data-left="' + left + '" data-right="' + right + '">';
        if (element.getId() != "suap-ckeditor")
        {
            html_content = main_body.getHtml();
            html_content = suap_div + html_content + "</div>";
        }
        else
        {
            html_content = suap_div + element.getHtml() + "</div>";
        }
        editor.setData(html_content);
    }
    if (editor.fire('save')) {
        let $form = editor.element.$.form;
        if (validarTags()) {
            if ($form) {
                try {
                    $form.submit();
                }
                catch (e) {
                    if ($form.submit.click) {
                        $form.submit.click();
                    }
                }
            }
        }
    }
};
var salvar_tags = function ()
{
    for (let inst in CKEDITOR.instances)
    {
        let editor = CKEDITOR.instances[inst]
        if (!editor.readOnly)
        {
            salvar_div(editor);
        }
    }
};
let arrImgPermitida = Array('png', 'jpg', 'jpeg');
var validarTags = function ()
{
    for (let inst in CKEDITOR.instances)
    {
        let editor = CKEDITOR.instances[inst];
        if (!editor.readOnly)
        {
            let data = editor.getData();
            // encontrar variáveis no padrão {{ variavel }}
            let variaveis = data.match(/\{\{([^}]+)\}\}/g);
            if(variaveis)
            {
                for (let i = 0; i < variaveis.length; i++)
                {
                    let variavel = variaveis[i];
                    let regexpNames = /{{\s*(?<variavel>\w+)\s*}}/mg;
                    if (regexpNames.exec(variavel) == null){
                        let decoded_variavel = $("<div/>").html(variavel).text();
                        alert(`Variável inválida ${decoded_variavel}`);
                        return false;
                    }
                }
            }

            let tags = [
                'img', 'button', 'input', 'select', 'iframe', 'frame',
                'embed', 'object', 'param', 'video', 'audio', 'form'
            ];
            for (let i = 0; i < tags.length; i++)
            {
                let elements = editor.document.getElementsByTag(tags[i]);
                if (elements.count() > 0)
                {
                    switch (tags[i])
                    {
                        case 'img':
                            let erro = false;
                            if (arrImgPermitida.length == 0)
                            {
                                alert('Não são permitidas imagens no conteúdo.');
                                erro = true;
                                break;
                            }
                            else
                            {
                                let posIni = null;
                                let posFim = null;
                                let n = elements.count();
                                for (var j = 0; j < n; j++) {
                                    let ImgSrc = elements.getItem(j).getAttribute('src');
                                    posIni = ImgSrc.indexOf('/');
                                    if (posIni != -1)
                                    {
                                        posFim = ImgSrc.indexOf(';', posIni);
                                        if (posFim != -1)
                                        {
                                            posIni = posIni + 1;
                                            if (arrImgPermitida.indexOf(ImgSrc.substr(posIni, (posFim - posIni))) == -1)
                                            {
                                                alert('Imagem formato "' + ImgSrc.substr(posIni, (posFim - posIni)) + '" não permitida.');
                                                erro = true;
                                                break;
                                            }
                                        }
                                        else
                                        {
                                            alert('Não são permitidas imagens referenciadas.');
                                            erro = true;
                                            break;
                                        }
                                    }
                                }
                            }
                            if (erro) break;
                            continue;
                        case 'button':
                        case 'input':
                        case 'select':
                            alert('Não são permitidos componentes de formulário HTML no conteúdo.');
                            break;

                        case 'iframe':
                            alert('Não são permitidos formulários ocultos no conteúdo.');
                            break;

                        case 'frame':
                        case 'form':
                            alert('Não são permitidos formulários no conteúdo.');
                            break;

                        case 'embed':
                        case 'object':
                        case 'param':
                            alert('Não são permitidos objetos no conteúdo.');
                            break;

                        case 'video':
                            alert('Não são permitidos vídeos no conteúdo.');
                            break;

                        case 'audio':
                            alert('Não é permitido áudio no conteúdo.');
                            break;
                    }
                    return false;
                }
            }
        }
    }
    return true;
};
