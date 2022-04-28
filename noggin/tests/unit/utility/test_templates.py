import pytest
from flask import current_app

from noggin.utility.templates import format_channel, format_nickname


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            "irc:/username",
            {
                "href": "irc://irc.libera.chat/username,isnick",
                "title": "IRC on irc.libera.chat",
                "name": "username",
            },
        ),
        (
            "irc://irc.unit.tests/username[m]",
            {
                "href": "irc://irc.unit.tests/username[m],isnick",
                "title": "IRC on irc.unit.tests",
                "name": "username[m]",
            },
        ),
        (
            "matrix:/username",
            {
                "href": (
                    "https://matrix.to/#/@username:fedora.im"
                    "?web-instance[element.io]=chat.fedoraproject.org"
                ),
                "title": "Matrix on fedora.im",
                "name": "@username",
            },
        ),
        (
            "matrix://unit.tests/username",
            {
                "href": (
                    "https://matrix.to/#/@username:unit.tests"
                    "?web-instance[element.io]=chat.fedoraproject.org"
                ),
                "title": "Matrix on unit.tests",
                "name": "@username:unit.tests",
            },
        ),
        (
            "username",
            {
                "href": "irc://irc.libera.chat/username,isnick",
                "title": "IRC on irc.libera.chat",
                "name": "username",
            },
        ),
        (
            "@username",
            {
                "href": "irc://irc.libera.chat/username,isnick",
                "title": "IRC on irc.libera.chat",
                "name": "username",
            },
        ),
    ],
)
def test_format_nickname(request_context, value, expected):
    expected_html = '<a href="{href}" title="{title}">{name}</a>'.format(**expected)
    assert str(format_nickname(value)) == expected_html


def test_format_nickname_no_matrixto_args(request_context):
    value = "matrix://unit.tests/username"
    name = "@username:unit.tests"
    title = "Matrix on unit.tests"
    href = "https://matrix.to/#/@username:unit.tests"
    expected_html = f'<a href="{href}" title="{title}">{name}</a>'
    current_app.config["CHAT_MATRIX_TO_ARGS"] = None
    assert str(format_nickname(value)) == expected_html


def test_format_nickname_invalid(request_context):
    with pytest.raises(ValueError) as e:
        format_nickname("invalid:/username")
        assert str(e) == "ValueError: Unsupported chat protocol: 'invalid'"


def test_format_nickname_invalid_with_config(app, request_context, mocker):
    mocker.patch.dict(
        app.config["CHAT_NETWORKS"], {"new-scheme": {"default_server": "unit.tests"}}
    )
    with pytest.raises(ValueError) as e:
        format_nickname("new-scheme:/username")
        assert str(e) == "ValueError: Can't parse 'new-scheme:/username'"


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            "irc:/channel",
            {
                "href": "irc://irc.libera.chat/channel",
                "title": "IRC on irc.libera.chat",
                "name": "#channel@irc.libera.chat",
            },
        ),
        (
            "irc:///channel",
            {
                "href": "irc://irc.libera.chat/channel",
                "title": "IRC on irc.libera.chat",
                "name": "#channel@irc.libera.chat",
            },
        ),
        (
            "irc://irc.unit.tests/#channel",
            {
                "href": "irc://irc.unit.tests/channel",
                "title": "IRC on irc.unit.tests",
                "name": "#channel@irc.unit.tests",
            },
        ),
        (
            "matrix:/channel",
            {
                "href": "https://matrix.to/#/#channel:fedora.im",
                "title": "Matrix on fedora.im",
                "name": "#channel:fedora.im",
            },
        ),
        (
            "matrix://unit.tests/#channel",
            {
                "href": "https://matrix.to/#/#channel:unit.tests",
                "title": "Matrix on unit.tests",
                "name": "#channel:unit.tests",
            },
        ),
        (
            "channel",
            {
                "href": "irc://irc.libera.chat/channel",
                "title": "IRC on irc.libera.chat",
                "name": "#channel@irc.libera.chat",
            },
        ),
        (
            "#channel",
            {
                "href": "irc://irc.libera.chat/channel",
                "title": "IRC on irc.libera.chat",
                "name": "#channel@irc.libera.chat",
            },
        ),
    ],
)
def test_format_channel(request_context, value, expected):
    expected_html = '<a href="{href}" title="{title}">{name}</a>'.format(**expected)
    assert str(format_channel(value)) == expected_html
