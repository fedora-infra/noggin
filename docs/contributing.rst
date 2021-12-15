============
Contributing
============

Thanks for considering contributing to noggin, we really appreciate it!

Quickstart:

1. Look for an `existing issue
   <https://github.com/fedora-infra/noggin/issues>`_ about the bug or
   feature you're interested in. If you can't find an existing issue, create a
   `new one <https://github.com/fedora-infra/noggin/issues/new>`_.

2. Fork the `repository on GitHub
   <https://github.com/fedora-infra/noggin>`_.

3. Fix the bug or add the feature, and then write one or more tests which show
   the bug is fixed or the feature works.

4. Submit a pull request and wait for a maintainer to review it.

More detailed guidelines to help ensure your submission goes smoothly are
below.

.. note:: If you do not wish to use GitHub, please send patches to
          infrastructure@lists.fedoraproject.org.

Development Environment
=======================
Vagrant allows contributors to get quickly up and running with a Noggin development environment by
automatically configuring a virtual machine. To get started, first install the Vagrant and Virtualization
packages needed, and start the libvirt service::

    $ sudo dnf install ansible libvirt vagrant-libvirt vagrant-sshfs vagrant-hostmanager
    $ sudo systemctl enable libvirtd
    $ sudo systemctl start libvirtd

Check out the code and run ``vagrant up``::

    $ git clone https://github.com/fedora-infra/noggin
    $ cd noggin
    $ vagrant up

Next, SSH into your newly provisioned development environment::

    $ vagrant ssh noggin

where you can run the following commands::

    $ noggin-restart
    $ noggin-stop
    $ noggin-logs
    $ noggin-start
    $ noggin-unit-tests

The noggin web application should be running automatically. To access it, go to http://ipa.noggin.test:5000/ in the browser on your
host machine to see the web application. http://ipa.noggin.test will give you access to the regular freeIPA
webUI.

Note that the ``/vagrant/`` folder contains the source of the git checkout on your host. Any changes
to the files in that directory on the host will be automatically synced to the VM.


Guidelines
==========

Python Support
--------------
Noggin supports Python 3.6 or greater. This is automatically enforced by the
continuous integration (CI) suite.


Code Style
----------
We follow the `PEP8 <https://www.python.org/dev/peps/pep-0008/>`_ style guide
for Python. This is automatically enforced by the CI suite.

We are using `Black <https://github.com/ambv/black>`_ to automatically format
the source code. It is also checked in CI. The Black webpage contains
instructions to configure your editor to run it on the files you edit.

Handle every possible case, and do so where it makes sense. Example: It's
important to handle issues from talking to the IPA server, but show flashes in
the Flask code, not the proxy/client code.


Security
--------
Remember to keep the code simple enough that it can be easily reviewed for
security concerns.

Code that touches security-critical paths must be signed off by **two** people.
People who sign off are agreeing to have reviewed the code thoroughly and
thought about edge cases.


Tests
-----
The test suites can be run using `tox <http://tox.readthedocs.io/>`_ by simply
running ``tox`` from the repository root. All code must have test coverage or
be explicitly marked as not covered using the ``# no-qa`` comment. This should
only be done if there is a good reason to not write tests.

Your pull request should contain tests for your new feature or bug fix. If
you're not certain how to write tests, we will be happy to help you.


Release Notes
-------------

To add entries to the release notes, create a file in the ``news`` directory in the
``source.type`` name format, where the ``source`` part of the filename is:

* ``42`` when the change is described in issue ``42``
* ``PR42`` when the change has been implemented in pull request ``42``, and
  there is no associated issue
* ``Cabcdef`` when the change has been implemented in changeset ``abcdef``, and
  there is no associated issue or pull request.

And where the extension ``type`` is one of:

* ``bic``: for backwards incompatible changes
* ``dependency``: for dependency changes
* ``feature``: for new features
* ``bug``: for bug fixes
* ``dev``: for development improvements
* ``docs``: for documentation improvements
* ``other``: for other changes

The content of the file will end up in the release notes. It should not end with a ``.``
(full stop).

