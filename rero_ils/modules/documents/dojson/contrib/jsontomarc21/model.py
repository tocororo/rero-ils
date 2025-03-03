# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2021 RERO
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

"""RERO-ILS to MARC21 model definition."""


from dojson import utils
from dojson.contrib.to_marc21.model import Underdo
from flask import current_app
from flask_babelex import gettext as translate
from invenio_db import db

from rero_ils.modules.contributions.api import Contribution
from rero_ils.modules.documents.utils import display_alternate_graphic_first
from rero_ils.modules.documents.views import create_title_responsibilites
from rero_ils.modules.holdings.api import Holding, HoldingsSearch
from rero_ils.modules.items.api import Item, ItemsSearch
from rero_ils.modules.libraries.api import Library
from rero_ils.modules.locations.api import Location
from rero_ils.modules.organisations.api import Organisation


def replace_contribution_sources(contribution, source_order):
    """Prepare contributions data from sources.

    :param contribution: contribution to use.
    :source_order: Source order to use to get the informations.
    :returns: contribution agent with localized values.
    """
    def set_value(data, old_data, key):
        """Set new data value."""
        value = data.get(key)
        if not old_data.get(key) and value:
            old_data[key] = value
        return old_data

    refs = []
    agent = contribution.get('agent')
    for source in source_order:
        source_data = agent.get(source, {})
        if source_data:
            refs.append({
                'source': source,
                'pid': source_data.get("pid")
            })
            for key in ['bf:Agent', 'preferred_name', 'numeration',
                        'qualifier', 'date_of_birth', 'date_of_death',
                        'subordinate_unit', 'conference', 'conference_number',
                        'conference_date', 'conference_place']:
                agent = set_value(source_data, agent, key)
            agent.pop(source)
    agent['refs'] = refs
    if 'bf:Agent' in agent:
        agent['type'] = agent.pop('bf:Agent')
    contribution['agent'] = agent
    return contribution


def get_holdings_items(document_pid, organisation_pids=None, library_pids=None,
                       location_pids=None):
    """Create Holding and Item informations.

    :param document_pid: document pid to use for holdings search
    :param organisation_pids: Which organisations items to add.
    :param library_pids: Which from libraries items to add.
    :param location_pids: Which from locations items to add.

    :returns: list of holding informations with associated organisation,
              library and location pid, name informations.
    """
    def get_name(resource, pid):
        """Get name from resource.

        The name will be cached.
        :param resource: Resource class to use.
        :param pid: Pid for the resource to get the name from.
        :returns: name from the resource
        """
        data = resource.get_record_by_pid(pid)
        if data:
            return data.get('name')

    results = []
    if document_pid:
        holding_pids = Holding.get_holdings_pid_by_document_pid(
            document_pid=document_pid,
            with_masked=False
        )

        holding_pids = list(holding_pids)
        organisations = {}
        libraries = {}
        locations = {}
        query = HoldingsSearch().filter('terms', pid=holding_pids)
        if organisation_pids:
            query = query.filter({
                'terms': {'organisation.pid': organisation_pids}})
        if library_pids:
            query = query.filter({
                'terms': {'library.pid': library_pids}})
        if location_pids:
            query = query.filter({
                'terms': {'location.pid': location_pids}})
        for hit in query.scan():
            holding = hit.to_dict()
            organisation_pid = hit.organisation.pid
            if organisation_pid not in organisations:
                organisations[organisation_pid] = get_name(Organisation,
                                                           organisation_pid)
            library_pid = hit.library.pid
            if library_pid not in libraries:
                libraries[library_pid] = get_name(Library, library_pid)
            location_pid = hit.location.pid
            if location_pid not in locations:
                locations[location_pid] = get_name(Location, location_pid)

            result = {
                'organisation': {
                    'pid': organisation_pid,
                    'name': organisations[organisation_pid]
                },
                'library': {
                    'pid': library_pid,
                    'name': libraries[library_pid]
                },
                'location': {
                    'pid': location_pid,
                    'name': locations[location_pid]
                },
                'holdings': {
                    'call_number': holding.get('call_number'),
                    'second_call_number': holding.get('second_call_number'),
                    'enumerationAndChronology': holding.get(
                        'enumerationAndChronology'),
                    'electronic_location': holding.get(
                        'electronic_location', []),
                    'notes': holding.get('notes', []),
                    'supplementaryContent': holding.get(
                        'supplementaryContent'),
                    'index': holding.get('index'),
                    'missing_issues': holding.get('missing_issues'),
                }
            }
            if hit.holdings_type == 'standard':
                item_pids = Item.get_items_pid_by_holding_pid(
                    hit.pid,
                    with_masked=False
                )
                item_hits = ItemsSearch() \
                    .filter('terms', pid=list(item_pids)) \
                    .scan()
                for item_hit in item_hits:
                    item_data = item_hit.to_dict()
                    item_result = result
                    item_result['item'] = {
                        'barcode': item_data.get('barcode'),
                        'all_number': item_data.get('all_number'),
                        'second_call_number': item_data.get(
                            'second_call_number'),
                        'enumerationAndChronology': item_data.get(
                            'enumerationAndChronology'),
                        'url': item_data.get('url'),
                        'notes': item_data.get('notes', []),
                    }
                    results.append(item_result)
            else:
                results.append(result)
    return results


