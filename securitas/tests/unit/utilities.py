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
