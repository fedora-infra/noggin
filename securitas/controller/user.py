from flask import flash, redirect, render_template, session, url_for
import python_freeipa

from securitas import app
from securitas.form.edit_user import EditUserForm
from securitas.representation.group import Group
from securitas.representation.user import User
from securitas.utility import with_ipa, user_or_404
from securitas.form.password_reset import PasswordResetForm


@app.route('/user/<username>/')
@with_ipa(app, session)
def user(ipa, username):
    user = User(user_or_404(ipa, username))
    # As a speed optimization, we make two separate calls.
    # Just doing a group_find (with all=True) is super slow here, with a lot of
    # groups.
    groups = [Group(g) for g in ipa.group_find(user=username, all=False)['result']]
    managed_groups = [
        Group(g)
        for g in ipa.group_find(membermanager_user=username, all=False)['result']
    ]
    return render_template(
        'user.html', user=user, groups=groups, managed_groups=managed_groups
    )


@app.route('/user/<username>/edit/', methods=['GET', 'POST'])
@with_ipa(app, session)
def user_edit(ipa, username):
    # TODO: Maybe make this a decorator some day?
    if session.get('securitas_username') != username:
        flash('You do not have permission to edit this account.', 'danger')
        return redirect(url_for('user', username=username))

    user = User(user_or_404(ipa, username))
    form = EditUserForm(obj=user)
    password_reset_form = PasswordResetForm()

    if form.validate_on_submit():
        try:
            ipa.user_mod(
                username,
                first_name=form.firstname.data,
                last_name=form.lastname.data,
                full_name='%s %s' % (form.firstname.data, form.lastname.data),
                display_name='%s %s' % (form.firstname.data, form.lastname.data),
                mail=form.mail.data,
                ipasshpubkey=form.sshpubkeys.data,
                fasircnick=form.ircnick.data,
                faslocale=form.locale.data,
                fastimezone=form.timezone.data,
                fasgpgkeyid=form.gpgkeys.data,
                fasgithubusername=form.github.data.lstrip('@'),
                fasgitlabusername=form.gitlab.data.lstrip('@'),
                fasrhbzemail=form.rhbz_mail.data,
            )
        except python_freeipa.exceptions.BadRequest as e:
            if e.message == 'no modifications to be performed':
                form.errors['non_field_errors'] = [e.message]
            else:
                app.logger.error(
                    f'An error happened while editing user {username}: {e.message}'
                )
                form.errors['non_field_errors'] = [e.message]
        else:
            flash('Profile has been succesfully updated.', 'success')
            return redirect(url_for('user', username=username))

    # if the form has errors, we don't want to add new fields. otherwise,
    # more fields will show up with every validation error
    if not form.errors:
        # Append 2 empty entries at the bottom of the gpgkeys fieldlist
        for i in range(2):
            form.gpgkeys.append_entry()
            form.sshpubkeys.append_entry()

    return render_template(
        'user-edit.html', user=user, form=form, password_reset_form=password_reset_form
    )
