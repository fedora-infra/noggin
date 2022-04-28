from contextlib import contextmanager
from urllib import parse

import pyotp
from bs4 import BeautifulSoup
from flask import get_flashed_messages, template_rendered


def assert_redirects_with_flash(
    response, expected_url, expected_message, expected_category
):
    assert response.status_code == 302, f"Response code was {response.status_code}"
    assert (
        response.location == expected_url
    ), f"Expected URL {expected_url}, got {response.location}"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) > 0, "No flash message was set"
    assert len(messages) == 1, "More than one flash message were set"
    category, message = messages[0]
    assert (
        message == expected_message
    ), f"\nExpected message: {expected_message}\nActual message:   {message}"
    assert (
        category == expected_category
    ), f"\nExpected category: {expected_category}\nActual category:   {category}"


def assert_form_field_error(response, field_name, expected_message):
    assert response.status_code == 200
    page = BeautifulSoup(response.data, 'html.parser')
    field = page.select_one(f"input[name='{field_name}']")
    assert field is not None, "Can't find the field"
    assert 'is-invalid' in field['class']
    invalidfeedback = field.find_next('div', class_='invalid-feedback')
    message = invalidfeedback.get_text(strip=True)
    assert (
        message == expected_message
    ), f"\nExpected message: {expected_message!r}\nActual message:   {message!r}"


def assert_form_generic_error(response, expected_message):
    assert response.status_code == 200
    page = BeautifulSoup(response.data, 'html.parser')
    error_message = page.select_one("#formerrors .text-danger")
    assert error_message is not None
    message = error_message.get_text(strip=True)
    assert (
        message == expected_message
    ), f"\nExpected message: {expected_message!r}\nActual message:   {message!r}"


def otp_secret_from_page(page):
    """
    Takes a page with an OTP QR code on it, and returns the secret
    """
    return otp_secret_from_uri(page.select_one("#otp-uri").attrs['value'])


def otp_secret_from_uri(uri):
    return parse.parse_qs(parse.urlparse(uri).query)['secret'][0]


def get_otp(secret):
    """
    Return an TOTP OTP from the given secret
    """
    totp = pyotp.TOTP(secret, 6)
    return totp.now()


# https://flask.palletsprojects.com/en/1.1.x/signals/#subscribing-to-signals
@contextmanager
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)
