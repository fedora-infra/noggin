from bs4 import BeautifulSoup
from flask import get_flashed_messages


def assert_redirects_with_flash(
    response, expected_url, expected_message, expected_category
):
    assert response.status_code == 302
    assert (
        response.location == f"http://localhost{expected_url}"
    ), f"Expected URL http://localhost{expected_url}, got {response.location}"
    messages = get_flashed_messages(with_categories=True)
    assert len(messages) == 1
    category, message = messages[0]
    assert message == expected_message
    assert category == expected_category


def assert_form_field_error(response, field_name, expected_message):
    assert response.status_code == 200
    page = BeautifulSoup(response.data, 'html.parser')
    field = page.select_one(f"input[name='{field_name}']")
    assert 'is-invalid' in field['class']
    invalidfeedback = field.find_next('div', class_='invalid-feedback')
    assert invalidfeedback.get_text(strip=True) == expected_message


def assert_form_generic_error(response, expected_message):
    assert response.status_code == 200
    page = BeautifulSoup(response.data, 'html.parser')
    error_message = page.select_one("#formerrors .text-danger")
    assert error_message is not None
    assert error_message.get_text(strip=True) == expected_message
