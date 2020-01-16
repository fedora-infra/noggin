# .bashrc

export FLASK_APP=/vagrant/securitas/app.py
export SECURITAS_CONFIG_PATH=/home/vagrant/securitas.cfg

alias securitas-devel="poetry run flask run --host=0.0.0.0"