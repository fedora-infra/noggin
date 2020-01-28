#!/usr/bin/env python3

import python_freeipa
from python_freeipa.client_legacy import ClientLegacy
from faker import Faker

fake = Faker()


ipa_server = "ipa.example.com"
ipa_user = "admin"
ipa_pw = "adminPassw0rd!"
ipa = ClientLegacy(host=ipa_server, verify_ssl=False)
ipa.login(ipa_user, ipa_pw)

# create a developers group
try:
    ipa.group_add("developers", "A group for developers")
except python_freeipa.exceptions.FreeIPAError as e:
    print(e)

# create some random users and add them to both the developers and admin groups randomly
for x in range(50):
    firstName = fake.first_name()
    lastName = fake.last_name()
    username = firstName + str(x)
    try:
        ipa.user_add(
            username,
            firstName,
            lastName,
            firstName + " " + lastName,
            home_directory=f"/home/fedora/{username}",
            disabled=False,
            user_password='testuserpw',
            fasircnick=username,
            faslocale=None,
            fastimezone=None,
            fasgpgkeyid=[],
        )
        if x % 3 == 0:
            ipa.group_add_member("developers", username, skip_errors=True)
        if x % 2 == 0:
            ipa.group_add_member("admins", username, skip_errors=True)
    except python_freeipa.exceptions.FreeIPAError as e:
        print(e)

# add a known user for testing purposes
try:
    ipa.user_add(
        "testuser",
        "Test",
        "User",
        "Test User",
        home_directory=f"/home/fedora/testUser",
        disabled=False,
        random_pass=True,
        fasircnick="testuser",
        faslocale=None,
        fastimezone=None,
        fasgpgkeyid=[],
    )
except python_freeipa.exceptions.FreeIPAError as e:
    print(e)