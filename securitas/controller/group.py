from flask import render_template, session

from securitas import app
from securitas.utility import group_or_404, with_ipa

@app.route('/group/<groupname>/')
@with_ipa(app, session)
def group(ipa, groupname):
    group = group_or_404(ipa, groupname)
    return render_template('group.html', group=group)

@app.route('/groups/')
@with_ipa(app, session)
def groups(ipa):
    groups = ipa.group_find()
    return render_template('groups.html', groups=groups)
