from contextlib import contextmanager


class FormError(Exception):
    def __init__(self, field, message):
        self.field = field
        self.message = message

    def populate_form(self, form):
        field = form[self.field]
        field.errors.append(self.message)


@contextmanager
def handle_form_errors(form):
    """Handle form errors by raising exceptions.

    The point of this context manager is to let controller developers create form errors by raising
    exceptions instead of setting variables. This is particularly useful when you are making
    multiple API calls in a row and handling exceptions separately: instead of doing nested
    ``try..except..else`` statements they would have non-nested code raising exceptions.

    For example, without this function you would have something similar to::

        if form.validate_on_submit():
            try:
                api_call_1()
            except UserError as e:
                form.user.errors.append(e.msg)
            else:
                try:
                    api_call_2()
                except PasswordError as e:
                    form.password.errors.append(e.msg)
                else:
                    try:
                        api_call_3()
                    except GenericError as e:
                        form.non_field_errors.errors.append(e.msg)
                    else:
                        flash("Success!")
                        return redirect("/")
        return render_template(..., form=form)

    Every API call causes an additional level of nesting because the code must fall through the
    initial ``if`` statement to reach the ``render_template`` call. With this function this could be
    rewritten as::

        if form.validate_on_submit():
            with handle_form_errors(form):
                try:
                    api_call_1()
                except UserError as e:
                    raise FormError("user", e.msg)
                try:
                    api_call_2()
                except PasswordError as e:
                    raise FormError("password", e.msg)
                try:
                    api_call_3()
                except GenericError as e:
                    raise FormError("non_field_errors", e.msg)
                flash("Success!")
                return redirect("/")
        return render_template(..., form=form)

    This code does not nest more on each API call, which is (arguably) clearer as the number of
    necessary API call increases.

    Args: form (wtforms.Form): The form that errors should be stored to
    """
    try:
        yield
    except FormError as e:
        e.populate_form(form)
