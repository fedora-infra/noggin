=====================
OTP Recovery Codes
=====================

:Author: Alexander Bokovoy
:Status: Implemented
:Created: 2026-07-02

.. contents:: Table of Contents
   :local:
   :depth: 2


Problem Statement
=================

When a Noggin user enrolls an OTP token for two-factor authentication,
losing the authenticator device (phone loss, factory reset, hardware
failure) locks them out completely. FreeIPA enforces OTP once any token
is active for the user — there is no fallback. The only recovery path
today requires an IPA administrator to delete the lost token and
provision a new one.

This is unacceptable for a self-service portal. Users must have a
recovery mechanism they can set up *before* lockout occurs, without
requiring administrator intervention.


Goals
=====

1. Allow users to generate a set of single-use recovery codes during OTP
   enrollment.
2. Any recovery code can be used in place of a TOTP code at any login
   prompt (Noggin, SSH, FreeIPA WebUI, etc.).
3. No changes to FreeIPA schema, ``ipa-otpd``, or 389-ds SLAPI plugins.
4. Fit naturally into Noggin's existing OTP management UI.
5. Recovery codes can be regenerated (invalidating all previous codes).


Non-Goals
=========

- Out-of-band identity verification (email link, manager approval) for
  locked-out users who never set up recovery codes.
- Per-token HOTP authentication window overrides (requires FreeIPA
  schema changes).


Design
======

Overview
--------

Recovery codes are implemented as an **always-active HOTP token** owned
by the user. Each recovery code is a pre-computed HOTP value for a
sequential counter position. Because the token stays enabled, the
FreeIPA OTP validation path accepts recovery codes alongside the user's
primary TOTP token with no server-side changes.

This is the same pattern used by Google, GitHub, and most services that
offer backup codes for 2FA.


How It Works in FreeIPA
-----------------------

FreeIPA's OTP validation happens inside the ``ipa-pwd-extop`` SLAPI
plugin (``prepost.c:ipapwd_pre_bind_otp()``). When a user authenticates
with ``password + OTP``:

1. The plugin calls ``otp_token_find()`` which searches LDAP for all
   **active** tokens owned by the user. The LDAP filter excludes
   disabled tokens (``ipatokenDisabled=TRUE``) and tokens outside their
   validity window.

2. ``otp_token_validate_berval()`` iterates over all matching tokens and
   tries to validate the OTP code from the end of the password string
   against each token (TOTP or HOTP).

3. For an HOTP token, validation checks the code against
   ``counter + offset`` for offsets 0 through ``ipatokenHOTPauthWindow``
   (default: 10). On success, the counter advances past the matched
   position. The counter never goes backwards, so each code is
   single-use.

Because the recovery HOTP token is active and owned by the user, it
participates in this validation loop transparently. No changes to the
FreeIPA C code, Python plugins, or LDAP schema are needed.


Identifying Recovery Tokens
----------------------------

FreeIPA has no ``ipatokenPurpose`` attribute. Recovery tokens are
distinguished by convention:

- **Description**: Set to ``"Recovery codes"`` (the literal string, not
  localized in LDAP — localization is only in the Noggin UI).
- **Token type**: ``hotp`` (as opposed to ``totp`` for the primary
  token).

Noggin identifies a user's recovery token by loading all tokens and
filtering with the ``is_recovery(description)`` method::

    desc = current_app.config['OTP_RECOVERY_DESCRIPTION']
    recovery_token = next(
        (t for t in all_tokens if t.is_recovery(desc)), None
    )

When generating or regenerating codes, the route also does a targeted
search::

    ipa.otptoken_find(
        o_ipatokenowner=username,
        o_type='hotp',
        o_description=current_app.config['OTP_RECOVERY_DESCRIPTION'],
    )

The description is a convention, not an enforcement mechanism. A user
who renames the token via IPA CLI breaks the lookup, but the codes still
work for authentication. Noggin hides the rename/disable/delete buttons
for recovery tokens and blocks renaming a regular token to the recovery
description.


Code Count and HOTP Auth Window
-------------------------------

The default ``ipatokenHOTPauthWindow`` is **10**, meaning the server
accepts codes up to 10 counter positions ahead of the current counter.
This constrains the design:

- **Generate exactly 10 codes** (counter positions 0–9).
- If the user uses code #7 first, the counter advances to 8. Codes 0–6
  become permanently invalid. Codes 8 and 9 remain valid.
- Generating more than 10 codes would fail: code #15 is 15 positions
  ahead of counter 0, exceeding the auth window.

