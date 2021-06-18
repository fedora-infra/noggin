import pytest

from noggin.utility.templates import format_nickname


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
                "href": "https://matrix.to/#/@username:matrix.org",
                "title": "Matrix on matrix.org",
                "name": "@username",
            },
        ),
        (
            "matrix://example.com/username",
            {
                "href": "https://matrix.to/#/@username:example.com",
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
