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


class AcqOrderIdentifier(RecordIdentifier):
    """Sequence generator for acquisition order identifiers."""

    __tablename__ = 'acq_order_id'
    __mapper_args__ = {'concrete': True}

    recid = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        primary_key=True, autoincrement=True,
    )


class AcqOrderMetadata(db.Model, RecordMetadataBase):
    """AcqOrder record metadata."""

    __tablename__ = 'acq_order_metadata'


class AcqOrderType:
    """Type of acquisition order."""

    MONOGRAPH = 'monograph'
    MONOGRAPHIC_SET = 'monographic_set'
    SERIAL = 'serial'
    STANDING_ORDER = 'standing_order'
    PLANNED_ORDER = 'planned_order'
    MULTI_VOLUME = 'multi_volume'


class AcqOrderStatus:
    """Available statuses for an acquisition order."""

    CANCELLED = 'cancelled'
    ORDERED = 'ordered'
    PENDING = 'pending'
    PARTIALLY_RECEIVED = 'partially_received'
    RECEIVED = 'received'


class AcqOrderNoteType:
    """Type of acquisition order note."""

    STAFF = 'staff_note'
    VENDOR = 'vendor_note'