ORDER = ['leader', 'pid', 'fixed_length_data_elements',
         'identifiedBy', 'title_responsibility', 'provisionActivity',
         'copyrightDate', 'physical_description', 'contribution', 'type',
         'holdings_items']
LEADER = '00000cam a2200000zu 4500'


class ToMarc21Overdo(Underdo):
    """Specialized Overdo."""

    responsibility_statement = {}

    def do(self, blob, language='en', ignore_missing=True,
           exception_handlers=None, with_holdings_items=False,
           organisation_pids=None, library_pids=None, location_pids=None):
        """Translate blob values and instantiate new model instance.

        Raises ``MissingRule`` when no rule matched and ``ignore_missing``
        is ``False``.

        :param blob: ``dict``-like object on which the matching rules are
                     going to be applied.
        :param ignore_missing: Set to ``False`` if you prefer to raise
                               an exception ``MissingRule`` for the first
                               key that it is not matching any rule.
        :param exception_handlers: Give custom exception handlers to take care
                                   of non-standard codes that are installation
                                   specific.
        :param with_holdings_items: Add holding, item information in field 949
                                    to the result (attention time consuming).
        :param organisation_pids: Which organisations items to add.
        :param library_pids: Which libraries items to add.
        :param location_pids: Which locations items to add.):
        :param language: Language to use.
        """
        # TODO: real leader
        self.language = language
        blob['leader'] = LEADER
        # create fixed_length_data_elements for 008
        # TODO: add 008/00-05  Date entered on file
        fixed_data = '000000|||||||||xx#|||||||||||||||||||||c'
        provision_activity = blob.get('provisionActivity', [])
        for p_activity in provision_activity:
            if p_activity.get('type') == 'bf:Publication':
                end_date = str(p_activity.get('endDate', ''))
                if end_date:
                    fixed_data = fixed_data[:11] + end_date + fixed_data[15:]
                start_date = str(p_activity.get('startDate', ''))
                if start_date:
                    fixed_data = fixed_data[:7] + start_date + fixed_data[11:]
                    break
        language = utils.force_list(blob.get('language'))
        if language:
            language = language[0].get('value')
            fixed_data = fixed_data[:35] + language + fixed_data[38:]
        blob['fixed_length_data_elements'] = fixed_data

        # Add responsibilityStatement to title
        if blob.get('title'):
            blob['title_responsibility'] = {
                'titles': blob.get('title', {}),
                'responsibility': ' ; '.join(create_title_responsibilites(
                    blob.get('responsibilityStatement', [])
                ))
            }
        # Fix ContributionsSearch
        order = current_app.config.get(
            'RERO_ILS_CONTRIBUTIONS_LABEL_ORDER', [])
        source_order = order.get(
            self.language,
            order.get(order['fallback'], [])
        )
        contributions = blob.get('contribution', [])
        for contribution in contributions:
            if ref := contribution['agent'].get('$ref'):
                agent, _ = Contribution.get_record_by_ref(ref)
                if agent:
                    db.session.commit()
                    contribution['agent'] = agent
                    replace_contribution_sources(
                        contribution=contribution,
                        source_order=source_order
                    )

        if with_holdings_items:
            # add holdings items informations
            get_holdings_items
            blob['holdings_items'] = get_holdings_items(
                document_pid=blob.get('pid'),
                organisation_pids=organisation_pids,
                library_pids=library_pids,
                location_pids=location_pids
            )

        # Physical Description
        physical_description = {}
        extent = blob.get('extent')
        durations = ', '.join(blob.get('duration', []))
        if extent:
            if durations:
                if f'({durations})' in extent:
                    physical_description['extent'] = extent
                else:
                    physical_description['extent'] = f'{extent} ({durations})'
            else:
                physical_description['extent'] = extent
        note = blob.get('note', [])
        other_physical_details = []
        for value in note:
            if value['noteType'] == 'otherPhysicalDetails':
                other_physical_details.append(value['label'])
        if not other_physical_details:
            for value in blob.get('productionMethod', []):
                other_physical_details.append(translate(value))
            for value in blob.get('illustrativeContent', []):
                other_physical_details.append(value)
            for value in blob.get('colorContent', []):
                other_physical_details.append(translate(value))
        if other_physical_details:
            physical_description['other_physical_details'] = \
                ' ; '.join(other_physical_details)
        accompanying_material = ' ; '.join(
            [v.get('label') for v in note
                if v['noteType'] == 'accompanyingMaterial']
        )
        if accompanying_material:
            physical_description['accompanying_material'] = \
                accompanying_material
        dimensions = blob.get('dimensions', [])
        book_formats = blob.get('bookFormat', [])
        upper_book_formats = [v.upper() for v in book_formats]
        new_dimensions = []
        for dimension in dimensions:
            try:
                index = upper_book_formats.index(dimension.upper())
                new_dimensions.append(book_formats[index])
                del book_formats[index]
            except ValueError:
                new_dimensions.append(dimension)
        for book_format in book_formats:
            new_dimensions.append(book_format)
        if new_dimensions:
            physical_description['dimensions'] = ' ; '.join(new_dimensions)

        if physical_description:
            blob['physical_description'] = physical_description

        # Add order
        keys = {}
        for key, value in blob.items():
            count = 1
            if isinstance(value, (list, set, tuple)):
                count = len(value)
            keys.setdefault(key, count-1)
            keys[key] += 1
        order = []
        for key in ORDER:
            for count in range(0, keys.get(key, 0)):
                order.append(key)
        blob['__order__'] = order
        result = super().do(
            blob,
            ignore_missing=ignore_missing,
            exception_handlers=exception_handlers
        )
        return result


