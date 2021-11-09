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
            "irc://irc.example.com/username[m]",
            {
                "href": "irc://irc.example.com/username[m],isnick",
                "title": "IRC on irc.example.com",
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
            "matrix://example.com/username",
            {
                "href": (
                    "https://matrix.to/#/@username:example.com"
                    "?web-instance[element.io]=chat.fedoraproject.org"
                ),
                "title": "Matrix on example.com",
                "name": "@username:example.com",
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
    value = "matrix://example.com/username"
    name = "@username:example.com"
    title = "Matrix on example.com"
    href = "https://matrix.to/#/@username:example.com"
    expected_html = f'<a href="{href}" title="{title}">{name}</a>'
    current_app.config["CHAT_MATRIX_TO_ARGS"] = None
    assert str(format_nickname(value)) == expected_html


def test_format_nickname_invalid(request_context):
    with pytest.raises(ValueError) as e:
        format_nickname("invalid:/username")
        assert str(e) == "ValueError: Unsupported chat protocol: 'invalid'"


def test_format_nickname_invalid_with_config(app, request_context, mocker):
    mocker.patch.dict(
        app.config["CHAT_NETWORKS"], {"new-scheme": {"default_server": "example.com"}}
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
            "irc://irc.example.com/#channel",
            {
                "href": "irc://irc.example.com/channel",
                "title": "IRC on irc.example.com",
                "name": "#channel@irc.example.com",
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
            "matrix://example.com/#channel",
            {
                "href": "https://matrix.to/#/#channel:example.com",
                "title": "Matrix on example.com",
                "name": "#channel:example.com",
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