The global HOTP auth window is configurable via ``ipa otpconfig-mod
--hotpauthwindow=N``, but this is a deployment decision and not
something Noggin should change.


Implementation Plan
===================

1. Configuration
----------------

Add to ``noggin/defaults.py``::

    # Number of recovery codes to generate. Must not exceed the FreeIPA
    # ipatokenHOTPauthWindow (default: 10).
    OTP_RECOVERY_CODE_COUNT = 10
    # Description string used to identify recovery tokens in LDAP.
    OTP_RECOVERY_DESCRIPTION = "Recovery codes"

The code count is a configuration value rather than a hard-coded constant
so deployments with a larger ``ipatokenHOTPauthWindow`` can increase it.


2. Recovery Code Generation Utility
------------------------------------

A helper in ``noggin/utility/recovery_codes.py`` computes HOTP codes
from a Base32-encoded key::

    from pyotp import HOTP

    def generate_recovery_codes(secret_b32: str, count: int) -> list[str]:
        """Pre-compute HOTP codes for counter positions 0..count-1.

        Returns a list of zero-padded 8-digit code strings.
        """
        hotp = HOTP(secret_b32, digits=8)
        return [hotp.at(i) for i in range(count)]

Using 8 digits (vs 6 for TOTP) makes recovery codes visually distinct
from regular OTP codes, reducing user confusion. The ``pyotp`` library
already supports HOTP; no new dependencies are needed.


3. OTPToken Representation
---------------------------

``noggin/representation/otptoken.py`` exposes the HOTP counter and a
method to identify recovery tokens::

    class OTPToken(Representation):
        attr_names = {
            "uniqueid": "ipatokenuniqueid",
            "description": "description",
            "disabled": "ipatokendisabled",
            "counter": "ipatokenhotpcounter",
        }
        attr_types = {
            "disabled": "bool",
            "counter": "int",
        }
        pkey = "uniqueid"
        ipa_object = "otptoken"

        @property
        def uri(self):
            return self.raw.get('uri')

        def is_recovery(self, recovery_description):
            token_type = self.raw.get('type') or ''
            if isinstance(token_type, list):
                token_type = token_type[0] if token_type else ''
            return (
                token_type.lower() == 'hotp'
                and self.description == recovery_description
            )

``is_recovery`` is a **method** (not a property) that takes the
recovery description string as a parameter. This decouples the
``OTPToken`` class from the Flask application context — the caller
passes ``current_app.config['OTP_RECOVERY_DESCRIPTION']`` rather than
the representation reading it from ``current_app`` directly.

The ``type`` field is a virtual attribute that FreeIPA computes from the
LDAP objectClass (``ipatokenTOTP`` → ``"TOTP"``, ``ipatokenHOTP`` →
``"HOTP"``). It is returned by ``otptoken_find`` and ``otptoken_show``
but is **not** included in ``attr_names`` because FreeIPA returns it as
a plain string (not a list) or sometimes as a list, depending on
context. The method reads from ``self.raw`` directly and handles both
cases.

The ``counter`` attribute uses an ``int`` converter (added to
``noggin/representation/base.py``) to parse the HOTP counter value,
which is used to compute how many recovery codes remain.


4. Forms
--------

Add to ``noggin/form/edit_user.py``::

    class UserSettingsGenerateRecoveryForm(ModestForm):
        password = PasswordField(
            _('Enter your current password'),
            validators=[DataRequired(message=_('You must provide a password'))],
        )
        otp = StringField(
            _('One-Time Password'),
            validators=[Optional()],
        )
        submit = SubmitButtonField(_("Generate Recovery Codes"))


    class UserSettingsRegenerateRecoveryForm(ModestForm):
        password = PasswordField(
            _('Enter your current password'),
            validators=[DataRequired(message=_('You must provide a password'))],
        )
        otp = StringField(
            _('One-Time Password'),
            validators=[Optional()],
        )
        submit = SubmitButtonField(_("Regenerate Recovery Codes"))

Two distinct form classes allow ``ModestForm``'s submit-button detection
to distinguish which action the user intends on a page with both forms.


5. Controller Routes
--------------------

All OTP routes live in ``noggin/controller/user_otp.py`` (extracted from
``user.py`` for maintainability). The module includes a
``_reauthenticate(form, auth_username)`` helper that consolidates the
password+OTP re-authentication pattern used by the generate, regenerate,
and admin reset routes.

``POST /user/<username>/settings/otp/recovery/generate``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generates a new set of recovery codes. Steps:

