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

"""Define relation between records and buckets."""

from __future__ import absolute_import

from invenio_db import db
from invenio_pidstore.models import RecordIdentifier
from invenio_records.models import RecordMetadataBase


class ContributionIdentifier(RecordIdentifier):
    """Sequence generator for Document identifiers."""

    __tablename__ = 'contribution_id'
    __mapper_args__ = {'concrete': True}

    recid = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        primary_key=True,
        autoincrement=True,
    )


class ContributionMetadata(db.Model, RecordMetadataBase):
    """Contribution record metadata."""

    __tablename__ = 'contribution_metadata'


class ContributionType:
    """Class holding all availabe contribution types."""

    ORGANISATION = 'bf:Organisation'
    PERSON = 'bf:Person'


class ContributionUpdateAction:
    """Class holding all availabe agent record creation actions."""

    REPLACE = 'replace'
    UPTODATE = 'uptodate'
    ERROR = 'error'
