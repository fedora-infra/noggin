from flask import render_template, session

from securitas import app
from securitas.utility import with_ipa

@app.route('/user/<username>/')
@with_ipa(app, session)
def user(ipa, username):
    user = ipa.user_show(username)
    return render_template('user.html', user=user)
