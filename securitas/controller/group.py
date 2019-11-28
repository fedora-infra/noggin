from flask import flash, render_template, redirect, session, url_for
import python_freeipa

from securitas import app
from securitas.form.add_group_member import AddGroupMemberForm
from securitas.form.remove_group_member import RemoveGroupMemberForm
from securitas.representation.user import User
from securitas.representation.group import Group
from securitas.utility import group_or_404, with_ipa

@app.route('/group/<groupname>/')
@with_ipa(app, session)
def group(ipa, groupname):
    group = Group(group_or_404(ipa, groupname))
    sponsor_form = AddGroupMemberForm(groupname=groupname)
    remove_form = RemoveGroupMemberForm(groupname=groupname)
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
        sponsors=sponsors,
        sponsor_form=sponsor_form,
        remove_form=remove_form,
    )

@app.route('/group/add-member/', methods=['POST'])
@with_ipa(app, session)
def group_add_member(ipa):
    sponsor_form = AddGroupMemberForm()
    if sponsor_form.validate_on_submit():
        username = sponsor_form.new_member_username.data
        groupname = sponsor_form.groupname.data
        # First make sure the user exists
        try:
            user = ipa.user_show(username)
        except python_freeipa.exceptions.NotFound:
            flash('User %s was not found in the system.' % username, 'red')
            return redirect(url_for('group', groupname=groupname))
        try:
            ipa.group_add_member(groupname, users=username)
        except python_freeipa.exceptions.ValidationError as e:
            # e.message is a dict that we have to process ourselves for now:
            # https://github.com/opennode/python-freeipa/issues/24
            for error in e.message['member']['user']:
                flash('Unable to add user %s: %s' % (error[0], error[1]), 'red')

            for error in e.message['member']['group']:
                flash('Unable to add group %s: %s' % (error[0], error[1]), 'red')

            return redirect(url_for('group', groupname=groupname))

        flash(
            'You got it! %s has been added to %s.' % (username, groupname),
            'green')
        return redirect(url_for('group', groupname=groupname))

@app.route('/group/remove-member/', methods=['POST'])
@with_ipa(app, session)
def group_remove_member(ipa):
    form = RemoveGroupMemberForm()
    if form.validate_on_submit():
        groupname = form.groupname.data
        username = form.username.data
        try:
            ipa.group_remove_member(groupname, users=username)
        except python_freeipa.exceptions.ValidationError as e:
            # e.message is a dict that we have to process ourselves for now:
            # https://github.com/opennode/python-freeipa/issues/24
            for error in e.message['member']['user']:
                flash('Unable to remove user %s: %s' % (error[0], error[1]), 'red')

            for error in e.message['member']['group']:
                flash('Unable to remove group %s: %s' % (error[0], error[1]), 'red')

            return redirect(url_for('group', groupname=groupname))

        flash(
            'You got it! %s has been removed from %s.' % (username, groupname),
            'green')
        return redirect(url_for('group', groupname=groupname))

@app.route('/groups/')
@with_ipa(app, session)
def groups(ipa):
    groups = [Group(g) for g in ipa.group_find()['result']]
    return render_template('groups.html', groups=groups)
