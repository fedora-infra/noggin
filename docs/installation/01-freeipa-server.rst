=============================
Setting up the FreeIPA server
=============================

Preparation
===========

In order to run a FreeIPA server in a virtual machine, we need to set up the
following four files in the same directory.

.. code-block:: yaml

    .
    ├── Fedora-Cloud-Base-XX-A.B.x86_64.raw
    ├── head.cfg
    ├── head.sh
    └── head.yml

    1 directory, 4 files


Sourcing Image
--------------

Download the most recent release of
`Fedora Linux Cloud Edition <https://fedoraproject.org/cloud/download/>`_
in the RAW extension.


Network Configuration
---------------------

After replacing the variables mentioned below, the ``head.cfg`` file should
look like the following.

- IPv4 gateway - ``<GATEWAY_IPV4>``
- IPv4 address - ``<ADDRESS_IPV4_WITH_SUBNET>``
- IPv4 DNS servers - ``<DNSLIST_IPV4>``
- DHCP on IPv4 - ``Disabled``
- DHCP on IPv6 - ``Disabled``

.. code-block:: yaml

    #cloud-config

    network:
      version: 2
      renderer: "NetworkManager"
      ethernets:
        eth0:
          dhcp4: false
          dhcp6: false
          gateway4: "<GATEWAY_IPV4>"
          addresses:
            - "<ADDRESS_IPV4_WITH_SUBNET>"
          nameservers:
            addresses:
              - "<DNSLIST_IPV4>"


Machine Configuration
---------------------

After replacing the variables mentioned below, the ``head.yml`` file should
look like the following.

- Hostname - ``<HOSTNAME>``
- FQDN - ``<FQDN>``
- Name for administrator user - ``root``
- GECOS for administrator user - ``<ROOTMETA>``
- Password for administrator user - ``<ROOTPASS>``
- Disable administrator user account? - ``False``
- Name for default user - ``<USERNAME>``
- GECOS for default user - ``<USERMETA>``
- Password for default user - ``<USERPASS>``
- Disable default user account? - ``False``
- Sudo mode for default user - ``ALL=(ALL) NOPASSWD:ALL``
- Public SSH key for default user - ``<PUBLIC_SSHKEY>``
- Groups for default user - ``wheel``

.. code-block:: yaml

    #cloud-config

    preserve_hostname: false
    hostname: "<HOSTNAME>"
    fqdn: "<FQDN>"

    system_info:
      default_user:
        name: "root"
        gecos: "<ROOTMETA>"
        plain_text_passwd: "<ROOTPASS>"
        lock_passwd: false

    final_message: |
      Operating system has been initialized
      Version: $version
      Timestamp: $timestamp
      Datasource: $datasource
      Uptime: $uptime

    users:
      - name: "<USERNAME>"
        gecos: "<USERMETA>"
        plain_text_passwd: "<USERPASS>"
        lock_passwd: false
        sudo: "ALL=(ALL) NOPASSWD:ALL"
        ssh_authorized_keys:
          - "<PUBLIC_SSHKEY>"
        groups:
          - "wheel"

    growpart:
      mode: auto
      devices:
        - "/"
      ignore_growroot_disabled: false


Configuration Script
--------------------

After replacing the variables mentioned below, the ``head.sh`` file should
look like the following.

- Specific hostname - ``nogginvirt``
- Environment name - ``head``
- Memory size (in MB, should be minimum 2048) - ``4096``
- CPU count (should be minimum 2) - ``4``
- Network configuration file location - ``<PATH_TO_HEAD_CFG>``
- Machine configuration file location - ``<PATH_TO_HEAD_YML>``
- Disk size (in GB, should be minimum 16) - ``24G``
- Cloud image file location (in RAW) - ``<CLOUD_INPUT_IMAGE>``
- Output image file location (in RAW) - ``<CLOUD_OUTPUT_IMAGE>``
- Network interface binding name - ``<BINDNAME>``
- VNC port number - ``<DESKPORT>``
- Operating system variant - ``fedora-unknown``

