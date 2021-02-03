# .bashrc
alias noggin-ipa-resetdb="sudo ipa-restore /var/lib/ipa/backup/backup-clean -p {{ ipa_admin_password }}"
alias noggin-ipa-populatedb="python /home/vagrant/create_dummy_data.py"
