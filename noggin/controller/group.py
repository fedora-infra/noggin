from flask import flash, g, render_template, redirect, session, url_for
from flask_babel import _
import python_freeipa
from noggin_messages import MemberSponsorV1

from noggin import app
from noggin.form.add_group_member import AddGroupMemberForm
from noggin.form.remove_group_member import RemoveGroupMemberForm
from noggin.representation.user import User
from noggin.representation.group import Group
from noggin.utility import group_or_404, with_ipa, messaging, undo_button


@app.route('/group/<groupname>/')
@with_ipa(app, session)
def group(ipa, groupname):
    group = Group(group_or_404(ipa, groupname))
    sponsor_form = AddGroupMemberForm(groupname=groupname)
    remove_form = RemoveGroupMemberForm(groupname=groupname)

    members = [User(u) for u in ipa.user_find(in_group=groupname)['result']]

    batch_methods = [
        {"method": "user_find", "params": [[], {"uid": sponsorname, 'all': True}]}
        for sponsorname in group.sponsors
    ]
    sponsors = [
        User(u['result'][0]) for u in ipa.batch(methods=batch_methods)['results']
    ]

    # We can safely assume g.current_user exists after @with_ipa
    current_user_is_sponsor = g.current_user.username in group.sponsors

    return render_template(
        'group.html',
        group=group,
        members=members,
        sponsors=sponsors,
        sponsor_form=sponsor_form,
        remove_form=remove_form,
        current_user_is_sponsor=current_user_is_sponsor,
    )


@app.route('/group/<groupname>/members/', methods=['POST'])
@with_ipa(app, session)
def group_add_member(ipa, groupname):
    group_or_404(ipa, groupname)
    sponsor_form = AddGroupMemberForm()
    if sponsor_form.validate_on_submit():
        username = sponsor_form.new_member_username.data
        # First make sure the user exists
        try:
            ipa.user_show(username)
        except python_freeipa.exceptions.NotFound:
            flash(
                _('User %(username)s was not found in the system.', username=username),
                'danger',
            )
            return redirect(url_for('group', groupname=groupname))
        try:
            ipa.group_add_member(group=groupname, users=username)
        except python_freeipa.exceptions.ValidationError as e:
            # e.message is a dict that we have to process ourselves for now:
            # https://github.com/opennode/python-freeipa/issues/24
            for error in e.message['member']['user']:
                flash(
                    _(
                        'Unable to add user %(username)s: %(errormessage)s',
                        username=error[0],
                        errormessage=error[1],
                    ),
                    'danger',
                )
            return redirect(url_for('group', groupname=groupname))

        flash_text = _(
            'You got it! %(username)s has been added to %(groupname)s.',
            username=username,
            groupname=groupname,
        )
        flash(
            flash_text
            + undo_button(
                url_for("group_remove_member", groupname=groupname),
                "username",
                username,
                sponsor_form.hidden_tag(),
            ),
            'success',
        )

        messaging.publish(
            MemberSponsorV1(
                {
                    "msg": {
                        "agent": g.current_user.username,
                        "user": username,
                        "group": groupname,
                    }
                }
            )
        )

        return redirect(url_for('group', groupname=groupname))

    for field_errors in sponsor_form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('group', groupname=groupname))


@app.route('/group/<groupname>/members/remove', methods=['POST'])
@with_ipa(app, session)
def group_remove_member(ipa, groupname):
    group_or_404(ipa, groupname)
    form = RemoveGroupMemberForm()
    if form.validate_on_submit():
        username = form.username.data
        try:
            ipa.group_remove_member(group=groupname, users=username)
        except python_freeipa.exceptions.ValidationError as e:
            # e.message is a dict that we have to process ourselves for now:
            # https://github.com/opennode/python-freeipa/issues/24
            for error in e.message['member']['user']:
                flash('Unable to remove user %s: %s' % (error[0], error[1]), 'danger')
            return redirect(url_for('group', groupname=groupname))
        flash_text = _(
            'You got it! %(username)s has been removed from %(groupname)s.',
            username=username,
            groupname=groupname,
        )
        flash(
            flash_text
            + undo_button(
                url_for("group_add_member", groupname=groupname),
                "new_member_username",
                username,
                form.hidden_tag(),
            ),
            'success',
        )
        return redirect(url_for('group', groupname=groupname))

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('group', groupname=groupname))


@app.route('/groups/')
@with_ipa(app, session)
def groups(ipa):
    groups = [Group(g) for g in ipa.group_find(fasgroup=True)['result']]
    return render_template('groups.html', groups=groups)