def add_value(result, sub_tag, value):
    """Add value with tag to result."""
    if value:
        result.setdefault('__order__', []).append(sub_tag)
        result[sub_tag] = value
    return result


def add_values(result, sub_tag, values):
    """Add values with tag to result."""
    if values:
        for count in range(len(values)):
            result.setdefault('__order__', []).append(sub_tag)
        result[sub_tag] = values
    return result


to_marc21 = ToMarc21Overdo()


@to_marc21.over('leader', '^leader')
def reverse_leader(self, key, value):
    """Reverse - leader."""
    assert len(value) == 24
    return value


@to_marc21.over('001', '^pid')
def reverse_pid(self, key, value):
    """Reverse - pid."""
    return [value]


@to_marc21.over('008', '^fixed_length_data_elements')
def reverse_fixed_length_data_elements(self, key, value):
    """Reverse - fixed length data elements."""
    return [value]


@to_marc21.over('02X', '^identifiedBy')
@utils.reverse_for_each_value
@utils.ignore_value
def reverse_identified_by(self, key, value):
    """Reverse - identified by."""
    status = value.get('status')
    qualifier = value.get('qualifier')
    identified_by_type = value['type']
    identified_by_value = value['value']
    result = {}
    if identified_by_type == 'bf:Isbn':
        subfield = 'a'
        if status:
            subfield = 'z'
        result['__order__'] = [subfield]
        result[subfield] = identified_by_value
        if qualifier:
            result['__order__'].append('q')
            result['q'] = qualifier
        self.append(('020__', utils.GroupableOrderedDict(result)))
    return None