.. code-block:: shell

    #!/bin/sh

    SPECNAME="nogginvirt"
    EVMTNAME="head"
    MEMCOUNT="4096"
    CPUCOUNT="4"
    NTWKFILE="<PATH_TO_HEAD_CFG>"
    CINTFILE="<PATH_TO_HEAD_YML>"
    DISKSIZE="24G"
    SRCEIMEJ="<CLOUD_INPUT_IMAGE>"
    DESTIMEJ="<CLOUD_OUTPUT_IMAGE>"
    NTWKNAME="<BINDNAME>"
    VNCPORTN="<DESKPORT>"

    GRINCOLR="\033[42m"
    RESETCOL="\033[0m"

    sudo qemu-img info $DESTIMEJ

    sudo qemu-img resize $DESTIMEJ -f raw $DISKSIZE

    sudo qemu-img info $DESTIMEJ

    sudo \
      virt-install \
        --virt-type kvm \
        --os-variant fedora-unknown \
        --arch x86_64 \
        --name $SPECNAME-$EVMTNAME \
        --memory $MEMCOUNT \
        --cpu host-passthrough \
        --vcpus $CPUCOUNT \
        --disk $DESTIMEJ,device=disk,bus=virtio,format=raw,sparse=false \
        --graphics vnc,listen=0.0.0.0,port=$VNCPORTN \
        --network model=virtio,bridge=$BRDGNAME \
        --cloud-init user-data=$INITFILE,network-config=$NTWKFILE \
        --import \
        --noautoconsole


Installation
============

Setting up the virtual machine
------------------------------

1. Ensure that the most recent release of Fedora Linux Cloud Edition is kept
   in a certain directory

2. Ensure that the variables are suitably replaced in the configuration files
   kept in the same directory.

3. Execute the configuration script start setting up the virtual machine.

   .. code-block:: shell

        sh head.sh

   .. code-block:: shell

        image: head.img
        file format: raw
        virtual size: 2 GiB (2147483648 bytes)
        disk size: 622 MiB
        Child node '/file':
            filename: head.img
            protocol type: file
            file length: 2 GiB (2147483648 bytes)
            disk size: 622 MiB

        image: head.img
        file format: raw
        virtual size: 24 GiB (25769803776 bytes)
        disk size: 622 MiB
        Child node '/file':
            filename: head.img
            protocol type: file
            file length: 24 GiB (25769803776 bytes)
            disk size: 622 MiB

        Starting install...
        Creating domain...
        Domain creation completed.

4. Monitor the instantiation of the cloud installation using the following
   command.

   .. code-block:: shell

        virsh console nogginvirt-head

5. Connect to the instantiated cloud installation using the following command.

   .. code-block:: shell

        ssh -i <PATH_TO_SSHKEY> <USERNAME>@<ADDRESS_IPV4>


Setting up a FreeIPA installation
---------------------------------

1. Edit the hosts file of the cloud installation to reflect the following.

   .. code-block:: shell

        <ADDRESS_IPV4>      <FQDN>                               <HOSTNAME>

   For example

   .. code-block:: shell

        192.168.0.131      nogginvirt-head.apexaltruism.net      nogginvirt-head

2. Open ports in the firewall to allow for ports used by the FreeIPA server.

   .. code-block:: shell

        sudo firewall-cmd --add-service=freeipa-ldap --add-service=freeipa-ldaps --permanent

3. Reload the firewall daemon to ensure that the changes thus made take effect.

   .. code-block:: shell

        sudo firewall-cmd --reload

4. Install the FreeIPA server package without the optionally provided
   dependencies.

   .. code-block:: shell

        sudo dnf install freeipa-server --setopt=install_weak_deps=False

5. Set up a DNS server depending on the deployment environment preferences.

   Either set up DNS entries on an already used DNS service in the
   infrastructure

   Or elect to use the integrated DNS server for FreeIPA.

   .. code-block:: shell

        sudo dnf install freeipa-server-dns --setopt=install_weak_deps=False