If it is not present already, add a file in the ``news`` directory named ``username.author``
where ``username`` is the first part of your commit's email address, and containing the name
you want to be credited as. There is a script to generate a list of authors that we run
before releasing, but creating the file manually allows you to set a custom name.

A preview of the release notes can be generated with
``towncrier --draft``.


Licensing
---------

Your commit messages must include a Signed-off-by tag with your name and e-mail
address, indicating that you agree to the `Developer Certificate of Origin
<https://developercertificate.org/>`_ version 1.1::

	Developer Certificate of Origin
	Version 1.1

	Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
	1 Letterman Drive
	Suite D4700
	San Francisco, CA, 94129

	Everyone is permitted to copy and distribute verbatim copies of this
	license document, but changing it is not allowed.


	Developer's Certificate of Origin 1.1

	By making a contribution to this project, I certify that:

	(a) The contribution was created in whole or in part by me and I
	    have the right to submit it under the open source license
	    indicated in the file; or

	(b) The contribution is based upon previous work that, to the best
	    of my knowledge, is covered under an appropriate open source
	    license and I have the right under that license to submit that
	    work with modifications, whether created in whole or in part
	    by me, under the same open source license (unless I am
	    permitted to submit under a different license), as indicated
	    in the file; or

	(c) The contribution was provided directly to me by some other
	    person who certified (a), (b) or (c) and I have not modified
	    it.

	(d) I understand and agree that this project and the contribution
	    are public and that a record of the contribution (including all
	    personal information I submit with it, including my sign-off) is
	    maintained indefinitely and may be redistributed consistent with
	    this project or the open source license(s) involved.

Use ``git commit -s`` to add the Signed-off-by tag.


Releasing
---------

When cutting a new release, follow these steps:

#. Update the version in ``pyproject.toml``
#. Add missing authors to the release notes fragments by changing to the ``news`` directory and
   running the ``get-authors.py`` script, but check for duplicates and errors
#. Generate the release notes by running ``poetry run towncrier`` (in the base directory)
#. Adjust the release notes in ``docs/release_notes.rst``.
#. Generate the docs with ``tox -r -e docs`` and check them in ``docs/_build/html``.
#. Commit the changes
#. Push the commit to the upstream Github repository (via a PR or not).
#. Change to the stable branch and cherry-pick the commit (or merge if appropriate)
#. Run the checks one last time to be sure: ``tox -r``,
#. Tag the commit with ``-s`` to generate a signed tag
#. Push the commit to the upstream Github repository with ``git push``,
   and the new tag with ``git push --tags``
#. Generate a tarball and push to PyPI with the command ``poetry publish --build``
#. Create `the release on GitHub <https://github.com/fedora-infra/noggin/tags>`_ and copy the
   release notes in there,
#. Deploy and announce.


Translations
------------

To extract the messages.pot that is in noggin/translations/messages.pot, use::

  poetry run pybabel extract -F babel.cfg -o noggin/translations/messages.pot noggin

This will update the messages.pot with the newest strings that have been flagged in the
templates and code.

To add a new language, use the command::

  poetry run pybabel init -i noggin/translations/messages.pot -d noggin/translations/ -l fr_FR

To update all created languages with the newest strings in messages.pot, use::

  poetry run pybabel update -i noggin/translations/messages.pot -d noggin/translations

To compile the translations in updated .mo files into what noggin can use, use the command::

  poetry run pybabel compile -d noggin/translations


UI and themes
-------------

Noggin has support for themes, have a look at the existing themes for inspiration.

Some notes regarding our Content Security Policy:

- inline ``<script>`` tags must have a ``nonce`` attribute, look at the other templates for the proper Jinja snippet.
- CSS files can't use the ``data:`` scheme for images. Bootstrap makes use of that, for example.
  You can convert a CSS file that uses the ``data:`` scheme for SVGs with the ``data-uri-to-svg.py`` script, it will
  extract the files and replace the ``url()`` instructions. You can then just use the new file it created in the
  HTML template.