1. Validate ``UserSettingsGenerateRecoveryForm``.
2. Re-authenticate the user with ``maybe_ipa_login()`` (password +
   existing OTP).
3. Check that the user has no existing recovery token (to prevent
   duplicates).
4. Generate a 35-byte random key:
   ``b32encode(os.urandom(OTP_KEY_LENGTH)).decode('ascii')``.
5. Create the HOTP token in FreeIPA::

       ipa.otptoken_add(
           o_ipatokenowner=username,
           o_type='hotp',
           o_ipatokenotpkey=secret,
           o_ipatokenotpdigits=8,
           o_ipatokenotpalgorithm='sha256',
           o_description='Recovery codes',
       )

6. Compute HOTP codes 0..9 from the key using ``generate_recovery_codes()``.
7. Render a page showing the codes with a strong warning to save them.

``POST /user/<username>/settings/otp/recovery/regenerate``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Regenerates recovery codes (invalidates all previous ones). Steps:

1. Validate ``UserSettingsRegenerateRecoveryForm``.
2. Re-authenticate the user.
3. Find and delete the existing recovery token::

       tokens = ipa.otptoken_find(
           o_ipatokenowner=username,
           o_type='hotp',
           o_description='Recovery codes',
       )
       for t in tokens['result']:
           ipa.otptoken_del(
               a_ipatokenuniqueid=t['ipatokenuniqueid'][0],
           )

4. Create a new HOTP token and compute codes (same as generate flow).
5. Render the codes page.


6. OTP Settings Page Changes
-----------------------------

``user_settings_otp()`` in ``noggin/controller/user_otp.py``:

- Passes ``generate_recovery_form`` and ``regenerate_recovery_form`` to
  the template.
- Separates tokens into regular tokens and recovery tokens using the
  ``_categorize_tokens()`` helper::

      def _categorize_tokens(all_tokens):
          desc = current_app.config['OTP_RECOVERY_DESCRIPTION']
          tokens = [t for t in all_tokens if not t.is_recovery(desc)]
          tokens.sort(key=lambda t: t.description or "")
          recovery_token = next(
              (t for t in all_tokens if t.is_recovery(desc)), None
          )
          return tokens, recovery_token

- Passes ``recovery_token`` and the forms to the template.


7. Template Changes
-------------------

Shared recovery code display logic is in
``noggin/templates/_recovery_codes.html``, which provides two Jinja2
macros:

- ``codes_grid(recovery_codes)`` — renders the 2-column grid of codes
  with Copy and Download buttons.
- ``codes_scripts(download_filename)`` — renders the JavaScript for
  copy-to-clipboard and download-as-text-file functionality.

Both ``user-settings-otp.html`` and ``user-settings-otp-admin-reset.html``
import these macros with ``{% import '_recovery_codes.html' as recovery_macros %}``.

Changes to ``user-settings-otp.html``:

Recovery codes section (after the token list)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: html+jinja

   <div class="card-body mt-4">
     <h5>{{ _("Recovery Codes") }}</h5>
     <p class="text-muted">
       {{ _("Recovery codes can be used to sign in if you lose access "
            "to your authenticator app. Each code can only be used once.") }}
     </p>
     {% if recovery_token %}
       <p>
         <span class="badge bg-success">{{ _("Active") }}</span>
         {{ _("You have recovery codes set up.") }}
       </p>
       <form action="{{ url_for('.user_settings_otp_recovery_regenerate',
                        username=current_user.username) }}"
             method="post" class="d-inline">
         <input type="hidden" name="csrf_token"
                value="{{ csrf_token() }}"/>
         {{ regenerate_recovery_form.password(
                placeholder=_("Current password")) }}
         {% if tokens %}
           {{ regenerate_recovery_form.otp(
                  placeholder=_("One-Time Password")) }}
         {% endif %}
         {{ regenerate_recovery_form.submit(color="warning") }}
       </form>
     {% else %}
       <p>
         <span class="badge bg-warning text-dark">{{ _("Not set up") }}</span>
         {{ _("You have no recovery codes. Generate them now to avoid "
              "being locked out if you lose your authenticator device.") }}
       </p>
       <form action="{{ url_for('.user_settings_otp_recovery_generate',
                        username=current_user.username) }}"
             method="post" class="d-inline">
         <input type="hidden" name="csrf_token"
                value="{{ csrf_token() }}"/>
         {{ generate_recovery_form.password(
                placeholder=_("Current password")) }}
         {% if tokens %}
           {{ generate_recovery_form.otp(
                  placeholder=_("One-Time Password")) }}
         {% endif %}
         {{ generate_recovery_form.submit(color="primary") }}
       </form>
     {% endif %}
   </div>

