========================
Securitas' documentation
========================

*securitas* is a self-service portal for FreeIPA.
The primary purpose of the portal is to allow users to sign up and manage their
account information and group membership.

Immediate goals of *securitas* are:

* Allow users to register (i.e., create FreeIPA accounts)
* Allow users to see select information about other users
* Allow users to update and manage their information (name, password, etc.)
* Allow group administrators to add/remove members from groups for which they
  are responsible.

Here is what works so far:

* Logging in
* Registering new accounts
* Resetting current, known (possibly expired) passwords (but not forgotten ones)
* Decent error handling for all of the above
* User pages (seeing information about a user, groups they are in, etc.)
* Group pages (seeing who all is in a group)
* Allowing group member managers to sponsor people into groups
* Allowing group member managers to remove people from groups
* Editing user profile information

.. image:: https://images.elrod.me/securitas-screenshot.png?2
    :alt: screenshot


.. User Guide

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   release_notes

.. API

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   api


.. Contributors

.. toctree::
   :maxdepth: 2
   :caption: Contributor Guide

   contributing
