import python_freeipa
from flask import flash, g, redirect, render_template, url_for
from flask_babel import _

from noggin.form.group import AddGroupMemberForm, RemoveGroupMemberForm
from noggin.representation.group import Group
from noggin.representation.user import User
from noggin.security.ipa import raise_on_failed
from noggin.utility import messaging
from noggin.utility.controllers import group_or_404, with_ipa
from noggin.utility.pagination import paginated_find
from noggin.utility.templates import undo_button
from noggin_messages import MemberSponsorV1

from . import blueprint as bp


@bp.route('/group/<groupname>/')
@with_ipa()
def group(ipa, groupname):
    group = Group(group_or_404(ipa, groupname))
    sponsor_form = AddGroupMemberForm(groupname=groupname)
    remove_form = RemoveGroupMemberForm(groupname=groupname)

    members = paginated_find(ipa, User, in_group=groupname, default_page_size=48)

    batch_methods = [
        {"method": "user_find", "params": [[], {"uid": sponsorname, 'all': True}]}
        for sponsorname in group.sponsors
    ]
    # Don't call remote batch method with an empty list
    if batch_methods:
        sponsors = [
            User(u['result'][0]) for u in ipa.batch(a_methods=batch_methods)['results']
        ]
    else:
        sponsors = []

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


@bp.route('/group/<groupname>/members/', methods=['POST'])
@with_ipa()
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
            return redirect(url_for('.group', groupname=groupname))
        try:
            result = ipa.group_add_member(a_cn=groupname, o_user=username)
            raise_on_failed(result)
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
            return redirect(url_for('.group', groupname=groupname))

        flash_text = _(
            'You got it! %(username)s has been added to %(groupname)s.',
            username=username,
            groupname=groupname,
        )
        flash(
            flash_text
            + undo_button(
                url_for(".group_remove_member", groupname=groupname),
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

        return redirect(url_for('.group', groupname=groupname))

    for field_errors in sponsor_form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.group', groupname=groupname))


@bp.route('/group/<groupname>/members/remove', methods=['POST'])
@with_ipa()
def group_remove_member(ipa, groupname):
    group_or_404(ipa, groupname)
    form = RemoveGroupMemberForm()
    if form.validate_on_submit():
        username = form.username.data
        try:
            result = ipa.group_remove_member(groupname, o_user=username)
            raise_on_failed(result)
        except python_freeipa.exceptions.ValidationError as e:
            # e.message is a dict that we have to process ourselves for now:
            # https://github.com/opennode/python-freeipa/issues/24
            for error in e.message['member']['user']:
                flash(f"Unable to remove user {error[0]}: {error[1]}", "danger")
            return redirect(url_for('.group', groupname=groupname))
        flash_text = _(
            'You got it! %(username)s has been removed from %(groupname)s.',
            username=username,
            groupname=groupname,
        )
        flash(
            flash_text
            + undo_button(
                url_for(".group_add_member", groupname=groupname),
                "new_member_username",
                username,
                form.hidden_tag(),
            ),
            'success',
        )
        return redirect(url_for('.group', groupname=groupname))

    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, 'danger')
    return redirect(url_for('.group', groupname=groupname))


@bp.route('/group/<groupname>/sponsors/remove', methods=['POST'])
@with_ipa()
def group_remove_sponsor(ipa, groupname):
    group = Group(group_or_404(ipa, groupname))
    # Don't allow removing the last sponsor
    if len(group.sponsors) < 2:
        flash("Removing the last sponsor is not allowed.", "danger")
        return redirect(url_for('.group', groupname=groupname))
    # Only removing onelself from sponsors is allowed
    username = g.current_user.username
    try:
        result = ipa.group_remove_member_manager(groupname, o_user=username)
        raise_on_failed(result)
    except python_freeipa.exceptions.ValidationError as e:
        # e.message is a dict that we have to process ourselves for now:
        # https://github.com/opennode/python-freeipa/issues/24
        for error in e.message['membermanager']['user']:
            flash(f"Unable to remove user {error[0]}: {error[1]}", "danger")
        return redirect(url_for('.group', groupname=groupname))
    flash(
        _(
            'You got it! %(username)s is no longer a sponsor of %(groupname)s.',
            username=username,
            groupname=groupname,
        ),
        'success',
    )
    return redirect(url_for('.group', groupname=groupname))


@bp.route('/groups/')
@with_ipa()
def groups(ipa):
    groups = paginated_find(ipa, Group, fasgroup=True)
    return render_template('groups.html', groups=groups)