Recovery codes display modal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After generation/regeneration, display the codes in a modal with:

- A grid of 10 codes in monospace font (2 columns × 5 rows).
- A "Copy all" button.
- A "Download as text file" button.
- A prominent warning: *"Save these codes in a safe place. You will not
  be able to see them again."*
- A checkbox: *"I have saved my recovery codes"* that enables the
  "Done" button.

Recovery token in the token list
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The recovery token must **not** appear in the regular token list. It is
shown only in the dedicated recovery codes section. The
``_categorize_tokens()`` helper (applied in the controller, not the
template) separates recovery tokens from regular ones.

First-token enrollment prompt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When a user creates their **first** OTP token, after the TOTP
confirmation step, redirect to the recovery codes generation flow (or
show a strong prompt to generate them). This ensures every OTP user has
recovery codes from day one.

The implementation should add a flash message after successful first
token creation::

    flash(
        Markup(_(
            'The token has been created. <a href="%(url)s">Generate '
            'recovery codes</a> now to avoid being locked out.',
            url=url_for('.user_settings_otp', username=username),
        )),
        "warning",
    )


8. Last-Token Protection Interaction
--------------------------------------

FreeIPA's ``ipa-otp-lasttoken`` SLAPI plugin prevents deleting or
disabling the last active token for a user with OTP-only authentication.
This interacts with recovery codes in two ways:

**Positive**: If the user deletes all their TOTP tokens, the recovery
HOTP token remains as the last active token and cannot be deleted. The
user is not fully locked out — they can still authenticate with
``password + recovery_code``.

**Regeneration edge case**: The regenerate flow deletes the old recovery
token before creating a new one. If the recovery token is the user's
*only* active token, the delete will fail with
``"Can't delete last active token"``. Noggin must handle this error and
tell the user to add a regular OTP token first. In practice this is
unlikely — the user would have to delete all TOTP tokens while keeping
the recovery token, which is a degenerate state.

The regeneration handler should catch this::

    except python_freeipa.exceptions.BadRequest as e:
        if "Can't delete last active token" in e.message:
            flash(
                _('Cannot regenerate recovery codes while they are '
                  'your only active token. Add a regular OTP token '
                  'first.'),
                'warning',
            )
            return redirect(
                url_for('.user_settings_otp', username=username)
            )


Security Considerations
=======================

Recovery codes are always valid
-------------------------------

Unlike a disabled-token approach, recovery codes can be used at any
time, not only when the primary token is lost. This is by design — it
matches industry practice — but it means:

- Recovery codes are an equivalent credential to the TOTP token.
- Compromise of recovery codes = compromise of the second factor.
- The codes page must emphasize secure storage (password manager, printed
  and locked away).

Recovery codes are shown only once
-----------------------------------

The HOTP key is stored in LDAP with ``no_display`` — it cannot be read
back after creation. Noggin computes the codes client-side (in the
controller) immediately after ``otptoken_add`` and renders them in the
response. The codes are never stored by Noggin (no database, no session,
no file).

If the user loses the codes without using them, they must regenerate
(which requires authentication with password + existing OTP).

Brute-force resistance
-----------------------

8-digit codes provide 10^8 (100 million) possible values. FreeIPA's
authentication lockout policy (``krbMaxFailCount``) applies to OTP
failures, so brute-force is rate-limited at the IPA level. No additional
rate limiting is needed in Noggin.

Counter exhaustion
------------------

After all 10 recovery codes are used, the HOTP counter is at 10. Any
further codes would need to be within the auth window of the current
counter — since there are no pre-computed codes for counter ≥ 10, the
token becomes effectively inert. The user must regenerate codes.

The ``_get_recovery_codes_remaining()`` helper in
``noggin/controller/user_otp.py`` queries ``ipatokenHOTPcounter`` via
``otptoken_show`` and computes the remaining count. The OTP settings
page displays "N codes remaining" with status badges. When the remaining
count drops to ``OTP_RECOVERY_LOW_THRESHOLD`` (default: 3) or below, a
warning badge is shown. When all codes are exhausted, a danger badge
prompts immediate regeneration.


Testing Plan
============

Unit tests
----------

