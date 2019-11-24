from flask import Flask, render_template, request, flash, redirect, url_for, make_response, session

from securitas.ipa import maybe_ipa_admin_session, maybe_ipa_login, maybe_ipa_session

app = Flask(__name__)
app.config.from_envvar('SECURITAS_CONFIG_PATH')

@app.context_processor
def inject_global_template_vars():
    ipa = maybe_ipa_session(app)
    # TODO: move project out to config var
    return dict(
        project="The Fedora Project",
        ipa=ipa,
        current_user=ipa.user_find(whoami=True) if ipa else None
    )

@app.route('/')
def root():
    ipa = maybe_ipa_session(app)
    username = session.get('securitas_username_insecure')
    if ipa and username:
        return redirect(url_for('user', username=username))
    return render_template('index.html')

@app.route('/logout')
def logout():
    ipa = maybe_ipa_session(app)
    if ipa:
        ipa.logout()
    session.clear()
    return redirect(url_for('root'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        flash('Please provide both a username and a password.', 'red')
        return redirect(url_for('root'))

    # This call will set the cookie itself, we don't have to.
    ipa = maybe_ipa_login(app, username, password)
    if ipa:
        flash('Welcome, %s!' % username)
        return redirect(url_for('user', username=username))
    flash('Could not log in to the IPA server.', 'red')
    return redirect(url_for('root'))

@app.route('/register', methods=['POST'])
def register():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    if not all([first_name, last_name, username, password, password_confirm]):
        flash('Please fill in all fields to register an account.', 'red')
        return redirect(url_for('root'))
    if password != password_confirm:
        flash('Password and confirmation did not match.', 'red')
        return redirect(url_for('root'))
    ipa_admin = maybe_ipa_admin_session(app)
    if not ipa_admin:
        flash('Internal error: Could not obtain admin session. Try again later.', 'red')
        return redirect(url_for('root'))
    add = ipa_admin.user_add(
        username,
        first_name,
        last_name,
        '%s %s' % (first_name, last_name), # TODO ???
        user_password=password,
        login_shell='/bin/bash')
    print(add)
    flash(
        'Congratulations, you now have an account! Go ahead and sign in to proceed.',
        'green')
    return redirect(url_for('root'))    
        
    
@app.route('/user/<username>/')
def user(username):
    ipa = maybe_ipa_session(app)
    if ipa:
        user = ipa.user_show(username)
        return render_template('user.html', user=user)
    else:
        flash('Please log in to continue.', 'orange')
        return redirect(url_for('root'))
