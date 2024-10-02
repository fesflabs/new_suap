$(document).ready(function() {
    $("#captcha-row").hide();

    var username = $("#id_username");
    username.focus();
    username.blur(
        function(){
            if(username.val()){
                $.ajax({
                    url: "/comum/login_exige_captcha/"+username.val()+"/",
                    success:function(data) {
                        if(data === 'OK'){
                            $("#captcha-row").show();
                        } else {
                            $("#captcha-row").hide();
                        }
                    }
                })
            }
        }
    );

    $('input[type="submit"]').on('click', function() {
        var user = $('#id_username');
        var password = $('#id_password');
        var form = $(this.form);
        var elem = $(this);
        if(user.val() && password.val()){
            elem.attr("disabled", "disabled");
            elem.val("Aguarde...");
            form.submit();
        }
    });
});