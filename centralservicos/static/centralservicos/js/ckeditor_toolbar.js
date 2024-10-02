jQuery(document).ready(function () {
    if (CKEDITOR.status != 'loaded') {
        CKEDITOR.on('loaded', plugin_save);
    } else {
        plugin_save(null);
    }
});

function plugin_save(evt) {
    CKEDITOR.plugins.registered['save'] = {
        init: function (editor) {
            var command = editor.addCommand('save', {
                modes: {wysiwyg: 1, source: 1},
                readOnly: 1,
                exec: function (editor) {
                    if (editor.fire('save')) {
                        var $form = editor.element.$.form;
                        if (validarTags()) {
                            if ($form) {
                                try {
                                    $form.submit();
                                } catch (e) {
                                    if ($form.submit.click) {
                                        $form.submit.click();
                                    }
                                }
                            }
                        }
                    }
                }
            });
            editor.ui.addButton('Save', {label: 'Salvar', command: 'save'});
        }
    }
}
var arrImgPermitida = Array('png', 'jpg', 'jpeg');
var validarTags = function () {
    for (inst in CKEDITOR.instances) {
        var editor = CKEDITOR.instances[inst];
        if (!editor.readOnly) {
            var data = editor.getData();
            var tags = ['img', 'button', 'input', 'select', 'iframe', 'frame', 'embed', 'object', 'param', 'video', 'audio', 'form'];
            for (var i = 0; i < tags.length; i++) {
                var elements = editor.document.getElementsByTag(tags[i]);
                if (elements.count() > 0) {
                    switch (tags[i]) {
                        case 'img':
                            var erro = false;
                            if (arrImgPermitida.length == 0) {
                                alert('Não são permitidas imagens no conteúdo.');
                                erro = true;
                                break;
                            } else {
                                var posIni = null;
                                var posFim = null;
                                var n = elements.count();
                                for (var j = 0; j < n; j++) {
                                    ImgSrc = elements.getItem(j).getAttribute('src');
                                    posIni = ImgSrc.indexOf('/');
                                    if (posIni != -1) {
                                        posFim = ImgSrc.indexOf(';', posIni);
                                        if (posFim != -1) {
                                            posIni = posIni + 1;
                                            if (arrImgPermitida.indexOf(ImgSrc.substr(posIni, (posFim - posIni))) == -1) {
                                                alert('Imagem formato "' + ImgSrc.substr(posIni, (posFim - posIni)) + '" não permitida.');
                                                erro = true;
                                                break;
                                            }
                                        } else {
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