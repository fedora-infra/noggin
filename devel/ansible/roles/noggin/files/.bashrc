# .bashrc

export PATH=$PATH:/home/vagrant/.local/bin

alias noggin-start="sudo systemctl start noggin.service && echo 'Noggin is running on http://0.0.0.0:5000'"
alias noggin-logs="sudo journalctl -u noggin.service"
alias noggin-restart="sudo systemctl restart noggin.service && echo 'Noggin is running on http://0.0.0.0:5000'"
alias noggin-stop="sudo systemctl stop noggin.service && echo 'Noggin service stopped'"
