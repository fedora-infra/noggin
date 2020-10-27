============
Installation
============
Installation documentation for Noggin.


============
Requirements
============
Noggin requires the following to operate:

1. Access to a FreeIPA/Red Hat Identity Management installation
2. Access to an Openshift cluster to run the Noggin container


===================================
Install Red Hat Identity Management
===================================
For more information see the following documents regarding installation

1. .. _Docs: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/installing_identity_management/preparing-the-system-for-ipa-server-installation_installing-identity-management
2. .. _Playbook install docs: https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/installing_identity_management/installing-an-identity-management-replica-using-an-ansible-playbook_installing-identity-management
3. .. _Ansible FreeIPA module docs: https://github.com/freeipa/ansible-freeipa


Install ansible and ansible-freeipa rpms

::
    yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
    ARCH=$( /bin/arch )
    subscription-manager repos --enable "codeready-builder-for-rhel-8-${ARCH}-rpms"
    yum install ansible
    yum install ansible-freeipa
    yum install freeipa-fas


The location where the ansible roles are installed:

::
    [root@server]# ls -1 /usr/share/ansible/roles/
    ipaclient
    ipareplica
    ipaserver


The location where the documentation is once installed:

::
    [root@server]# ls -1 /usr/share/doc/ansible-freeipa/
    playbooks
    README-client.md
    README.md
    README-replica.md
    README-server.md
    README-topology.md


The location where the ansible playbooks are once installed:

::
    [root@server]# ls -1 /usr/share/doc/ansible-freeipa/playbooks/
    install-client.yml
    install-cluster.yml
    install-replica.yml
    install-server.yml
    uninstall-client.yml
    uninstall-cluster.yml
    uninstall-replica.yml
    uninstall-server.yml


Sample Inventory:

::
    [root@server]# cat inventory
    [ipaservers]
    ipa01.stg.iad2.fedoraproject.org

    [ipareplicas]
    ipa02.stg.iad2.fedoraproject.org

    [ipaserver:vars]
    ipaserver_domain=stg.iad2.fedoraproject.org
    ipaserver_realm=STG.FEDORAPROJECT.ORG
    ipaserver_setup_dns=yes
    ipaserver_auto_forwarders=yes
    ipaadmin_password=adminPassw0rd!

    [ipareplicas:vars]
    ipaadmin_password=adminPassw0rd!
    testuser_password=testuserPass0rd!


A sample playbook making use of the role to install the server:

::
    [root@server]# cat install_server.yaml
    ---
    - name: Playbook to configure IPA server
      hosts: ipaservers
      become: true

      roles:
      - role: ipaserver
        state: present

    [root@server]# ansible-playbook -i inventory install_server.yaml



A sample playbook making use of the install a replica role:

::
    [root@server]# cat install_replica.yaml
    ---
    - name: Playbook to configure IPA replicas
      hosts: ipareplicas
      become: true

      roles:
      - role: ipareplica
        state: present

    [root@server]# ansible-playbook -i inventory install_replica.yaml


A sample playbook making use of the ipauser role to create an admin and test user

::
    ---
    - name: Playbook to handle users
      hosts: ipaservers
      become: true

      tasks:
      - name: Set the password for the admin user
        ipauser:
          name: admin
          update_password: on_create
          ipaadmin_password: "{{ ipaadmin_password }}"

      - name: Set test user password
        ipauser:
          name: test
          password: "{{ test_password }}"
          update_password: on_create
 

A sample playbook making use of the ipagroup role to create a group and add the test user to it.

::
    ---
    - name: Playbook to handle groups
      hosts: ipaservers
      become: true

      tasks:
      - ipagroup:
        ipaadmin_password: "{{ ipaadmin_password }}"
        name: ops
        user:
        - test
    

===================
Noggin Installation
===================

To see a full list of possible configurations for Noggin, check the sample configuration file at .. _Docs: https://github.com/fedora-infra/noggin/blob/dev/noggin.cfg.default
The template used during installation can be updated with these configurations: .. _Config template: https://pagure.io/fedora-infra/ansible/blob/master/f/roles/openshift-apps/noggin/templates/noggin.cfg.py


Clone the Fedora infrastructure ansible repo:

::
    [root@server]# git clone https://pagure.io/fedora-infra/ansible.git


The ansible playbooks require a number of variables to be set and available:

::
    [root@server]# cat extravars.yml
    # These variables will be used when env == 'production'
    noggin_admin_password: "somepassword"                                      # IPA password for the user noggin
    noggin_fernet_secret: "G8ObvrpEEwbjWUO9rU1qAkDQRafAFd39heVKYf6TZi8="       # Fernet Cryptography key
    noggin_session_secret: "monkiesmonkiesmonkiesmonkiesmonkies!!!1111monkies" # Session Secret
    noggin_github_secret: ""                                                   # Openshift github webhook, not needed
    env: "production"
    env_suffix: ""                                                             # Empty for production

    # These variables will be used when env == 'dev' or set to any value other than 'production'
    # noggin_stg_admin_password: ""
    # noggin_stg_fernet_secret: ""
    # noggin_stg_session_secret: ""
    # noggin_stg_github_secret : "" # Openshift github webhook, not needed
    # env: "staging"
    # env_suffix: ".stg"

    noggin_theme: "default"                                                    # Default noggin theme
    ipa_server: "{{ ipa_stg }}"                                                # Hostname for the ipa server

Example inventory:

::
    [root@server]# cd ansible
    [root@server]# cat inventory
    [os_masters_stg]
    os-master01.stg.iad2.fedoraproject.org
    os-master02.stg.iad2.fedoraproject.org
    os-master03.stg.iad2.fedoraproject.org

    [os_infra_nodes_stg]
    os-node01.stg.iad2.fedoraproject.org
    os-node02.stg.iad2.fedoraproject.org
    os-node03.stg.iad2.fedoraproject.org
    os-node04.stg.iad2.fedoraproject.org
    os-node05.stg.iad2.fedoraproject.org

    [os_nodes_stg:children]
    os_infra_nodes_stg


    [os_control]
    os-control01.iad2.fedoraproject.org

    [os_stg:children]
    os_nodes_stg
    os_masters_stg
    os_control_stg

    [ipa_stg]
    ipa01.stg.iad2.fedoraproject.org


Run the installation playbook:

::
    [root@server]# ansible-playbook -i inventory/inventory playbooks/openshift-apps/noggin.yml -e "@extravars.yml"
