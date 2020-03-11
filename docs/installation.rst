============
Installation
============

This covers installation in a development context.

.. note:: **TODO**: Cover end-user installation here.


* Use relrod's `containerdev`_ project for development. (Or don't, but at least follow the steps in the Dockerfile to set up your own environment.)
* Copy your IPA server's ``/etc/ipa/ca.crt`` to ``.containerdev-public/ipa01``
* Copy ``noggin.cfg.default`` to ``noggin.cfg`` and edit it accordingly. It's in .gitignore, so you are safe to put whatever in it.

  * The ``FREEIPA_ADMIN_USER``/``FREEIPA_ADMIN_PASSWORD`` combination doesn't need to be a full admin user. It just needs to be a user in a role with a privilege that has the following permissions:

    * System: Add User to default group
    * System: Add Users
    * System: Change User password
    * System: Read UPG Definition

* Have ``podman`` installed
* Run ``containerdev-build && containerdev``
* From inside the container shell, run ``flask run -h0``
* In your local browser go to http://localhost:5000

.. _containerdev: https://github.com/relrod/containerdev
