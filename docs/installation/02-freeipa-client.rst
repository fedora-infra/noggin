============================
Setting up the Noggin server
============================

Preparation
===========

In order to run a Noggin server in a virtual machine, we need to set up the
following four files in the same directory.

.. code-block:: yaml

    .
    ├── Fedora-Cloud-Base-XX-A.B.x86_64.raw
    ├── main.cfg
    ├── main.sh
    └── main.yml

    1 directory, 4 files


Sourcing Image
--------------

Download the most recent release of
`Fedora Linux Cloud Edition <https://fedoraproject.org/cloud/download/>`_
in the RAW extension.


Network Configuration
---------------------

After replacing the variables mentioned below, the ``main.cfg`` file should
look like the following.

- IPv4 gateway - ``<GATEWAY_IPV4>``
- IPv4 address - ``<ADDRESS_IPV4_WITH_SUBNET>``
- IPv4 DNS servers - ``<DNSLIST_IPV4>``
- DHCP on IPv4 - ``Disabled``
- DHCP on IPv6 - ``Disabled``

Ensure that the ``<ADDRESS_IPV4>`` of the virtual machine running the FreeIPA
server is accessible from the chosen network configuration here.

It is strongly recommended to have the virtual machine for the Noggin server
set up in the same subnet as that of the virtual machine running the FreeIPA
server to minimize latencies and possible performance inconsistencies.

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

After replacing the variables mentioned below, the ``main.yml`` file should
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

After replacing the variables mentioned below, the ``main.sh`` file should
look like the following.

- Specific hostname - ``nogginvirt``
- Environment name - ``main``
- Memory size (in MB, should be minimum 2048) - ``4096``
- CPU count (should be minimum 2) - ``4``
- Network configuration file location - ``<PATH_TO_MAIN_CFG>``
- Machine configuration file location - ``<PATH_TO_MAIN_YML>``
- Disk size (in GB, should be minimum 16) - ``24G``
- Cloud image file location (in RAW) - ``<CLOUD_INPUT_IMAGE>``
- Output image file location (in RAW) - ``<CLOUD_OUTPUT_IMAGE>``
- Network interface binding name - ``<BINDNAME>``
- VNC port number - ``<DESKPORT>``
- Operating system variant - ``fedora-unknown``

.. code-block:: shell

    #!/bin/sh

    SPECNAME="nogginvirt"
    EVMTNAME="main"
    MEMCOUNT="4096"
    CPUCOUNT="4"
    NTWKFILE="<PATH_TO_MAIN_CFG>"
    CINTFILE="<PATH_TO_MAIN_YML>"
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

        sh main.sh

   .. code-block:: shell

        image: main.img
        file format: raw
        virtual size: 2 GiB (2147483648 bytes)
        disk size: 622 MiB
        Child node '/file':
            filename: main.img
            protocol type: file
            file length: 2 GiB (2147483648 bytes)
            disk size: 622 MiB

        image: main.img
        file format: raw
        virtual size: 24 GiB (25769803776 bytes)
        disk size: 622 MiB
        Child node '/file':
            filename: main.img
            protocol type: file
            file length: 24 GiB (25769803776 bytes)
            disk size: 622 MiB

        Starting install...
        Creating domain...
        Domain creation completed.

4. Monitor the instantiation of the cloud installation using the following
   command.

   .. code-block:: shell

        virsh console nogginvirt-main

5. Connect to the instantiated cloud installation using the following command.

   .. code-block:: shell

        ssh -i <PATH_TO_SSHKEY> <USERNAME>@<ADDRESS_IPV4>


Installing and configuring a web server
---------------------------------------

1. Choose a web serer compatible with the deployment environment preferences.

   Either configure an already used web server in the infrastructure

   Or elect to use Nginx which is the default for this documentation.

   .. code-block:: shell

        sudo dnf install nginx --setopt=install_weak_deps=False


Setting up a Noggin installation
--------------------------------

Noggin server can be installed on the cloud installation using one of the
following three methods.

- Installing from PyPI

- Installing from Fedora Linux repositories

- Installing from source


Installing from PyPI
````````````````````

1. Execute the following command to install Noggin and Noggin Messages project
   from PyPI.

   .. code-block:: shell

        pip3 install noggin-aaa noggin-messages