@to_marc21.over('245', '^title_responsibility')
@utils.ignore_value
def reverse_title(self, key, value):
    """Reverse - title."""
    def get_part(parts, new_parts):
        """Create part list."""
        for part in new_parts:
            part_numbers = []
            for part_number in part.get('partNumber', []):
                language = part_number.get('language', 'default')
                if display_alternate_graphic_first(language):
                    part_numbers.insert(0, part_number['value'])
                else:
                    part_numbers.append(part_number['value'])
            part_names = []
            for part_name in part.get('partName', []):
                language = part_name.get('language', 'default')
                if display_alternate_graphic_first(language):
                    part_names.insert(0, part_name['value'])
                else:
                    part_names.append(part_name['value'])
            parts.append({
                'part_number': '. '.join(part_numbers),
                'part_name': '. '.join(part_names)
            })
        return parts

    result = None
    titles = value.get('titles')
    responsibility = value.get('responsibility')
    main_titles = []
    sub_titles = []
    main_titles_parallel = []
    sub_titles_parallel = []
    parts = []
    for title in titles:
        if title.get('type') == 'bf:Title':
            for main_title in title.get('mainTitle'):
                if display_alternate_graphic_first(
                        main_title.get('language', 'default')):
                    main_titles.insert(0, main_title['value'])
                else:
                    main_titles.append(main_title['value'])
            for sub_title in title.get('subtitle', []):
                if display_alternate_graphic_first(
                        sub_title.get('language', 'default')):
                    sub_titles.insert(0, sub_title['value'])
                else:
                    sub_titles.append(sub_title['value'])
        if title.get('type') == 'bf:ParallelTitle':
            for main_title in title.get('mainTitle'):
                if display_alternate_graphic_first(
                        main_title.get('language', 'default')):
                    main_titles_parallel.insert(0, main_title['value'])
                else:
                    main_titles_parallel.append(main_title['value'])
            for sub_title in title.get('subtitle', []):
                if display_alternate_graphic_first(
                        sub_title.get('language', 'default')):
                    sub_titles_parallel.insert(0, sub_title['value'])
                else:
                    sub_titles_parallel.append(sub_title['value'])
        parts = get_part(parts, title.get('part', []))

    result = {
        '__order__': ['a'],
        '$ind1': '0',
        'a': '. '.join(main_titles)
    }
    if sub_titles:
        result['__order__'].append('b')
        result['b'] = '. '.join(sub_titles)
    if main_titles_parallel:
        if result.get('b'):
            result['b'] += f' = {". ".join(main_titles_parallel)}'
        else:
            result['__order__'].append('b')
            result['b'] = '. '.join(main_titles_parallel)
    if sub_titles_parallel:
        if result.get('b'):
            result['b'] += f' : {". ".join(sub_titles_parallel)}'
        else:
            result['__order__'].append('b')
            result['b'] = '. '.join(sub_titles_parallel)
    if responsibility:
        result['__order__'].append('c')
        result['c'] = responsibility
    for part in parts:
        part_number = part.get('part_number')
        if part_number:
            result['__order__'].append('n')
            result.setdefault('n', [])
            result['n'].append(part_number)
        part_name = part.get('part_name')
        if part_name:
            result['__order__'].append('p')
            result.setdefault('p', [])
            result['p'].append(part_name)

    return result or None


@to_marc21.over('264', '^(provisionActivity|copyrightDate)')
@utils.reverse_for_each_value
@utils.ignore_value
def reverse_title(self, key, value):
    """Reverse - provisionActivity."""
    # Pour chaque objet de "provisionActivity" (répétitif), créer une 264 :
    # * si type=bf:Publication, ind2=1
    #     * sinon si type=bf:Distribution, ind2=2
    #         * sinon si type=bf:Manufacture, ind2=3
    #             * sinon si type=bf:Production, ind2=0
    # * prendre dans l’ordre chaque chaque objet de "statement"
    #     * $a = [label] si type=bf:Place
    #     * $a = [label] si type=bf:Agent
    #     * $a = [label] si type=bf:Date
    # Pour chaque "copyrightDate" :
    # * 264 ind2=4 $a = [copyrightDate]
    if key == 'copyrightDate':
        result = {
            '$ind2': '4',
        }
        result = add_value(result, 'a', value)
        return result
    else:
        data = {}
        order = []
        for statement in value.get('statement', []):
            statement_type = statement.get('type')
            subfield = 'a'
            if statement_type == 'bf:Agent':
                subfield = 'b'
            elif statement_type == 'Date':
                subfield = 'c'
            for label in statement.get('label'):
                order.append(subfield)
                data.setdefault(subfield, [])
                data[subfield].append(label['value'])
                # only take the first label
                break
        if data:
            provision_activity_type = value.get('type')
            ind2 = ''
            if provision_activity_type == 'bf:Publication':
                ind2 = '1'
            elif provision_activity_type == 'bf:Distribution':
                ind2 = '2'
            elif provision_activity_type == 'bf:Manufacture':
                ind2 = '3'
            elif provision_activity_type == 'bf:Production':
                ind2 = '0'
            result = {'$ind2': ind2}
            for key, value in data.items():
                result = add_values(result, key, value)
            result['__order__'] = order
            return result


