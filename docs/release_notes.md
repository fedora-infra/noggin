# Release notes

<!-- towncrier release notes start -->

## v1.10.0

Released on 2024-04-15.

### Features

- Show the Discussion URL in the group infomation page (#867)
- Use DNS to list the IPA servers (#1357)

### Bug Fixes

- Previously, the Leave Group button on the group page was at the top of the list of group members. 
  However if a group has a large number of sponsors, this button would be far down the page.
  The leave group button is now located in the subheader of the group listing page, avoiding this issue. (#600)
- Only choose an IPA server that is in the config (#1356)
- Revisited and rewrote the installation steps in greater detail (#1363)
- Alerts / Flash Messages of type Success now timeout and disappear after 5 seconds (#1379)

### Other Changes

- The Fedora, Default, and CentOS themes now use Bootstrap 5 or Fedora Bootstrap 2 (#966)
- Remove OpenSUSE theme assets as they are not used anymore (#1391)

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request reviews for this release:

- Akashdeep Dhar
- Aurélien Bompard
- Cappy Ishihara
- Elias
- Nils Philippsen
- Patrik Polakovič
- Ryan Lerch
- William Modave

## v1.9.0

Released on 2024-01-10.

### Features

- Add validation for the OTP field on the login page (#1152)
- Add the RSS URL to the user profile (#1216)
- Give a clearer error message to registering users who use a mixed case username (#1327)

### Bug Fixes

- Fix the boolean values (checkboxes) not showing up in the profile page (#1202)
- Don't show disabled (locked) users in Noggin (#1210)

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

- Andika Triwidada
- Ettore Atalan
- Aurélien Bompard
- Luna Jernberg
- Borys Dikovets
- Jan Kuparinen
- Frank Dana
- Hoppár Zoltán
- josep constantí
- Linus Virtanen
- Maksim Kliazovich
- 김인수
- Tao Mon Lae
- Yuri Chornoivan

## v1.8.0

Released on 2023-09-21.
This is a feature release that adds a RSS URL to the user profile.

### Features

* Add the RSS URL to the user profile (#1216).

### Bug Fixes

* Fix the boolean values (checkboxes) not showing up in the profile page
  (#1202).
* Don't show disabled (locked) users in Noggin (#1210).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Jonathan Wright
* Aurélien Bompard
* grimst
* Lenka Segura
* Nils Philippsen
* Pedro Moura
* Ryan Lerch


## v1.7.1

Released on 2023-01-17.
This is a bugfix release.

### Features

* Add compatibility with Flask 2.2.X by using ``register_error_handler``
  instead of a plain WSGI wrapper. (PR #1008).

### Bug Fixes

* ``/forgot-password/ask`` endpoint now handles ``smtplib.SMTPRecipientsRefused``
  error gracefully. (#817).
* Store the chosen IPA server in the session for both the user client and the
  admin client. This prevents admin commands from running on a server and user
  commands running on another. (#1079).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Ettore Atalan
* Aurélien Bompard
* Francois Andrieu
* Erol Keskin
* Ernedin Zajko
* Hoppár Zoltán
* Nathan
* Robert Klein


## v1.7.0

Released on 2022-07-04. This is a feature release.

### Backwards Incompatible Changes

* Noggin no longer assumes it is being deployed in Fedora infrastructure by
  default (PR #949). This is technically a backwards incompatible change
  but the only deployment where it could break things is the Fedora install
  and it has been taken care of.

### Dependency Changes

* Update dependency versions.

### Features

* Add a blocklist for registering users (#957).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Akashdeep Dhar
* Aurélien Bompard
* Neal Gompa
* Oğuz Ersen


## v1.6.1

Released on 2022-06-02.
This is a minor release.

### Development Improvements

* The tests have been moved outside of the installed package (PR #940).

### Dependency Changes

* Update dependencies.


## v1.6.0

Released on 2022-05-13. This is a feature release.

### Features

* Support Python 3.9 and 3.10 (PR #832).
* Allow users to rename their 2FA token (#819).

### Bug Fixes

* Make the password change page less confusing (#798).
* Lowercase email addresses upon registration (#834).
* Issue a proper error message when the username is too short (#866).
* Update the GECOS field when changing first name or last name (#913).


## v1.5.1

Released on 2021-12-15. This is a bugfix release.

### Bug Fixes

* Let users login even if they registered with a username that is now invalid
  (PR #831).


## v1.5.0

Released on 2021-12-15.

### Dependency Changes

* Update to Flask 2.0, and update other dependencies (PR #828).

### Features

* Allow the configuration of a regexp to validate usernames, and limit its
  length (PR #827).

### Development Improvements

* Use Github Actions for CI (PR #828).


## v1.4.0

Released on 2021-11-10.
This is a feature and bugfix release.

### Features

* Improve the display of group communication channels (IRC or Matrix)
  (#309).
* Add the email address in the user's profile (#568).
* Display the SSH public keys on the user's profile (#676).
* Mention that Fedora and CentOS accounts are merged (#689).
* The Matrix server now defaults to fedora.im, and the Matrix web client
  instance defaults to https://chat.fedoraproject.org (#780).

### Bug Fixes

* Change the Lost OTP link and wording to limit spam email on our admin mailbox
  (#678).
* Handle password changes for manually created users (#719).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Charles Lee
* Hela Basa
* Josep M. Ferrer


## v1.3.0

Released on 2021-07-21.

### Features

* Add a page to manage registering users (PR #672).
* Allow template override with a custom directory, see the
  ``TEMPLATES_CUSTOM_DIRECTORIES`` configration value (PR #701).
* Allow users to declare their Matrix IDs in addition to the IRC nicknames
  (#248).
* Display on users' profiles the agreements they have signed (#576).
* Validate email addresses when changed in the ``mail`` or ``rhbz_mail``
  attributes (#610).
* Allow users to select multiple pronouns (#646).

### Bug Fixes

* Don't tell users signing up that their username is already taken when it can
  be the email address (PR #665).
* Add the ``for`` attribute to checkbox labels (#658).

### Development Improvements

* Start using `pre-commit <https://pre-commit.com/>`_ to run the simple
  checkers (linters, formatters, security checks). Run ``poetry install`` to
  install the new dependencies, and then run ``pre-commit install`` to setup
  the git hook. Also add the `safety <https://pyup.io/safety/>`_ tool
  (PR #659).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Calvin Goodale


## v1.2.0
Released on 2021-05-18.


### Features

* Display the version in the page footer (#592).
* Allow sponsors to resign from their position in the group (#599).
* Disallow login and register with mixed-case usernames (#594).
* Add information in the validation email (#629).

### Bug Fixes

* Lowercase the username in Forgot Password Ask controller (#573).
* Skipped autocomplete in OTP fields (#593).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Josseline Perdomo
* Yaron Shahrabani


## v1.1.0

This is a feature release that adds a few interesting enhancements.


### Features

* Add a verification step when enrolling a new OTP token (#422).
* The GPG key ID fields now refuse key IDs shorter than 16 characters, and
  allow up to 40 characters (the full fingerprint) (#556).
* Paginate the group members list (#580).
* Handle separately OTP from password in UI (#572).

### Bug Fixes

* Start messages with capital letter (PR #521).
* Show more than 100 users on /group/<groupname> (PR #550).
* Fixed mailto href adding mailto in the template of the group (PR #581).
* Indirect groups are now included in the user's group list (#560).
* Redirect back to the original page after login (#574).
* Fix the OTP QR code being displayed by default (#577).

### Documentation Improvements

* Add rstcheck to check our rst files ([1c2205f](https://github.com/fedora-infra/noggin/commit/1c2205f)).
* Update the release docs ([96b08ea](https://github.com/fedora-infra/noggin/commit/96b08ea)).
* Fix code-block format in contributing docs (PR #595).

### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Chenxiong Qi
* Josseline Perdomo
* Rafael Fontenelle
* Ryan Lerch
* Vipul Siddhartha


## v1.0.0

This is a the first stable release, as deployed in production in the Fedora infrastructure
on March 24th 2021.


### Contributors

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Alain Reguera Delgado
* Aurélien Bompard
* Jan Kuparinen
* james02135
* Jean-Baptiste Holcroft
* Neal Gompa
* Nils Philippsen
* Rafael Fontenelle
* Ricky Tigg
* Ryan Lerch
* simmon
* Stephen Coady
