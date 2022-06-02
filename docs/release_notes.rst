=============
Release notes
=============

.. towncrier release notes start

v1.6.1
======

Released on 2022-06-02.
This is a minor release.

Development Improvements
^^^^^^^^^^^^^^^^^^^^^^^^

* The tests have been moved outside of the installed package (:pr:`940`).

Dependency Changes
^^^^^^^^^^^^^^^^^^

* Update dependencies.


v1.6.0
======

Released on 2022-05-13. This is a feature release.

Features
^^^^^^^^

* Support Python 3.9 and 3.10 (:pr:`832`).
* Allow users to rename their 2FA token (:issue:`819`).

Bug Fixes
^^^^^^^^^

* Make the password change page less confusing (:issue:`798`).
* Lowercase email addresses upon registration (:issue:`834`).
* Issue a proper error message when the username is too short (:issue:`866`).
* Update the GECOS field when changing first name or last name (:issue:`913`).


v1.5.1
======

Released on 2021-12-15. This is a bugfix release.

Bug Fixes
^^^^^^^^^

* Let users login even if they registered with a username that is now invalid
  (:pr:`831`).


v1.5.0
======

Released on 2021-12-15.

Dependency Changes
^^^^^^^^^^^^^^^^^^

* Update to Flask 2.0, and update other dependencies (:pr:`828`).

Features
^^^^^^^^

* Allow the configuration of a regexp to validate usernames, and limit its
  length (:pr:`827`).

Development Improvements
^^^^^^^^^^^^^^^^^^^^^^^^

* Use Github Actions for CI (:pr:`828`).


v1.4.0
======

Released on 2021-11-10.
This is a feature and bugfix release.

Features
^^^^^^^^

* Improve the display of group communication channels (IRC or Matrix)
  (:issue:`309`).
* Add the email address in the user's profile (:issue:`568`).
* Display the SSH public keys on the user's profile (:issue:`676`).
* Mention that Fedora and CentOS accounts are merged (:issue:`689`).
* The Matrix server now defaults to fedora.im, and the Matrix web client
  instance defaults to https://chat.fedoraproject.org (:issue:`780`).

Bug Fixes
^^^^^^^^^

* Change the Lost OTP link and wording to limit spam email on our admin mailbox
  (:issue:`678`).
* Handle password changes for manually created users (:issue:`719`).

Contributors
^^^^^^^^^^^^

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Charles Lee
* Hela Basa
* Josep M. Ferrer


v1.3.0
======

Released on 2021-07-21.

Features
^^^^^^^^

* Add a page to manage registering users (:pr:`672`).
* Allow template override with a custom directory, see the
  ``TEMPLATES_CUSTOM_DIRECTORIES`` configration value (:pr:`701`).
* Allow users to declare their Matrix IDs in addition to the IRC nicknames
  (:issue:`248`).
* Display on users' profiles the agreements they have signed (:issue:`576`).
* Validate email addresses when changed in the ``mail`` or ``rhbz_mail``
  attributes (:issue:`610`).
* Allow users to select multiple pronouns (:issue:`646`).

Bug Fixes
^^^^^^^^^

* Don't tell users signing up that their username is already taken when it can
  be the email address (:pr:`665`).
* Add the ``for`` attribute to checkbox labels (:issue:`658`).

Development Improvements
^^^^^^^^^^^^^^^^^^^^^^^^

* Start using `pre-commit <https://pre-commit.com/>`_ to run the simple
  checkers (linters, formatters, security checks). Run ``poetry install`` to
  install the new dependencies, and then run ``pre-commit install`` to setup
  the git hook. Also add the `safety <https://pyup.io/safety/>`_ tool
  (:pr:`659`).

Contributors
^^^^^^^^^^^^

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Calvin Goodale


v1.2.0
======
Released on 2021-05-18.


Features
^^^^^^^^

* Display the version in the page footer (:issue:`592`).
* Allow sponsors to resign from their position in the group (:issue:`599`).
* Disallow login and register with mixed-case usernames (:issue:`594`).
* Add information in the validation email (:issue:`629`).

Bug Fixes
^^^^^^^^^

* Lowercase the username in Forgot Password Ask controller (:issue:`573`).
* Skipped autocomplete in OTP fields (:issue:`593`).

Contributors
^^^^^^^^^^^^

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Josseline Perdomo
* Yaron Shahrabani


v1.1.0
======

This is a feature release that adds a few interesting enhancements.


Features
^^^^^^^^

* Add a verification step when enrolling a new OTP token (:issue:`422`).
* The GPG key ID fields now refuse key IDs shorter than 16 characters, and
  allow up to 40 characters (the full fingerprint) (:issue:`556`).
* Paginate the group members list (:issue:`580`).
* Handle separately OTP from password in UI (:issue:`572`).

Bug Fixes
^^^^^^^^^

* Start messages with capital letter (:pr:`521`).
* Show more than 100 users on /group/<groupname> (:pr:`550`).
* Fixed mailto href adding mailto in the template of the group (:pr:`581`).
* Indirect groups are now included in the user's group list (:issue:`560`).
* Redirect back to the original page after login (:issue:`574`).
* Fix the OTP QR code being displayed by default (:issue:`577`).

Documentation Improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Add rstcheck to check our rst files (:commit:`1c2205f`).
* Update the release docs (:commit:`96b08ea`).
* Fix code-block format in contributing docs (:pr:`595`).

Contributors
^^^^^^^^^^^^

Many thanks to the contributors of bug reports, pull requests, and pull request
reviews for this release:

* Aurélien Bompard
* Chenxiong Qi
* Josseline Perdomo
* Rafael Fontenelle
* Ryan Lerch
* Vipul Siddhartha


v1.0.0
======

This is a the first stable release, as deployed in production in the Fedora infrastructure
on March 24th 2021.


Contributors
^^^^^^^^^^^^

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
