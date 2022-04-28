# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  config.vm.box = "generic/debian11"
  config.vm.disk :disk, size: "8GB", primary: true
  config.vm.network "private_network", ip: "192.168.56.101"
  config.vm.synced_folder "~/vbox/shared/", "/media/sf_ddrshared", automount: true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = true
    vb.memory = "2048"
  end

  # Create shared folder so VM can access playbook and secrets
  config.vm.synced_folder ".", "/vagrant"

  # Ansible playbook for setting up VM and installing ddr-local
  config.vm.provision "ansible_local" do |ansible|
    ansible.playbook = "playbook.yml"
    ansible.install = true
    ansible.compatibility_mode = "2.0"
    ansible.become = true
    ansible.verbose = true
  end

end
