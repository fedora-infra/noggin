## Noggin

*noggin* is a self-service portal for FreeIPA.
The primary purpose of the portal is to allow users to sign up and manage their
account information and group membership.

*noggin* has the following UI Features:

- Ability to Log In to Noggin
- Register / Create a new Account
- Resetting current, known (possibly expired) passwords
- Resetting forgotten passwords
- User pages (seeing information about a user, groups they are in, etc.)
- Group pages (seeing who all is in a group)
- Allowing group member managers to sponsor people into groups
- Allowing group member managers to remove people from groups
- Editing user profile information

### Migrating your application:

If your application currently uses communicates with the Fedora Account System (FAS2) using it’s readonly API, this functionality will be provided by [fasjson](https://github.com/fedora-infra/fasjson/). Additionally, [fasjson-client](https://github.com/fedora-infra/fasjson-client/) provides a python client library for the fasjson api.

Refer to the [fasjson documentation](https://fasjson.readthedocs.io/) for information on migrating applications to the new API.

### Contributor Guide

Thanks for considering contributing to noggin, we really appreciate it!

Quickstart:

1.  Look for an  [existing issue](https://github.com/fedora-infra/noggin/issues)  about the bug or feature you’re interested in. If you can’t find an existing issue, create a  [new one](https://github.com/fedora-infra/noggin/issues/new).
2.  Fork the  [repository on GitHub](https://github.com/fedora-infra/noggin).
3.  Fix the bug or add the feature, and then write one or more tests which show the bug is fixed or the feature works.
4.  Submit a pull request and wait for a maintainer to review it.
Additional Information for contributers can be found in the [official docs](https://noggin-aaa.readthedocs.io/en/latest/contributing.html).

### Documentation

The documentation is available online at https://noggin-aaa.readthedocs.io/
