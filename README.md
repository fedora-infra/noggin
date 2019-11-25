# securitas

[![Build Status](https://travis-ci.org/relrod/securitas.svg?branch=master)](https://travis-ci.org/relrod/securitas)

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
  
Here is what works so far:

* User pages (seeing information about a user, groups they are in, etc.)
* Group pages (seeing who all is in a group)
* Logging in
* Registering new accounts
* Resetting current, known (possibly expired) passwords (but not forgotten ones)
* Decent error handling for all of the above

<img src="https://images.elrod.me/securitas-screenshot.png">

## Setup tips

* Use relrod's [containerdev](https://github.com/relrod/containerdev) project for development. (Or don't, but at least follow the steps in the Dockerfile to set up your own environment.)
* Copy your IPA server's `/etc/ipa/ca.crt` to `.containerdev-public/ipa01`
* Copy `securitas.cfg.default` to `securitas.cfg` and edit it accordingly. It's in .gitignore, so you are safe to put whatever in it.
  * The `FREEIPA_ADMIN_USER`/`FREEIPA_ADMIN_PASSWORD` combination doesn't need to be a full admin user. It just needs to be a user in a role with a privilege that has the following permissions:
    * System: Add User to default group
    * System: Add Users
    * System: Change User password
    * System: Read UPG Definition
* Have `podman` installed
* Run `containerdev-build && containerdev`
* From inside the container shell, run `flask run -h0`
* In your local browser go to localhost:5000


## Contribution guidelines

* Simplicity above all. Keep the code simple enough that it can be easily reviewed for security concerns.
* Prettiness above pep-8/similar. I'm not too interested in patches that only change code style.
  Most of the code was written in the style it was for a reason. Contributions which don't follow
  the style of neighboring code won't be accepted until they do.
* Handle every possible case, and do so where it makes sense. Example: It's important to handle issues from
  talking to the IPA server, but show flashes in the Flask code, not the proxy/client code.
* Once this project becomes "real", code that touches security-critical paths must be signed off by TWO people.
  People who sign off are agreeing to have reviewed the code thoroughly and thought about edge cases.
