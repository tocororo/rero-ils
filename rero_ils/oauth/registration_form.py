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

"""OAuth registration form for Dex/institutional sign-up."""

from flask import current_app
from werkzeug.local import LocalProxy

_security = LocalProxy(lambda: current_app.extensions["security"])


def dex_registration_form(*args, **kwargs):
    """Registration form for OAuth users — password field removed."""

    class _DexRegistrationForm(_security.confirm_register_form):
        # OAuth users have no local password
        password = None
        recaptcha = None
        submit = None

    return _DexRegistrationForm(*args, **kwargs)