6. Install the Fedora Account System plugin for IPA

   By either executing the following command

   .. code-block:: shell

        sudo dnf install freeipa-fas --setopt=install_weak_deps=False

   Or by running ``install.sh`` after checking out the codebase from the
   `freeipa-fas <https://github.com/fedora-infra/freeipa-fas/>`_ repository.

7. Configure the installed FreeIPA server using the following command.

   .. code-block:: shell

        sudo ipa-server-install

8. Answer the questions mentioned in the prompts of the installation script.

   Sticking to the values used before is mandatory in order for the server to
   work properly.

   .. code-block::

        The log file for this installation can be found in /var/log/ipaserver-install.log
        ==============================================================================
        This program will set up the IPA Server.
        Version 4.11.0

        This includes:
          * Configure a stand-alone CA (dogtag) for certificate management
          * Configure the NTP client (chronyd)
          * Create and configure an instance of Directory Server
          * Create and configure a Kerberos Key Distribution Center (KDC)
          * Configure Apache (httpd)
          * Configure SID generation
          * Configure the KDC to enable PKINIT

        To accept the default shown in brackets, press the Enter key.

        Do you want to configure integrated DNS (BIND)? [no]: no

        Enter the fully qualified domain name of the computer
        on which you're setting up server software. Using the form
        <hostname>.<domainname>
        Example: master.example.com


        Server host name [<FQDN>]: <FQDN>

        The domain name has been determined based on the host name.

        Please confirm the domain name [<DOMAIN.TLD>]: <DOMAIN.TLD>

        The kerberos protocol requires a Realm name to be defined.
        This is typically the domain name converted to uppercase.

        Please provide a realm name [<DOMAIN.TLD>]: <DOMAIN.TLD>
        Certain directory server operations require an administrative user.
        This user is referred to as the Directory Manager and has full access
        to the Directory for system management tasks and will be added to the
        instance of directory server created for IPA.
        The password must be at least 8 characters long.

        Directory Manager password: <DM_PASS>
        Password (confirm): <DM_PASS>

        The IPA server requires an administrative user, named 'admin'.
        This user is a regular system account used for IPA server administration.

        IPA admin password: <SU_PASS>
        Password (confirm): <SU_PASS>

        Trust is configured but no NetBIOS domain name found, setting it now.
        Enter the NetBIOS name for the IPA domain.
        Only up to 15 uppercase ASCII letters, digits and dashes are allowed.
        Example: EXAMPLE.

        NetBIOS domain name [<DOMAIN>]: <DOMAIN>

        Do you want to configure chrony with NTP server or pool address? [no]: no

        The IPA Master Server will be configured with:
        Hostname:       <FQDN>
        IP address(es): <ADDRESS_IPV4>
        Domain name:    <DOMAIN.TLD>
        Realm name:     <DOMAIN.TLD>

        The CA will be configured with:
        Subject DN:   CN=Certificate Authority,O=<DOMAIN.TLD>
        Subject base: O=<DOMAIN.TLD>
        Chaining:     self-signed

        Continue to configure the system with these values? [no]: yes

        The following operations may take some minutes to complete.
        Please wait until the prompt is returned.

        Disabled p11-kit-proxy
        Synchronizing time
        No SRV records of NTP servers found and no NTP server or pool address was provided.
        Using default chrony configuration.


9. Make note of the newly added values to the installation script prompts.

   These values would be used later while setting up the FreeIPA client in
   the Noggin server.


Setting up users after authentication
-------------------------------------

1. Login as the service administrator user using the password mentioned before.

   .. code-block:: shell

        kinit admin
        Password for admin@<FQDN>: <SU_PASS>

2. Add your first user to the FreeIPA server using the following command.

   .. code-block:: shell

        ipa user-add


Configuring FreeIPA server for registration
-------------------------------------------