Tests in ``tests/unit/controller/test_user_otp.py`` (64 tests). The
recovery code tests use mock-based testing (``mock_ipa_client`` fixture)
instead of VCR cassettes, since VCR cassettes are fragile and these
routes were added after the original cassettes were recorded. Admin
reset tests use a ``mock_admin_client`` fixture that provides a
logged-in admin session with mocked IPA admin.

**Core recovery code tests:**

- **test_recovery_generate**: Create a recovery token, verify 10
  eight-digit codes are returned in the response.
- **test_recovery_generate_requires_auth**: Wrong password returns
  error.
- **test_recovery_generate_duplicate**: Generating codes when a
  recovery token already exists returns an error.
- **test_recovery_regenerate**: Old token is deleted and a new one
  is created with fresh codes.
- **test_recovery_regenerate_last_token**: Graceful handling when the
  recovery token is the user's last active token.
- **test_recovery_generate_ipa_error**: IPA error during token
  creation shows error message.
- **test_recovery_token_hidden_from_list**: Recovery token does not
  appear in the regular token list.
- **test_recovery_token_no_rename**: Recovery token has no rename
  button in the UI.
- **test_rename_to_recovery_description_blocked**: Renaming a regular
  token to the recovery description is rejected.
- **test_recovery_generate_no_permission**: Cannot generate codes for
  another user.
- **test_recovery_regenerate_no_permission**: Cannot regenerate codes
  for another user.
- **test_recovery_generate_invalid_form**: Missing password returns
  validation error.
- **test_recovery_regenerate_delete_error**: IPA error during old
  recovery token deletion shows error message.
- **test_recovery_generate_cache_control**: Recovery code response
  includes ``Cache-Control: no-store``.

**Remaining code count tests:**

- **test_recovery_codes_remaining_display**: Remaining count and green
  "Active" badge appear when codes are available.
- **test_recovery_codes_remaining_low_warning**: Warning badge appears
  when codes are at or below the low threshold.
- **test_recovery_codes_remaining_zero**: Danger badge and
  "Exhausted" message when all codes are used.

**Mandatory recovery code tests:**

- **test_mandatory_recovery_codes_on_first_token**: With
  ``OTP_REQUIRE_RECOVERY_CODES`` enabled, confirming the first OTP
  token auto-generates recovery codes and shows the modal.
- **test_mandatory_recovery_codes_disabled**: With the config
  disabled (default), first token redirect with warning flash.
- **test_mandatory_recovery_codes_already_has_recovery**: No
  auto-generation when the user already has a recovery token.
- **test_mandatory_recovery_codes_auto_generate_failure**: IPA error
  during auto-generation falls back to a warning flash.

**Admin-assisted recovery tests:**

- **test_admin_otp_reset_get**: Admin sees the confirmation page with
  the target user's current tokens listed.
- **test_admin_otp_reset_post**: Admin resets OTP, all tokens deleted,
  recovery codes generated and shown.
- **test_admin_otp_reset_no_permission**: Non-admin user is rejected.
- **test_admin_otp_reset_self**: Admin trying to reset their own OTP
  redirects to normal OTP settings.
- **test_admin_otp_reset_disabled**: Route returns 404 when
  ``OTP_ADMIN_RECOVERY_ROLE`` is None.
- **test_admin_otp_reset_requires_auth**: Wrong password is rejected.
- **test_admin_otp_reset_delete_error**: IPA error during token
  deletion shows error message.
- **test_admin_otp_reset_create_error**: IPA error during recovery
  token creation shows error message.
- **test_admin_otp_reset_cache_control**: Admin reset response includes
  ``Cache-Control: no-store``.
- **test_admin_otp_reset_group_membership**: Admin with role membership
  via group (not direct user membership) can access OTP reset.

**Recovery code utility tests** (``tests/unit/utility/test_recovery_codes.py``,
8 tests):

- **test_generate_recovery_codes_count**: Verify correct number of
  codes are generated.
- **test_generate_recovery_codes_eight_digits**: Verify each code is
  exactly 8 digits.
- **test_generate_recovery_codes_match_hotp**: Verify codes match
  ``pyotp.HOTP`` output.
- **test_generate_recovery_codes_uses_sha256**: Verify SHA-256
  algorithm is used.
- **test_generate_recovery_codes_zero_count**: Zero count returns
  empty list.
- **test_generate_recovery_codes_negative_count**: Negative count
  returns empty list.
- **test_generate_recovery_codes_unique**: Verify all codes in a set
  are unique.
- **test_generate_recovery_codes_custom_count**: Custom count
  generates correct number of codes.

