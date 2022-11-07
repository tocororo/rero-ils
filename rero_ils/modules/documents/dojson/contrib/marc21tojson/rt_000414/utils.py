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

"""Rero-ils RT 000414 utils."""

from dojson import utils

SCHEMA_DOC = 'https://bib.rero.ch/schemas/documents/document-v0.0.1.json'
SCHEMA_ITEM = 'https://bib.rero.ch/schemas/items/item-v0.0.1.json'
SCHEMA_LOFI = \
    'https://bib.rero.ch/schemas/local_fields/local_field-v0.0.1.json'


def value_to_str(value):
    """Change GroupableOrderedDict values to string."""
    value_strings = []
    for val, data in value.iteritems(repeated=True):
        if val != '__order__':
            value_strings.append(f'${val} {data}')
    return ' '.join(value_strings)



def get_item(key, value):
    """Get Item.

    $D dépôt (sur 9 positions) --> location
    $F numéro de copie (1) --> ignorer
    $G dépôt temporaire --> temporary_location (n'existe en principe pas pour Charrat)
    $L nbre total de prêts --> legacy_checkout_count
    $V prix --> price
    $X classe d’item --> item_type
    $1 date de création de l’item --> ignorer (ou alors créer un operation_log)
    $6 code-barres --> barcode
    $9 Units --> enumerationAndChronology
    $a 1ère cote --> call_number
    $b 2ème cote --> second_call_number
    $o staff note --> note.content[if note.type:staff_note]
    $p public note --> note.content[if note.type:general_note]
    $q check in note --> note.content[if note.type:checkin_note]
    $r check out note --> note.content[if note.type:checkout_note]
    $s statut --> (n'existe en principe pas pour Charrat)
    $y url --> url
    $z date (à mettre obligatoirement lors de migration) --> ? ignorer
    """
    tags = {
        'd': {'tag': 'location', 'value': '{replace}'},
        'l': {'tag': 'legacy_checkout_count'},
        'v': {'tag': 'price'},
        'x': {'tag': 'item_type'},
        '6': {'tag': 'barcode', 'value': '{replace}'},
#        '9': {'tag': 'enumerationAndChronology', 'value': '{replace}'},
        'a': {'tag': 'call_number', 'value': '{replace}'},
        'b': {'tag': 'second_call_number', 'value': '{replace}'},
        'o': {'tag': 'note', 'value': 'staff_note'},
        'p': {'tag': 'note', 'value': 'general_note'},
        'q': {'tag': 'note', 'value': 'checkin_note'},
        'r': {'tag': 'note', 'value': 'checkout_note'},
        'y': {'tag': 'url', 'value': '{replace}'}
    }

    notes = []
    item = {'$schema': SCHEMA_ITEM}
    for tag, data in tags.items():
        for subfield_value in utils.force_list(value.get(tag, [])):
            if data['tag'] == 'location':
                item['location'] = {
                    '$ref':
                        f'https://bib.rero.ch/api/locations/{subfield_value}'
                }
            elif data['tag'] == 'item_type':
                item['item_type'] = {
                    '$ref':
                        f'https://bib.rero.ch/api/item_types/{subfield_value}'
                }
            elif data['tag'] == 'note':
                notes.append({
                    'type': data['value'],
                    'content': subfield_value
                })
            elif data['tag'] == 'price':
                item['price'] = float(subfield_value.replace(',', '.'))
            elif data['tag'] == 'legacy_checkout_count':
                item['legacy_checkout_count'] = int(subfield_value)
            else:
                item[data['tag']] = data['value'] \
                    .format(replace=subfield_value)
    if notes:
        item['note'] = notes
    item['organisation'] = {'$ref': 'https://bib.rero.ch/api/organisations/2'}
    item['library'] = {'$ref': 'https://bib.rero.ch/api/libraries/61'}
    item['type'] = 'standard'
    item['status'] = 'on_shelf'
    return item

