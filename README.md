# securitas

From Latin. n. "security".

*securitas* is a self-service portal for FreeIPA.
The primary purpose of the portal is to allow users to sign up and manage their
account information and group membership.

Immediate goals of *securitas* are:

* Allow users to register (i.e., create FreeIPA accounts)
* Allow users to see select information about other users
* Allow users to update and manage their information (name, password, etc.)
* Allow group administrators to add/remove members from groups for which they
  are responsible.

## Setup tips

* Use relrod's [containerdev](https://github.com/relrod/containerdev) project for development.
* Copy your IPA server's `/etc/ipa/ca.crt` to `.containerdev-public/ipa01`
* Copy `securitas.cfg.default` to `securitas.cfg` and edit it accordingly. It's in .gitignore, so you are safe to put whatever in it.
* Have `podman` installed
* Run `containerdev-build && containerdev`
* From inside the container shell, run `flask run -h0`
* In your local browser go to localhost:5000
