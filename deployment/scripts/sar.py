#!/usr/bin/env python

import json

import click
from python_freeipa.client_legacy import ClientLegacy


def print_human_readable_format(sar_data):
    """
    Print user data in human readable format.

    Args:
        sar_data (dict): User data to be printed.
    """
    header_start = "==========>"
    header_stop = "<=========="
    footer = "======================================================="
    chapter_start = "---->"
    chapter_stop = "<----"

    click.echo(
        "\n{} User account data for: {} {}\n".format(
            header_start, sar_data["username"], header_stop
        )
    )
    click.echo("mail: {}".format(sar_data["mail"]))
    click.echo("username: {}".format(sar_data["username"]))
    click.echo("givenname: {}".format(sar_data["givenname"]))
    click.echo("surname: {}".format(sar_data["surname"]))
    click.echo("home: {}".format(sar_data["homedirectory"]))
    click.echo("ircnick: {}".format(sar_data["ircnick"]))

    click.echo("\n{} groups: {}".format(chapter_start, chapter_stop))
    for idx, group in enumerate(sar_data["groups"], 1):
        click.echo("Group no {}: {}".format(idx, group))
    click.echo("\n{}".format(footer))


@click.command()
@click.option(
    '--username',
    envvar='SAR_USERNAME',
    required=True,
    help='The username for which sar data should be gathered.',
)
@click.option(
    '--server',
    envvar='IPA_SERVER_ADDRESS',
    required=True,
    help='The address for the FreeIPA server to query. e.g ipa.example.com',
)
@click.option(
    '--sar-admin-username',
    envvar='SAR_ADMIN_USERNAME',
    required=True,
    help='The admin username used to gather SAR data.',
)
@click.option(
    '--sar-admin-password',
    envvar='SAR_ADMIN_PASSWORD',
    required=True,
    help='The password for the admin account.',
)
@click.option(
    '--human-readable',
    default=False,
    is_flag=True,
    help='Print user data in human readable format.'
    ' The script defaults to JSON output.',
)
@click.version_option(message='%(version)s')
def get_user_data(
    username, sar_admin_username, sar_admin_password, human_readable, server
):
    """Get username SAR data."""
    ipa = ClientLegacy(host=server, verify_ssl=False)
    ipa.login(sar_admin_username, sar_admin_password)

    sar_response = ipa.user_show(username=username)

    sar_data = {}
    sar_data["username"] = sar_response["uid"][0]
    sar_data["mail"] = sar_response["mail"][0]
    sar_data["homedirectory"] = sar_response["homedirectory"][0]
    sar_data["surname"] = sar_response["sn"][0]
    sar_data["givenname"] = sar_response["givenname"][0]
    sar_data["ircnick"] = sar_response["fasircnick"][0]
    sar_data["groups"] = sar_response["memberof_group"]

    if human_readable:
        print_human_readable_format(sar_data)
    else:
        click.echo(json.dumps(sar_data, sort_keys=True))


if __name__ == '__main__':
    get_user_data()
