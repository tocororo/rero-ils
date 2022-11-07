# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2021 RERO
# Copyright (C) 2021 UCLOUVAIN
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

"""rero-ils RT 000414 items.

poetry run dojson -l marcxml -d pjson -i data.xml do rt_000414_item_lofi
"""

from dojson import Overdo, utils

from .utils import SCHEMA_ITEM, SCHEMA_LOFI, get_item, value_to_str


class ItemOverdo(Overdo):
    """Specialized Overdo."""

    def do(self, blob, ignore_missing=True, exception_handlers=None):
        """Translate blob values and instantiate new model instance."""
        return super().do(
            blob,
            ignore_missing=ignore_missing,
            exception_handlers=exception_handlers
        )


marc21 = ItemOverdo()


@marc21.over('pid', '^001')
@utils.ignore_value
def marc21_to_pid(self, key, value):
    """Get pid.

    If 001 starts with 'REROILS:' save as pid.
    """
    value = value.strip().split(':')
    return value[1] if value[0] == 'REROILS' else None


@marc21.over('items', '^949')
@utils.for_each_value
@utils.ignore_value
def marc21_to_pid(self, key, value):
    """Item."""
    item = self.setdefault('items', [{}])[0]
    if item_data := get_item(key, value):
        item['$schema'] = SCHEMA_ITEM
        item['document'] ={
            '$ref': 'https://bib.rero.ch/api/documents/{document_pid}'
        }
        for tag, data in item_data.items():
            item[tag] = data
        self['items'][0] = item


@marc21.over('local_field_3', '^919')
@utils.for_each_value
@utils.ignore_value
def marc21_to_pid(self, key, value):
    """Local field 3."""
    items = self.setdefault('items', [{}])
    local_field = items[0].setdefault('local_fields', [{}])[0]
    local_field['$schema'] = SCHEMA_LOFI
    local_field['organisation'] = {
        '$ref': 'https://bib.rero.ch/api/organisations/2'
    }
    local_field['parent'] = {
        '$ref': 'https://bib.rero.ch/api/items/{parent_pid}'
    }
    fields = local_field.setdefault('fields', {})
    if field_3 := fields.get('field_3'):
        fields['field_3'] = [f'{field_3[0]} | {value_to_str(value)}']
    else:
        fields['field_3'] = [value_to_str(value)]
    local_field['fields'] = fields
    self['items'][0]['local_fields'] = [local_field]


@marc21.over('local_field_2', '^986')
@utils.for_each_value
@utils.ignore_value
def marc21_to_pid(self, key, value):
    """Local field 2."""
    items = self.setdefault('items', [{}])
    local_field = items[0].setdefault('local_fields', [{}])[0]
    local_field['$schema'] = SCHEMA_LOFI
    local_field['organisation'] = {
        '$ref': 'https://bib.rero.ch/api/organisations/2'
    }
    local_field['parent'] = {
        '$ref': 'https://bib.rero.ch/api/items/{parent_pid}'
    }
    fields = local_field.setdefault('fields',{})
    fields['field_2'] = [value_to_str(value)]
    local_field['fields'] = fields
    self['items'][0]['local_fields'] = [local_field]
