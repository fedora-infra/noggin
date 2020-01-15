#!/usr/bin/env python3

import python_freeipa
from python_freeipa import Client
import random
from faker import Faker
fake = Faker()

ipa_server = "ipa.example.com"
ipa_user = "admin"
ipa_pw = "adminPassw0rd!"
instances = []
ipa = Client(host=ipa_server)
ipa.login(ipa_user, ipa_pw)
users = []

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
            home_directory='/home/fedora/%s' % username,
            disabled=False,
            random_pass=True,
            fasircnick=username,
            faslocale=None,
            fastimezone=None,
            fasgpgkeyid=[None],
        )
        users.append(username)
        for i in range(0,len(users)):
            if i % 3 == 0 and i!= 0:
                ipa.group_add_member("developers", users[i], skip_errors=True)
            if i % 2 == 0 and i!= 0:
                ipa.group_add_member("admins", users[i], skip_errors=True)
    except python_freeipa.exceptions.FreeIPAError as e:
        print(e)
