========================
Noggin's documentation
========================

*noggin* is a self-service portal for FreeIPA. Noggin also requires the use of
the `freeipa-fas <https://github.com/fedora-infra/freeipa-fas/>`_ extensions for
FreeIPA to provide additional fields and functionality.

The primary purpose of the portal is to allow users to sign up and manage their
account information and group membership.


Noggin has the following UI Features:

* Ability to Log In to Noggin
* Register / Create a new Account
* Resetting current, known (possibly expired) passwords
* Resetting forgotten passwords
* User pages (seeing information about a user, groups they are in, etc.)
* Group pages (seeing who all is in a group)
* Allowing group member managers to sponsor people into groups
* Allowing group member managers to remove people from groups
* Editing user profile information

Migrating your application:

If your application currently uses communicates with the Fedora Account System (FAS2)
using it's readonly API, this functionality will be provided by `fasjson <https://github.com/fedora-infra/fasjson/>`_.
Additionally, `fasjson-client <https://github.com/fedora-infra/fasjson-client/>`_ provides a python client library for
the fasjson api.

Refer to the `fasjson documentation <https://fasjson.readthedocs.io/>`_
for information on migrating applications to the new API.


.. image:: https://github.com/fedora-infra/noggin/actions/workflows/tests.yml/badge.svg?branch=dev
    :target: https://github.com/fedora-infra/noggin/actions/workflows/tests.yml?query=branch%3Adev

.. image:: https://img.shields.io/pypi/v/noggin-aaa.svg
    :target: https://pypi.org/project/noggin-aaa/

.. image:: https://img.shields.io/pypi/pyversions/noggin-aaa.svg
    :target: https://pypi.org/project/noggin-aaa/

.. image:: https://readthedocs.org/projects/noggin-aaa/badge/?version=latest
    :alt: Documentation Status
    :target: https://noggin-aaa.readthedocs.io/en/latest/?badge=latest


.. User Guide

.. toctree::
   :maxdepth: 1
   :caption: User Guide

   userguide


.. Sysadmin's Guide

.. toctree::
   :maxdepth: 2
   :caption: Sysadmin's Guide

   installation


.. Contributor's Guide

.. toctree::
   :maxdepth: 2
   :caption: Contributor's Guide

   contributing


.. Release Notes

.. toctree::
   :maxdepth: 2
   :caption: Release Notes

   release_notes


.. toctree::
   :maxdepth: 2
   :caption: Module Documentation

   _source/modules
