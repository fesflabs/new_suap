function checar_criterio_avaliacao() {
    if (document.getElementById('id_criterio_avaliacao_0').checked) {
        $('#id_media_aprovacao_sem_prova_final').parent().parent().show();
    } else {
        $('#id_media_aprovacao_sem_prova_final').parent().parent().hide();

        $('#id_media_aprovacao_sem_prova_final').val('');

    }
}



jQuery(function () {

    $('#id_criterio_avaliacao_0').click(function () {
        checar_criterio_avaliacao();
    });
    $('#id_criterio_avaliacao_1').click(function () {
        checar_criterio_avaliacao();
    });

    checar_criterio_avaliacao();
});
