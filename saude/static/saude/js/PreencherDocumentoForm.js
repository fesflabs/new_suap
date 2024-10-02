$(document).ready(function(){

    $('input[name=visualizar]').click(function (event) {
        csrf_token = $('input[name=csrfmiddlewaretoken]').val();

        form = new FormData();
        form.append('texto', CKEDITOR.instances['id_texto'].getData());
        form.append('data', $('input[name=data]').val());
        form.append('tipo', window.location.pathname.split('/')[4]);

        $.ajax({
            headers: { "X-CSRFToken": csrf_token },
            url: '/saude/previsualizar_documento_prontuario/',
            data: form,
            processData: false,
            contentType: false,
            type: 'POST',
            xhrFields: {
                responseType: 'blob'
            },
            success: function (data) {
                var blob = new Blob([data], { type: 'application/pdf' });
                if (window.navigator && window.navigator.msSaveOrOpenBlob) {
                    window.navigator.msSaveOrOpenBlob(blob); // for IE
                } else {
                    var fileURL = URL.createObjectURL(blob);
                    window.open(fileURL);
                }
            }
        });
    });
})
