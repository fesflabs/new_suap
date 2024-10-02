function get_hora_min_seg(segundos) {
    var t_horas = Math.trunc(segundos / 3600);
    var aux = segundos % 3600;
    var t_minutos = Math.trunc(aux / 60);
    var t_segundos = aux % 60;
    return [t_horas, t_minutos, t_segundos];
}

function formata_segundos(segundos, hora_min_seg_com_dois_digitos) {
    var h_m_s = get_hora_min_seg(segundos);
    var result = '';
    if (h_m_s[0] !== 0) {
        if (hora_min_seg_com_dois_digitos === true && h_m_s[0] <= 9)
            result += '0';
        result += h_m_s[0] + "h ";
    }
    if (h_m_s[1] !== 0){
        if (hora_min_seg_com_dois_digitos === true && h_m_s[1] <= 9)
            result += '0';
        result += h_m_s[1] + "min ";
    }
    if (h_m_s[2] !== 0){
        if (hora_min_seg_com_dois_digitos === true && h_m_s[2] <= 9)
            result += '0';
        result += h_m_s[2] + "seg ";
    }
    result = result.trim();
    if (result.length === 0){
        if (hora_min_seg_com_dois_digitos === true)
            result += '0';
        result += '0h';
    }
    return result
}

function get_dia_mes_ano(aaaammdd){
    // 01234567
    // aaaammdd
    var ano = aaaammdd.substr(0, 4);
    var mes = aaaammdd.substr(4, 2);
    var dia = aaaammdd.substr(6, 2);
    //
    return [dia, mes, ano];
}
