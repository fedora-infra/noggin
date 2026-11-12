$(document).ready(function () {
  var btn = $("#passkey-login-btn");

  if (!window.PublicKeyCredential) {
    btn
      .prop("disabled", true)
      .attr("title", "Your browser does not support WebAuthn");
    return;
  }

  btn.prop("disabled", false);

  btn.click(function (e) {
    e.preventDefault();
    btn.prop("disabled", true).text("Authenticating…");
    $("#passkey-login-error").addClass("d-none");

    var username = $("#login-username").val();
    if (!username) {
      showError("Please enter your username first.");
      btn.prop("disabled", false).text("Sign in with Passkey");
      return;
    }

    $.ajax({
      url: PASSKEY_LOGIN_BEGIN_URL,
      method: "POST",
      contentType: "application/json",
      headers: { "X-CSRFToken": PASSKEY_LOGIN_CSRF_TOKEN },
      data: JSON.stringify({ username: username }),
      success: function (options) {
        var publicKeyOptions = {
          challenge: base64urlToBuffer(options.challenge),
          rpId: options.rpId,
          timeout: options.timeout,
          userVerification: options.userVerification,
          allowCredentials: (options.allowCredentials || []).map(function (c) {
            return { type: c.type, id: base64urlToBuffer(c.id) };
          }),
        };

        navigator.credentials
          .get({ publicKey: publicKeyOptions })
          .then(function (assertion) {
            var payload = {
              id: bufferToBase64url(assertion.rawId),
              response: {
                clientDataJSON: bufferToBase64url(
                  assertion.response.clientDataJSON
                ),
                authenticatorData: bufferToBase64url(
                  assertion.response.authenticatorData
                ),
                signature: bufferToBase64url(assertion.response.signature),
              },
            };

            $.ajax({
              url: PASSKEY_LOGIN_COMPLETE_URL,
              method: "POST",
              contentType: "application/json",
              headers: { "X-CSRFToken": PASSKEY_LOGIN_CSRF_TOKEN },
              data: JSON.stringify(payload),
              success: function (result) {
                if (result.redirect) {
                  window.location.href = result.redirect;
                } else {
                  window.location.reload();
                }
              },
              error: function (xhr) {
                var msg = "Authentication failed";
                try {
                  msg = JSON.parse(xhr.responseText).error || msg;
                } catch (e) {}
                showError(msg);
                btn.prop("disabled", false).text("Sign in with Passkey");
              },
            });
          })
          .catch(function (err) {
            var msg;
            switch (err.name) {
              case "NotAllowedError":
                msg = "Authentication was cancelled or timed out.";
                break;
              case "SecurityError":
                msg = "Security error. Please ensure you're using HTTPS.";
                break;
              default:
                msg = err.message;
            }
            showError(msg);
            btn.prop("disabled", false).text("Sign in with Passkey");
          });
      },
      error: function (xhr) {
        var msg = "Could not start passkey authentication";
        try {
          msg = JSON.parse(xhr.responseText).error || msg;
        } catch (e) {}
        showError(msg);
        btn.prop("disabled", false).text("Sign in with Passkey");
      },
    });
  });

  function showError(msg) {
    $("#passkey-login-error").text(msg).removeClass("d-none");
  }

  function base64urlToBuffer(b64url) {
    var b64 = b64url.replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4) b64 += "=";
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  function bufferToBase64url(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = "";
    for (var i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary)
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=/g, "");
  }
});
