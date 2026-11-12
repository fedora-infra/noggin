$(document).ready(function () {
  var btn = $("#register-passkey-btn");

  if (!window.PublicKeyCredential) {
    btn
      .prop("disabled", true)
      .attr("title", "Your browser does not support WebAuthn");
    return;
  }

  btn.click(function () {
    btn.prop("disabled", true).text("Registering…");
    $("#passkey-error").addClass("d-none");
    $("#passkey-success").addClass("d-none");

    $.ajax({
      url: PASSKEY_REGISTER_BEGIN_URL,
      method: "POST",
      contentType: "application/json",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      data: JSON.stringify({}),
      success: function (options) {
        var publicKeyOptions = {
          challenge: base64urlToBuffer(options.challenge),
          rp: options.rp,
          user: {
            id: base64urlToBuffer(options.user.id),
            name: options.user.name,
            displayName: options.user.displayName,
          },
          pubKeyCredParams: options.pubKeyCredParams,
          excludeCredentials: (options.excludeCredentials || []).map(
            function (c) {
              return { type: c.type, id: base64urlToBuffer(c.id) };
            }
          ),
          authenticatorSelection: options.authenticatorSelection,
          timeout: options.timeout,
          attestation: options.attestation,
        };

        navigator.credentials
          .create({ publicKey: publicKeyOptions })
          .then(function (credential) {
            var payload = {
              id: bufferToBase64url(credential.rawId),
              response: {
                clientDataJSON: bufferToBase64url(
                  credential.response.clientDataJSON
                ),
                attestationObject: bufferToBase64url(
                  credential.response.attestationObject
                ),
              },
            };

            $.ajax({
              url: PASSKEY_REGISTER_COMPLETE_URL,
              method: "POST",
              contentType: "application/json",
              headers: { "X-CSRFToken": CSRF_TOKEN },
              data: JSON.stringify(payload),
              success: function () {
                window.location.reload();
              },
              error: function (xhr) {
                var msg = "Registration failed";
                try {
                  msg = JSON.parse(xhr.responseText).error || msg;
                } catch (e) {}
                showError(msg);
                btn.prop("disabled", false).text("Add Passkey");
              },
            });
          })
          .catch(function (err) {
            var msg;
            switch (err.name) {
              case "NotAllowedError":
                msg = "Registration was cancelled or timed out.";
                break;
              case "InvalidStateError":
                msg = "This authenticator is already registered.";
                break;
              case "SecurityError":
                msg = "Security error. Please ensure you're using HTTPS.";
                break;
              default:
                msg = err.message;
            }
            showError(msg);
            btn.prop("disabled", false).text("Add Passkey");
          });
      },
      error: function (xhr) {
        var msg = "Could not start registration";
        try {
          msg = JSON.parse(xhr.responseText).error || msg;
        } catch (e) {}
        showError(msg);
        btn.prop("disabled", false).text("Add Passkey");
      },
    });
  });

  function showError(msg) {
    $("#passkey-error").text(msg).removeClass("d-none");
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
