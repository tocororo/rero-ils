# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
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

"""Common pytest fixtures and plugins."""


from datetime import datetime

import pytest
from invenio_accounts.ext import hash_password
from invenio_accounts.models import User
from invenio_search import current_search_client


@pytest.fixture(scope='function')
def user_with_profile(db):
    """Create a simple invenio user with a profile."""
    with db.session.begin_nested():
        user = User(
            email='user_with_profile@test.com',
            password=hash_password('123456'),
            profile=dict(), active=True)
        db.session.add(user)
        profile = user.profile
        profile.birth_date = datetime(1990, 1, 1)
        profile.first_name = 'User'
        profile.last_name = 'With Profile'
        profile.city = 'Nowhere'
        profile.username = 'user_with_profile'
        db.session.merge(user)
    db.session.commit()
    user.password_plaintext = '123456'
    return user


@pytest.fixture(scope='function')
def user_without_email(db):
    """Create a simple invenio user without email."""
    with db.session.begin_nested():
        user = User(
            password=hash_password('123456'),
            profile=dict(), active=True)
        db.session.add(user)
        profile = user.profile
        profile.birth_date = datetime(1990, 1, 1)
        profile.first_name = 'User'
        profile.last_name = 'With Profile'
        profile.city = 'Nowhere'
        profile.username = 'user_without_email'
        db.session.merge(user)
    db.session.commit()
    user.password_plaintext = '123456'
    return user


@pytest.fixture(scope='module')
def create_app():
    """Create test app."""
    # from invenio_app.factory import create_ui
    # create_ui
    from invenio_app.factory import create_ui

    return create_ui


@pytest.fixture()
def ils_record():
    """Ils Record test record."""
    yield {
        'pid': 'ilsrecord_pid',
        'name': 'IlsRecord Name',
    }


@pytest.fixture()
def ils_record_2():
    """Ils Record test record 2."""
    yield {
        'pid': 'ilsrecord_pid_2',
        'name': 'IlsRecord Name 2',
    }


@pytest.fixture(scope='module')
def es_default_index(es):
    """ES default index."""
    current_search_client.indices.create(
        index='records-record-v1.0.0',
        body={
            'mappings': {
                'record-v1.0.0': {
                    'properties': {
                        'pid': {'type': 'keyword'}
                    }
                }
            }
        },
        ignore=[400]
    )
    yield es
    current_search_client.indices.delete(
        index='records-record-v1.0.0',
        ignore=[400, 404]
    )
