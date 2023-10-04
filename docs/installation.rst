============
Installation
============


Installing and setting up IPA
=============================

Installing IPA
--------------
There is a `basic quick start guide`_ for setting up FreeIPA.
More comprehensive setup documentation is `available from Red Hat`_.

.. _basic quick start guide: https://www.freeipa.org/page/Quick_Start_Guide
.. _available from Red Hat: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/installing_identity_management/index

Install the IPA FAS plugin
--------------------------
If you're on Fedora, run::

    sudo dnf install freeipa-fas

Otherwise you can checkout the code from
https://github.com/fedora-infra/freeipa-fas/ and run ``install.sh``.

Setting up IPA
--------------
If you want to be able to manage registering users, you need to setup the
corresponding role and privilege in IPA.

First, create a privilege containing the permissions needed to manage stage users::

    ipa privilege-add "Stage User Managers" --desc "Manage registering users in Noggin"
    ipa privilege-add-permission "Stage User Managers" --permissions "System: Read Stage Users" --permissions "System: Modify Stage User" --permissions "System: Remove Stage User"

Then, create a role associated with this privilege::

    ipa role-add "Stage User Managers" --desc "Manage registering users in Noggin"
    ipa role-add-privilege "Stage User Managers" --privileges "Stage User Managers"

Finally, if your administrators group is called ``sysadmin``, give people in
the ``sysadmin`` group the role to manage registering users::

    ipa role-add-member "Stage User Managers" --groups sysadmin


Installing and setting up Noggin
================================

Install Noggin
--------------

If you're on Fedora, you can install the ``noggin`` package with::

    sudo dnf install noggin

Otherwise, you can install Noggin from PyPI with::

    pip install noggin noggin-messages

You can also download the tarball or clone the repository, and run::

    poetry install --without dev --extras deploy

You'll find ``poetry`` in your distribution's packages, on Fedora it's named
``poetry``. You will also need to install ``noggin-messages``, with ``pip`` or
with ``dnf``.

Configure Noggin
----------------
The tarball and the repository contain a file named ``deployment/noggin.cfg.example``.
Copy it in ``/etc/noggin/noggin.cfg``. The ``noggin`` package in Fedora already
installs this file.

Edit ``/etc/noggin/noggin.cfg`` to set up Noggin settings as appropriate. As we
set up a IPA system earlier, update the FREEIPA_* items to point to your
server.

Take a moment to review all the settings in the file and update them as needed.
Most settings in there should have comments documenting what they're for, or
are otherwise obvious for what needs to be set and why.

Install and configure a web server
----------------------------------
This document will use Nginx as the webserver, but any proxying webserver would
do.

First, install nginx::

    sudo dnf install nginx

Copy the file named ``deployment/nginx.conf`` in the tarball or the repo to
``/etc/nginx/conf.d``, and adjust as appropriate to your webserver setup (HTTPS
or not, certificates, domain(s), etc). If you are using the Fedora package,
this file is already installed.

Open ports in the firewall
--------------------------
On Fedora, this can be done with::

    sudo firewall-cmd --add-service=http
    sudo firewall-cmd --add-service=https
    sudo firewall-cmd --runtime-to-permanent

Setup the Noggin service
------------------------
The Fedora package already installs the service definition file. If you are not
on Fedora or are not using the RPM, you can use the files named
``deployment/noggin.service`` and ``deployment/noggin.sysconfig`` in the
tarball or the repo. Copy the ``.service`` file to
``/etc/systemd/system/noggin.service`` and the ``.sysconfig`` file to
``/etc/sysconfig/noggin``.

Adjust the ``ExecStart`` in ``/etc/systemd/system/noggin.service`` to account
for the environment where you installed Noggin.

- If you installed Noggin with ``pip`` as ``root``, ``gunicorn`` will be at
  ``/usr/local/bin/gunicorn``
- If you installed Noggin with ``pip`` as a normal user, ``gunicorn`` will be
  at ``/home/username/.local/bin/gunicorn``
- If you installed Noggin in a virtualenv, ``gunicorn`` will be at
  ``/path/to/virtualenv/bin/gunicorn``
- If you installed Noggin with Poetry, ``gunicorn`` will be at
  ``/home/username/.cache/pypoetry/virtualenvs/noggin-aaa-*/bin/gunicorn``

Enable and start Nginx and Noggin services::

    sudo systemctl enable --now noggin.service nginx.service

For more information, take a look at `the official Noggin documentation`_.

.. _the official Noggin documentation: https://noggin-aaa.readthedocs.io/