@to_marc21.over('300', '^physical_description')
@utils.ignore_value
def reverse_physical_description(self, key, value):
    """Reverse - physical_description."""
    result = {}
    add_value(result, 'a', value.get('extent'))
    add_value(result, 'b', value.get('other_physical_details'))
    add_value(result, 'c', value.get('dimensions'))
    add_value(result, 'e', value.get('accompanying_material'))
    return result or None


@to_marc21.over('7XX', '^contribution')
@utils.ignore_value
def reverse_contribution(self, key, value):
    """Reverse - contribution."""
    contributions = utils.force_list(value)
    if contributions:
        for contribution in contributions:
            roles = contribution.get('role', {})
            agent = contribution.get('agent', {})
            agent_type = agent.get('type')
            preferred_name = agent.get('preferred_name')
            if not preferred_name:
                current_app.logger.warning(f'JSON to MARC21 {key}: {value}')
                break
            result = {}
            result = add_value(result, 'a', preferred_name)
            if agent_type == 'bf:Person':
                tag = '7000_'
                if ',' in preferred_name:
                    tag = '7001_'
                result = add_value(result, 'b', agent.get('numeration'))
                result = add_value(result, 'c', agent.get('qualifier'))
                date_of_birth = agent.get('date_of_birth', '')
                date_of_birth = \
                    date_of_birth[:4] if len(date_of_birth) > 3 else ''
                date_of_death = agent.get('date_of_death', '')
                date_of_death = \
                    date_of_death[:4] if len(date_of_death) > 3 else ''
                date = f'{date_of_birth} - {date_of_death}'
                if date != ' - ':
                    result = add_value(result, 'd', date)
            elif agent_type == 'bf:Organisation':
                tag = '710__'
                if agent.get('conference'):
                    tag = '711__'
                result = add_values(result, 'b', agent.get('subordinate_unit'))
                result = add_value(result, 'n', agent.get('conference_number'))
                result = add_value(result, 'd', agent.get('conference_date'))
                result = add_value(result, 'c', agent.get('conference_place'))
            result = add_values(result, '4', roles)
            refs = agent.get('refs', [])
            if refs:
                result['0'] = []
            for ref in refs:
                result['__order__'].append('0')
                result['0'].append(f'({ref["source"]}){ref["pid"]}')
            self.append((tag, utils.GroupableOrderedDict(result)))
    return None


@to_marc21.over('900', '^type')
@utils.reverse_for_each_value
@utils.ignore_value
def reverse_type(self, key, value):
    """Reverse - type."""
    result = {
        '__order__': ['a'],
        'a': value.get('main_type')
    }
    subtype_type = value.get('subtype')
    if subtype_type:
        result['__order__'] = ['a', 'b']
        result['b'] = subtype_type
    return result


@to_marc21.over('949', '^holdings_items')
@utils.reverse_for_each_value
@utils.ignore_value
def reverse_holdings_items(self, key, value):
    """Reverse - holdings or items."""
    note_types_to_display = ['general_note', 'patrimonial_note',
                             'provenance_note', 'binding_note',
                             'condition_note']
    result = {
        '__order__': ['0', '1', '2', '3', '4', '5'],
        '0': value['organisation']['pid'],
        '1': value['organisation']['name'],
        '2': value['library']['pid'],
        '3': value['library']['name'],
        '4': value['location']['pid'],
        '5': value['location']['name'],
    }
    holdings = value.get('holdings', {})
    add_value(result, 'B', holdings.get('call_number'))
    add_value(result, 'C', holdings.get('second_call_number'))
    add_value(result, 'D', holdings.get('enumerationAndChronology'))
    uris = [data['uri'] for data in holdings.get('electronic_location')]
    add_values(result, 'E', uris)
    notes = []
    for note in holdings.get('notes', []):
        if note['type'] in note_types_to_display:
            notes.append(note['content'])
    if notes:
        add_values(result, 'F', notes)
    add_value(result, 'G', holdings.get('supplementaryContent'))
    add_value(result, 'H', holdings.get('index'))
    add_value(result, 'I', holdings.get('missing_issues'))

    item = value.get('item', {})
    add_value(result, 'a', item.get('barcode'))
    add_value(result, 'b', item.get('call_number'))
    add_value(result, 'c', item.get('enumerationAndChronology'))
    add_value(result, 'e', item.get('url'))
    notes = []
    for note in item.get('notes', []):
        if note['type'] in note_types_to_display:
            notes.append(note['content'])
    if notes:
        add_values(result, 'f', notes)

    return result
