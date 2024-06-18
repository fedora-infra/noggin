# -*- mode: ruby -*-
# vi: set ft=ruby :
ENV['VAGRANT_NO_PARALLEL'] = 'yes'

Vagrant.configure(2) do |config|
  config.hostmanager.enabled = true
  config.hostmanager.manage_host = true
  config.hostmanager.manage_guest = true

  config.vm.define "noggin" do |noggin|
    noggin.vm.box_url = "https://download.fedoraproject.org/pub/fedora/linux/releases/40/Cloud/x86_64/images/Fedora-Cloud-Base-Vagrant-libvirt.x86_64-40-1.14.vagrant.libvirt.box"
    noggin.vm.box = "f40-cloud-libvirt"
    noggin.vm.hostname = "noggin-dev.tinystage.test"

    noggin.vm.synced_folder '.', '/vagrant', disabled: true
    noggin.vm.synced_folder ".", "/home/vagrant/noggin", type: "sshfs"

    noggin.vm.provider :libvirt do |libvirt|
      libvirt.cpus = 2
      libvirt.memory = 2048
    end

    noggin.vm.provision "ansible" do |ansible|
      ansible.playbook = "devel/ansible/noggin.yml"
      ansible.verbose = true
    end
  end

end