Integration tests
-----------------

Against a live FreeIPA instance:

- Enroll a TOTP token and generate recovery codes.
- Authenticate with ``password + recovery_code`` (using one of the 10
  codes).
- Verify the used code no longer works (counter advanced).
- Verify remaining codes still work.
- Regenerate codes and verify old codes no longer work.


Migration
=========

Existing users who already have OTP tokens will not have recovery codes.
On the OTP settings page, they will see *"Not set up"* with a button to
generate codes. No data migration is needed — the feature is purely
additive.


Additional Features
====================

The following features extend the core recovery code functionality.

Remaining code count
---------------------

Noggin queries ``ipatokenHOTPcounter`` via ``otptoken_show`` for the
user's recovery token and computes the remaining code count as
``OTP_RECOVERY_CODE_COUNT - counter``. The OTP settings page displays
this count alongside a colored status badge:

- **Active** (green): Codes available, count above the low threshold.
- **Low** (orange): Remaining count at or below
  ``OTP_RECOVERY_LOW_THRESHOLD`` (default: 3). The user is prompted
  to consider regenerating.
- **Exhausted** (red): All codes have been used. The user is urged to
  regenerate immediately.

When the counter cannot be retrieved (e.g. IPA error), the page falls
back to a generic "You have recovery codes set up" message.

Configuration::

    # Warn the user when this many or fewer recovery codes remain.
    OTP_RECOVERY_LOW_THRESHOLD = 3

Mandatory recovery codes on first OTP enrollment
--------------------------------------------------

When ``OTP_REQUIRE_RECOVERY_CODES`` is ``True``, confirming the first
OTP token automatically generates recovery codes and displays them in
the codes modal. The user must acknowledge saving the codes before
proceeding. This ensures every OTP user has recovery codes from the
moment they enable two-factor authentication.

When the flag is ``False`` (the default), a flash message with a link
to generate recovery codes is shown instead.

Configuration::

    # Auto-generate recovery codes when the user enrolls their first
    # OTP token.
    OTP_REQUIRE_RECOVERY_CODES = False

Admin-assisted OTP recovery
-----------------------------

Allows users with a designated IPA role to reset a locked-out user's
OTP tokens and generate recovery codes to share with them through a
verified out-of-band channel.

**How it works:**

1. The admin navigates to the locked-out user's profile page and
   clicks "Reset OTP".
2. A confirmation page shows the user's current OTP tokens and explains
   what the reset will do.
3. The admin enters their own password to confirm.
4. All of the target user's OTP tokens (TOTP and existing recovery) are
   deleted via ``ipa_admin``.
5. A new HOTP recovery token is created and recovery codes are
   generated.
6. The admin shares the codes with the user through a secure channel.
7. The user logs in with ``password + recovery_code`` and can then
   enroll a new TOTP token.

**Access control:**

The ``require_otp_admin`` decorator checks whether the current user is
a member of the IPA role named in ``OTP_ADMIN_RECOVERY_ROLE``. The
role membership is checked via ``ipa_admin.role_show()``. An admin
cannot use this route on their own account (they are redirected to the
normal OTP settings page).

**Routes:**

- ``GET /user/<username>/settings/otp/admin-reset`` — Confirmation
  page showing current tokens and the reset form.
- ``POST /user/<username>/settings/otp/admin-reset`` — Executes the
  reset and renders the recovery codes.

**Configuration:**

::

    # IPA role whose members may reset another user's OTP tokens.
    # Set to None (default) to disable the feature entirely.
    OTP_ADMIN_RECOVERY_ROLE = None

**Setting up the IPA role:**

.. code-block:: shell

    # Create the role (once)
    ipa role-add "OTP Recovery Admins" \
        --desc="Members can reset OTP tokens for locked-out users"

    # Grant the role to specific users
    ipa role-add-member "OTP Recovery Admins" --users=helpdesk_user

    # Configure Noggin
    # In noggin.cfg:
    OTP_ADMIN_RECOVERY_ROLE = "OTP Recovery Admins"

**Security considerations:**

- The admin must re-authenticate with their own password before
  performing a reset. This prevents CSRF and ensures the action is
  intentional.
- All token operations use the ``ipa_admin`` privileged client, not
  the admin's own IPA session, since the admin may not have direct
  LDAP permissions on the target user's tokens.
- The reset action is logged at INFO level:
  ``Admin <admin> reset OTP for user <username>``.
- Recovery codes are shown once and never stored by Noggin. The admin
  must share them immediately through a secure channel.
