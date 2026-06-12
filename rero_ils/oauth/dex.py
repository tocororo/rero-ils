# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2024 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Dex OpenID OAuth provider for institutional authentication."""

from invenio_oauthclient.contrib.settings import OAuthSettingsHelper


class DexOAuthSettingsHelper(OAuthSettingsHelper):
    """Configuration helper for a Dex OpenID Connect provider."""

    def __init__(
        self,
        title="Dex OpenID",
        description="Connecting to Dex OpenID",
        icon="fa fa-university",
        base_url="http://127.0.0.1:5556",
    ):
        super().__init__(
            title=title,
            description=description,
            icon=icon,
            base_url=base_url,
            app_key="DEX_APP_CREDENTIALS",
            access_token_url=f"{base_url}/token",
            authorize_url=f"{base_url}/auth",
            access_token_method="POST",
            request_token_params={"scope": "openid email profile"},
            request_token_url=None,
            precedence_mask=None,
            signup_options=None,
            logout_url=None,
            hide_when=False,
        )
        self._handlers = dict(
            authorized_handler="invenio_oauthclient.handlers:authorized_signup_handler",
            disconnect_handler="invenio_oauthclient.handlers:disconnect_handler",
            signup_handler=dict(
                info=dex_account_info,
                info_serializer=dex_account_info_serializer,
                setup=dex_account_setup,
                view="invenio_oauthclient.handlers:signup_handler",
            ),
        )
        self._rest_handlers = dict(
            authorized_handler="invenio_oauthclient.handlers.rest:authorized_signup_handler",
            disconnect_handler="invenio_oauthclient.handlers.rest:disconnect_handler",
            signup_handler=dict(
                info=dex_account_info,
                info_serializer=dex_account_info_serializer,
                setup=dex_account_setup,
                view="invenio_oauthclient.handlers.rest:signup_handler",
            ),
            response_handler="invenio_oauthclient.handlers.rest:default_remote_response_handler",
            authorized_redirect_url="/",
            disconnect_redirect_url="/",
            signup_redirect_url="/",
            error_redirect_url="/",
        )

    def get_handlers(self):
        """Return Dex auth handlers."""
        return self._handlers

    def get_rest_handlers(self):
        """Return Dex auth REST handlers."""
        return self._rest_handlers


def dex_account_info(remote, resp):
    """Retrieve remote account information used to find local user."""
    user_info = remote.get("userinfo").data
    email = user_info.get("email", "")
    username = email.split("@")[0] if email else user_info.get("sub", "")
    full_name = user_info.get("name", "")

    return dict(
        user=dict(
            email=email,
            profile=dict(
                username=username,
                full_name=full_name,
            ),
        ),
        external_id=user_info.get("sub"),
        external_method="dex",
        active=True,
    )


def dex_account_info_serializer(remote, resp, **kwargs):
    """Serialize the account info response object."""
    return {
        "external_id": resp.get("sub"),
        "external_method": remote.name,
        "user": {
            "profile": {
                "full_name": resp.get("name", ""),
            },
        },
    }


def dex_account_setup(remote, token, resp):
    """Perform additional setup after user has been logged in via Dex."""
    from invenio_db import db

    user_info = remote.get("userinfo").data
    full_name = user_info.get("name", "")
    name_parts = full_name.split(" ", 1) if full_name else []
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    user = token.remote_account.user
    with db.session.begin_nested():
        profile = dict(user.user_profile or {})
        if first_name:
            profile["first_name"] = first_name
        if last_name:
            profile["last_name"] = last_name
        user.user_profile = profile
        db.session.merge(user)
