#!/usr/bin/env python3
import textwrap

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


# create a developers fasgroup
try:
    ipa.group_add("developers", "A group for developers", fasgroup=True, non_posix=True)
except python_freeipa.exceptions.FreeIPAError as e:
    print(e)

# create a designers fasgroup
try:
    ipa.group_add("designers", "A group for designers", fasgroup=True, non_posix=True)
except python_freeipa.exceptions.FreeIPAError as e:
    print(e)

# add 2 user agreements
agreement1 = '\n\n'.join(
    textwrap.fill(fake.paragraph(nb_sentences=20)) for _ in range(10)
)
ipa.fasagreement_add("FPCA", description=agreement1)
agreement2 = '\n\n'.join(
    textwrap.fill(fake.paragraph(nb_sentences=5)) for _ in range(15)
)
ipa.fasagreement_add("CentOS Agreement", description=agreement2)

# add developers and designers groups to the FPCA agreement
ipa.fasagreement_add_group("FPCA", group="developers")
ipa.fasagreement_add_group("FPCA", group="designers")

# add designers groups to the CentOS agreement
ipa.fasagreement_add_group("CentOS Agreement", group="designers")

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
            # User must have signed FPCA before being added to developers
            ipa.fasagreement_add_user("FPCA", user=username)
            ipa.group_add_member("developers", username, skip_errors=True)
            if x < 10:
                ipa.group_add_member_manager(
                    "developers", users=username, skip_errors=True
                )
        if x % 5 == 0:
            # User must have signed FPCA and CentOS before being added to designers
            ipa.fasagreement_add_user("FPCA", user=username)
            ipa.fasagreement_add_user("CentOS Agreement", user=username)

            ipa.group_add_member("designers", username, skip_errors=True)
            if x <= 15:
                ipa.group_add_member_manager(
                    "designers", users=username, skip_errors=True
                )
        if x % 2 == 0:
            ipa.group_add_member("admins", username, skip_errors=True)
    except python_freeipa.exceptions.FreeIPAError as e:
        print(e)
