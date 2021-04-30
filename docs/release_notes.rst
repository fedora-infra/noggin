=============
Release notes
=============

.. towncrier release notes start

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

* Add rstcheck to check our rst files (:issue:`1c2205f`).
* Update the release docs (:issue:`96b08ea`).
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