To allow for the management of registering users, the corresponding roles and
privileges need to be set up in the FreeIPA server.

1. Create a privilege containing the permissions needed to manage stage users
   by executing the following commands.

   .. code-block:: shell

        ipa privilege-add "Stage User Managers" --desc "Manage registering users in Noggin"

   .. code-block:: shell

        ipa privilege-add-permission "Stage User Managers" --permissions "System: Read Stage Users" --permissions "System: Modify Stage User" --permissions "System: Remove Stage User"

2. Create a role associated with this privilege by executing the following
   command.

   .. code-block:: shell

        ipa role-add "Stage User Managers" --desc "Manage registering users in Noggin"

   .. code-block:: shell

        ipa role-add-privilege "Stage User Managers" --privileges "Stage User Managers"

3. For an administrators group called ``sysadmin``, allow people in the
   ``sysadmin`` group the role to manage registering users.

   .. code-block:: shell

        ipa role-add-member "Stage User Managers" --groups sysadmin


Configuring FreeIPA server for passkey management
--------------------------------------------------

Noggin supports self-service management of FIDO2 passkeys. This requires
FreeIPA v4.10 or later, which includes built-in passkey support and the
self-service permission allowing users to manage their own passkeys.

.. note::
    The WebAuthn Relying Party (RP) ID is always the IPA primary domain
    (the Kerberos realm in lowercase). Noggin must be served from a hostname
    under this domain for passkey registration to work. For example, if the
    IPA domain is ``example.com``, Noggin can be at ``accounts.example.com``
    but not at ``accounts.otherdomain.com``.


Configuring Kerberos delegation for passkey login
-------------------------------------------------

Noggin can authenticate users via their registered passkeys. After verifying
the WebAuthn assertion locally, Noggin uses Kerberos protocol transition
(S4U2Self) to obtain a Kerberos ticket on behalf of the user, and then
constrained delegation (S4U2Proxy) to present that ticket to the FreeIPA HTTP
service and obtain a user-scoped IPA session.

This requires:

- FreeIPA v4.10 or later
- A Kerberos service principal and keytab for the Noggin service
- Constrained delegation rules allowing Noggin's service principal to
  delegate to the IPA HTTP service on behalf of users

.. note::
    FreeIPA's HTTP service principal is already configured with general
    constrained delegation rules (the built-in ``ipa-http-delegation`` rule
    that allows the IPA HTTP service to delegate to the LDAP service). Because
    a Kerberos principal can only be governed by one delegation mechanism,
    Resource-Based Constrained Delegation (RBCD) cannot be used to target the
    IPA HTTP service. The setup below uses general constrained delegation
    instead. For background on both mechanisms, see the
    `FreeIPA RBCD design document <https://freeipa.readthedocs.io/en/latest/designs/rbcd.html>`_
    and the
    `Service Constraint Delegation design <https://www.freeipa.org/page/V4/Service_Constraint_Delegation>`_.


Step 1: Create a service principal for Noggin
`````````````````````````````````````````````

The Noggin host must be enrolled as a FreeIPA client (via ``ipa-client-install``)
or at least have a host entry in IPA. Then create an HTTP service principal for
Noggin:

.. code-block:: shell

    kinit admin
    ipa service-add HTTP/noggin.example.com

Replace ``noggin.example.com`` with the fully qualified hostname where Noggin
is deployed.


Step 2: Obtain a keytab
```````````````````````

Generate a keytab file for the Noggin service principal. Run this command on
the Noggin host (or any enrolled host, then copy the keytab securely):

.. code-block:: shell

    ipa-getkeytab -s ipa.example.com -p HTTP/noggin.example.com \
        -k /etc/noggin/noggin.keytab

Set appropriate permissions so only the Noggin service user can read the
keytab:

.. code-block:: shell

    chown noggin:noggin /etc/noggin/noggin.keytab
    chmod 600 /etc/noggin/noggin.keytab


Step 3: Enable protocol transition (ok-to-auth-as-delegate)
````````````````````````````````````````````````````````````

