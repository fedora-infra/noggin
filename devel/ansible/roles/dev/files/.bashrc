# .bashrc

export PATH=$PATH:/home/vagrant/.local/bin

alias noggin-start="sudo systemctl start noggin.service && echo 'Noggin is running on http://0.0.0.0:5000'"
alias noggin-unit-tests="poetry run pytest -vv --cov noggin/ --cov-report term-missing noggin/tests/unit"
alias noggin-logs="sudo journalctl -u noggin.service"
alias noggin-restart="sudo systemctl restart noggin.service && echo 'Noggin is running on http://0.0.0.0:5000'"
alias noggin-stop="sudo systemctl stop noggin.service && echo 'Noggin service stopped'"
alias noggin-ipa-resetdb="sudo ipa-restore /var/lib/ipa/backup/noggin-clean -p adminPassw0rd!"
alias noggin-ipa-populatedb="poetry run python /vagrant/devel/create-test-data.py"

cd /vagrant