2. Download the ``noggin.cfg.example`` file from
   `here <https://github.com/fedora-infra/noggin/raw/v1.9.0/deployment/noggin.cfg.example>`__
   and copy it to the ``/etc/noggin`` directory as ``noggin.cfg`` file. Edit
   the variables (eg. the ``FREEIPA_*`` items to point to the FreeIPA server
   deployment.

3. Download the ``nginx.conf`` file from
   `here <https://github.com/fedora-infra/noggin/raw/v1.9.0/deployment/nginx.conf>`__
   and copy it to the ``/etc/nginx/conf.d`` directory as ``nginx.conf``. Make
   adjustments according to the deployment requirements (eg. HTTPS or not,
   certificates, domains etc.)

4. Download the ``noggin.service`` file from
   `here <https://github.com/fedora-infra/noggin/raw/v1.9.0/deployment/noggin.service>`__
   and copy it to the ``/etc/systemd/system`` directory as ``noggin.service``.

   Adjust the ``ExecStart`` section to account for the installation
   environment, WSGI changes, IP address and port numbers.

   If Noggin was installed as the ``root`` user, change ``gunicorn`` location
   to ``/usr/local/bin/gunicorn`` in the unit file.

   If Noggin was installed as a normal user, change ``gunicorn`` location to
   ``/home/<USERNAME>/.local/bin/gunicorn`` in the unit file.

5. Download the ``noggin.sysconfig`` file from
   `here <https://github.com/fedora-infra/noggin/raw/v1.9.0/deployment/noggin.sysconfig>`__
   and copy it to the ``/etc/sysconfig`` directory as ``noggin``.


Installing from Fedora Linux repositories
`````````````````````````````````````````

1. Execute the following command to install Noggin package from the Fedora
   Linux repositories.

   .. code-block:: shell

        sudo dnf install noggin

2. Edit the configuration file for Noggin located in the
   ``/etc/noggin/noggin.cfg`` directory with the variables used for setting
   up the FreeIPA server (eg. the ``FREEIPA_*`` items) to point to the
   FreeIPA server deployment.

3. Edit the web server configuration file named ``nginx.conf`` located in the
   ``/etc/nginx/conf.d`` directory and make adjustments according to the
   deployment requirements (eg. HTTPS or not, certificates, domains etc.)

4. Edit the service unit file named ``noggin.service`` located in the
   ``/etc/systemd/system`` directory and make changes in the ``ExecStart``
   section to account for the installation environment, WSGI changes, IP
   address and port numbers.

5. Copy the ``noggin.sysconfig`` file from the ``deployment`` directory to the
   ``/etc/sysconfig`` directory as ``noggin``.


Installing from source
``````````````````````

1. Download and extract the most recent tarball from the primary branch of
   the repository.

   .. code-block:: shell

        wget https://github.com/fedora-infra/noggin/releases/download/v1.9.0/noggin_aaa-1.9.0.tar.gz

   .. code-block:: shell

        tar -xvzf noggin_aaa-1.9.0.tar.gz

2. Install ``poetry`` and ``virtualenv`` using the following command if not
   already installed.

   .. code-block:: shell

        sudo dnf install poetry virtualenv --setopt=install_weak_deps=False

3. Create and activate a virtual environment in the project directory.

   .. code-block:: shell

        cd noggin_aaa

   .. code-block:: shell

        virtualenv venv

   .. code-block:: shell

        source venv/bin/activate

4. Install the project assets and its dependencies using the following command.

   .. code-block:: shell

        (venv) poetry install --without-dev --extras deploy

5. Copy the ``noggin.cfg.example`` file from the ``deployment`` directory to
   the ``/etc/noggin`` directory as ``noggin.cfg`` and add the variables used
   for setting up the FreeIPA server (eg. the ``FREEIPA_*`` items) to point to
   the FreeIPA server deployment.

6. Copy the ``nginx.conf`` file from the ``deployment`` directory to the
   ``/etc/nginx/conf.d`` directory as ``nginx.conf`` and make adjustments
   according to the deployment requirements (eg. HTTPS or not, certificates,
   domains etc.)

7. Copy the ``noggin.service`` file from the ``deployment`` directory to the
   ``/etc/systemd/system`` directory as ``noggin.service`` and adjust the
   ``ExecStart`` section to account for the installation environment, WSGI
   changes, IP address and port numbers. Change ``gunicorn`` location to
   ``/<PATH_TO_VIRTUALENV>/bin/gunicorn`` in the unit file.

8. Copy the ``noggin.sysconfig`` file from the ``deployment`` directory to the
   ``/etc/sysconfig`` directory as ``noggin``.


Allowing ports through the firewall
-----------------------------------

1. Execute the following commands to allow the required ports through the
   firewall.

   .. code-block:: shell

        sudo firewall-cmd --add-service=http --permanent

   .. code-block:: shell

        sudo firewall-cmd --add-service=https --permanent

2. Reload the firewall daemon to ensure that the changes thus made take effect.

   .. code-block:: shell

        sudo firewall-cmd --reload


Starting the services
---------------------

1. Execute the following command to enable and start the Nginx and Noggin
   services.

   .. code-block:: shell

        sudo systemctl enable --now noggin.service

   .. code-block:: shell

        sudo systemctl enable --now nginx.service


Discretion
==========

For more information, take a look at the
`official Noggin documentation <https://noggin-aaa.readthedocs.io/>`_.
