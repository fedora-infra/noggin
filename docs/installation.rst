============
Installation
============

.. note:: **TODO**: Cover end-user installation here.


IPA settings
============

If you want to be able to manage registering users, you need to setup the corresponding role and privilege in IPA.

First, create a privilege containing the permissions needed to manage stage users::

    ipa privilege-add "Stage User Managers" --desc "Manage registering users in Noggin"
    ipa privilege-add-permission "Stage User Managers" --permissions "System: Read Stage Users" --permissions "System: Modify Stage User" --permissions "System: Remove Stage User"

Then, create a role associated with this privilege::

    ipa role-add "Stage User Managers" --desc "Manage registering users in Noggin"
    ipa role-add-privilege "Stage User Managers" --privileges "Stage User Managers"

Finally, if your administrators group is called ``sysadmin``, give people in the ``sysadmin`` group the role to manage registering users::

    ipa role-add-member "Stage User Managers" --groups sysadmin
