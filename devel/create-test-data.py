#!/usr/bin/env python3

import python_freeipa
from faker import Faker

from noggin.security.ipa import Client
import noggin.utility.timezones as timezones

USER_PASSWORD = "testuserpw"

fake = Faker()
fake.seed_instance(0)

ipa_server = "ipa.example.com"
ipa_user = "admin"
ipa_pw = "adminPassw0rd!"
ipa = Client(host=ipa_server, verify_ssl=False)
ipa.login(ipa_user, ipa_pw)

untouched_ipa = Client(host=ipa_server, verify_ssl=False)

# create a developers group
try:
    ipa.group_add("developers", "A group for developers", fasgroup=True, non_posix=True)
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
            user_password=USER_PASSWORD,
            fasircnick=[username, username + "_"],
            faslocale="en-US",
            fastimezone=fake.random_sample(timezones.TIMEZONES, length=1)[0],
            fasgpgkeyid=[],
        )
        # 'change' the password as the user, so its not expired
        untouched_ipa.change_password(
            username, new_password=USER_PASSWORD, old_password=USER_PASSWORD
        )
        if x % 3 == 0:
            ipa.group_add_member("developers", username, skip_errors=True)
            if x < 10:
                ipa.group_add_member_manager(
                    "developers", users=username, skip_errors=True
                )
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
