FROM registry.fedoraproject.org/fedora-minimal:latest
# install the base packages
RUN microdnf install -y python3-flask poetry fedora-messaging gcc git libffi-devel python3-cryptography python3-devel python3-pip vim
# copy this entire directory to /opt/noggin
WORKDIR /opt/noggin
ADD . /opt/noggin
RUN poetry install --no-dev --extras deploy
RUN poetry run pybabel compile -d /opt/noggin/noggin/translations


ENV FLASK_APP=/opt/noggin/noggin/app.py
ENV NOGGIN_CONFIG_PATH=/etc/noggin.cfg
CMD [ "poetry", "run", "flask", "run", "-h", "0.0.0.0", "-p", "5000" ]