For S4U2Self to produce forwardable tickets (required for the subsequent
S4U2Proxy step), the Noggin service principal must have the
``ok-to-auth-as-delegate`` flag set:

.. code-block:: shell

    ipa service-mod HTTP/noggin.example.com --ok-to-auth-as-delegate=True

This flag allows the Noggin service to perform protocol transition — that is,
to obtain a Kerberos ticket on behalf of a user who authenticated via a
non-Kerberos mechanism (in this case, a passkey/WebAuthn assertion).

.. warning::
    The ``ok-to-auth-as-delegate`` flag grants the service the ability to
    impersonate any user to itself. The constrained delegation rules (next
    step) limit which target services the impersonated tickets can be
    forwarded to.


Step 4: Configure constrained delegation rules
````````````````````````````````````````````````

Create a constrained delegation target containing the IPA HTTP service
principal, and a rule that grants the Noggin service principal permission
to delegate to that target.

First, create a delegation target for the IPA HTTP service:

.. code-block:: shell

    ipa servicedelegationtarget-add noggin-delegation-targets

Add the IPA HTTP service principal(s) to the target. If you have multiple
IPA servers, add all of them:

.. code-block:: shell

    ipa servicedelegationtarget-add-member noggin-delegation-targets \
        --principals=HTTP/ipa.example.com@EXAMPLE.COM

    # If you have multiple IPA servers:
    ipa servicedelegationtarget-add-member noggin-delegation-targets \
        --principals=HTTP/ipa2.example.com@EXAMPLE.COM

Next, create a delegation rule and add the Noggin service as a member:

.. code-block:: shell

    ipa servicedelegationrule-add noggin-delegation
    ipa servicedelegationrule-add-member noggin-delegation \
        --principals=HTTP/noggin.example.com@EXAMPLE.COM

Finally, link the rule to the target:

.. code-block:: shell

    ipa servicedelegationrule-add-target noggin-delegation \
        --servicedelegationtargets=noggin-delegation-targets

Replace ``EXAMPLE.COM`` with your Kerberos realm (typically the IPA domain
in uppercase).


Step 5: Verify the delegation setup
````````````````````````````````````

Test the full S4U2Self + S4U2Proxy chain from the Noggin host using ``kvno``:

.. code-block:: shell

    kvno -U testuser -k /etc/noggin/noggin.keytab \
         -P HTTP/noggin.example.com HTTP/ipa.example.com

This command authenticates as the Noggin service using its keytab, obtains
an S4U2Self ticket on behalf of ``testuser``, and uses S4U2Proxy to request
a ticket to the IPA HTTP service. A successful result confirms the delegation
chain is correctly configured.


Step 6: Configure Noggin
`````````````````````````

Add the following settings to Noggin's configuration file
(``/etc/noggin/noggin.cfg``):

.. code-block:: python

    # Path to the Kerberos keytab for the Noggin service.
    # Setting this enables passkey login.
    KERBEROS_KEYTAB = '/etc/noggin/noggin.keytab'

    # The service principal in the keytab. If not set, Noggin derives it
    # from the machine's FQDN and the FREEIPA_DOMAIN setting:
    # HTTP/<fqdn>@<FREEIPA_DOMAIN in uppercase>
    # KERBEROS_SERVICE_PRINCIPAL = 'HTTP/noggin.example.com@EXAMPLE.COM'

When ``KERBEROS_KEYTAB`` is set to a valid keytab path, the passkey login
button appears on the login page. When it is ``None`` (the default), passkey
login is disabled and the button is hidden.


Discretion
==========

As there can be multiple ways of installing and configuring a FreeIPA server,
please refer to the basic quick start guide provided on the
`FreeIPA website <https://www.freeipa.org/page/Quick_Start_Guide>`_ and the
comprehensive setup documentation on the
`Red Hat website <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/installing_identity_management/index>`_
if the aforementioned guide does not work.
