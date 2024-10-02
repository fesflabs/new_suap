function popupTransferencia(diario) {
    var inputs = $("input[name='del_residente_diario']");
    var pks = [];
    for (u = 0; u < inputs.length; u++) {
        if (inputs[u].checked) {
            pks.push(inputs[u].value);
        }
    }

    pks = pks.join("_");
    if (pks.length > 0) {
        pks = pks + "/";
    }

    if (pks.length == 0) {
        alert('Por favor, selecione o(s) residente(s) que deseja transferir.');
    }
    else {
        document.location.href = "/residencia/transferir_diario/" + diario + "/" + pks;
    }
}