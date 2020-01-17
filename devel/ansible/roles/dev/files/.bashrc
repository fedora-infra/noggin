# .bashrc

export FLASK_APP=/vagrant/securitas/app.py
export SECURITAS_CONFIG_PATH=/home/vagrant/securitas.cfg

alias securitas-start="sudo systemctl start securitas.service && echo 'Securitas is running on http://0.0.0.0:5000'"
alias securitas-unit-tests="SECURITAS_CONFIG_PATH=/vagrant/securitas/tests/unit/securitas.cfg poetry run pytest -vv securitas/tests/unit"
alias securitas-logs="sudo journalctl -u securitas.service"
alias securitas-restart="sudo systemctl restart securitas.service && echo 'Securitas is running on http://0.0.0.0:5000'"
alias securitas-stop="sudo systemctl stop securitas.service && echo 'Securitas service stopped'"

cd /vagrant
