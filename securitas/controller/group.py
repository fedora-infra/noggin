from flask import render_template, session

from securitas import app
from securitas.representation.user import User
from securitas.representation.group import Group
from securitas.utility import group_or_404, with_ipa

@app.route('/group/<groupname>/')
@with_ipa(app, session)
def group(ipa, groupname):
    group = Group(group_or_404(ipa, groupname))
    members = {}
    sponsors = {}
    for member in group.members:
        info = User(ipa.user_show(member))
        members[info.username] = info
    for sponsor in group.sponsors:
        if sponsor in members:
            sponsors[sponsor] = members[sponsor]
        else:
            info = User(ipa.user_show(sponsor))
            sponsors[info.username] = info

    return render_template(
        'group.html',
        group=group,
        members=members,
        sponsors=sponsors)

@app.route('/groups/')
@with_ipa(app, session)
def groups(ipa):
    groups = [Group(g) for g in ipa.group_find()['result']]
    return render_template('groups.html', groups=groups)
