/**
 * Created by diegosaraiva on 27/01/17.
 */
function log_text(s) {
    var d = document.createElement("div");
    d.innerHTML = s;
    document.getElementById('log').appendChild(d);
}
//For getting CSRF token
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function error_handle(err)
{
    switch(err) {
        case "user_cancel":
            console.log("user has explicitly cancelled the operation via GUI or via pinpad");
            break;
        case "no_certificates":
            console.log("No certificates available for the plugin for listing");
            break;
        case "invalid_argument":
            console.log("Developer has sent an invalid argument to the API.");
            break;
        case "technical_error":
            console.log("Unexpected technical error in the plugin");
            break;
        case "no_implementation":
            console.log("No plugins or extensions or necessary platform support found");
            break;
        case "not_allowed":
            console.log("execution not allowed by policy (like not using https)");
            break;
        case "pin_blocked":
            console.log("The smart card is blocked");
            break;
        default:
            console.log(err);
    }
}
function debug() {
    window.hwcrypto.debug().then(function(response) {
        console.log("Debug: " + response);
    });
}

function sign(hash, role, form, url) {
    // Timestamp
    var timestamp = new Date().toUTCString();
    // Select hash
    var hashtype = "SHA-256";
    // Set backend
    var backend =  "chrome";
    // Get language
    var lang = "en";

    var role = document.getElementById("id_papel").value;
    console.log("sign() clicked on " + timestamp);

    if (!window.hwcrypto.use(backend)) {
        console.log("Selecting backend failed.");
    }
    // debug
    window.hwcrypto.debug().then(function(response) {
            console.log("Debug: " + response);
        }, function(err) {
            error_handle(err);
            return;
        }
    );

    // Sign
    console.log("Signing " + hashtype + ": " + hash + " with " + role);
    window.hwcrypto.getCertificate({lang: lang}).then(function(certificate)
    {

        console.log("Using certificate:\n" + hexToPem(certificate.hex));
        window.hwcrypto.sign(certificate, {type: hashtype, hex: hash}, {lang: lang}).then(function(signature)
        {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                        // Only send the token to relative URLs i.e. locally.
                        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
                    }
                }
            });
            var form_data = form.serializeArray();
            form_data.push({name: 'cert', value: hexToPem(certificate.hex)});
            form_data.push({name: 'sig',  value: signature.hex});
            form_data.push({name: 'data', value: hash});
            form_data.push({name: 'role', value: role});
            form_data.push({name: 'csrfmiddlewaretoken', value: getCookie('csrftoken')});
            $.ajax({
                method: "POST",
                url: url,
                data: form_data,
                success: function (data) {
                    form.off('submit').submit();
                }
            });
        }, function(error) {
            error_handle(error);
            window.location.reload();
        });
    }, function(error) {
        error_handle(error);
        window.location.reload();
    });
}
