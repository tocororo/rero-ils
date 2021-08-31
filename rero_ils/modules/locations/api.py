# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
# Copyright (C) 2020 UCLouvain
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

"""API for manipulating locations."""
from functools import partial

from elasticsearch_dsl.query import Q
from flask_babelex import gettext as _

from .models import LocationIdentifier, LocationMetadata
from ..api import IlsRecord, IlsRecordsIndexer, IlsRecordsSearch
from ..errors import MissingRequiredParameterError
from ..fetchers import id_fetcher
from ..minters import id_minter
from ..providers import Provider
from ..utils import extracted_data_from_ref

# provider
LocationProvider = type(
    'LocationProvider',
    (Provider,),
    dict(identifier=LocationIdentifier, pid_type='loc')
)
# minter
location_id_minter = partial(id_minter, provider=LocationProvider)
# fetcher
location_id_fetcher = partial(id_fetcher, provider=LocationProvider)


class LocationsSearch(IlsRecordsSearch):
    """RecordsSearch for locations."""

    class Meta:
        """Search only on locations index."""

        index = 'locations'
        doc_types = None
        fields = ('*', )
        facets = {}

        default_filter = None


class Location(IlsRecord):
    """Location class."""

    minter = location_id_minter
    fetcher = location_id_fetcher
    provider = LocationProvider
    model_cls = LocationMetadata
    pids_exist_check = {
        'required': {
            'lib': 'library'
        }
    }

    def extended_validation(self, **kwargs):
        """Validate record against schema.

        and extended validation to allow only one location with field
        is_online = True per library. Also check that "pickup_name" field
        is present and not empty if location is pickup
        """
        online_location_pid = self.get_library().online_location
        if self.get('is_online') and online_location_pid and \
                self.pid != online_location_pid:
            return _('Another online location exists in this library')
        if self.get('is_pickup', False) and \
                not self.get('pickup_name', '').strip():
            return _('Pickup name field is required.')
        return True

    @classmethod
    def get_pickup_location_pids(cls, patron_pid=None, item_pid=None):
        """Return pickup locations."""
        from ..items.api import Item
        from ..patrons.api import Patron
        search = LocationsSearch()

        if item_pid:
            loc = Item.get_record_by_pid(item_pid).get_location()
            if loc.restrict_pickup_to:
                search = search.filter('terms', pid=loc.restrict_pickup_to)

        search = search.filter('term', is_pickup=True)

        if patron_pid:
            org_pid = Patron.get_record_by_pid(patron_pid).organisation_pid
            search = search.filter('term', organisation__pid=org_pid)

        locations = search.source(['pid']).scan()
        for location in locations:
            yield location.pid

    def get_library(self):
        """Get library."""
        from ..libraries.api import Library
        library_pid = extracted_data_from_ref(self.get('library'))
        return Library.get_record_by_pid(library_pid)

    def get_number_of_items(self):
        """Get number of items."""
        from ..items.api import ItemsSearch
        results = ItemsSearch().filter(
            'term', location__pid=self.pid).source().count()
        return results

    def get_number_of_loans(self):
        """Get number of loans."""
        from ..loans.api import LoansSearch, LoanState
        exclude_states = [
            LoanState.CANCELLED, LoanState.ITEM_RETURNED, LoanState.CREATED]
        results = LoansSearch() \
            .filter('bool', should=[
                Q('term', pickup_location_pid=self.pid),
                Q('term', transaction_location_pid=self.pid)
            ]) \
            .exclude('terms', state=exclude_states) \
            .count()
        return results

    def get_links_to_me(self):
        """Get number of links."""
        links = {}
        items_count = self.get_number_of_items()
        if items_count:
            links['items'] = items_count
        loans_count = self.get_number_of_loans()
        if loans_count:
            links['loans'] = loans_count

        return links

    def reasons_not_to_delete(self):
        """Get reasons not to delete record."""
        from ..loans.api import LoansSearch
        cannot_delete = {}
        links = self.get_links_to_me()
        if links:
            cannot_delete['links'] = links
        other = {}
        pickup_location_count = LoansSearch() \
            .filter('term', pickup_location_pid=self.pid).count()
        if pickup_location_count:
            other['loans pickup locations'] = pickup_location_count
        transaction_location_count = LoansSearch() \
            .filter('term', transaction_location_pid=self.pid).count()
        if transaction_location_count:
            other['loans transaction locations'] = transaction_location_count
        if other:
            cannot_delete['other'] = other
        return cannot_delete

    @property
    def library_pid(self):
        """Get library pid for location."""
        return extracted_data_from_ref(self.get('library'))

    @property
    def organisation_pid(self):
        """Get organisation pid for location."""
        from ..libraries.api import Library

        library = Library.get_record_by_pid(self.library_pid)
        return library.organisation_pid

    @property
    def restrict_pickup_to(self):
        """Get restriction pickup location pid of location."""
        location_pids = []
        for restrict_pickup_to in self.get('restrict_pickup_to', []):
            location_pids.append(extracted_data_from_ref(restrict_pickup_to))
        return location_pids

    @classmethod
    def can_request(cls, item, **kwargs):
        """Check if an item can be requested regarding its location.

        :param item : the item to check
        :param kwargs : addition arguments
        :return a tuple with True|False and reasons to disallow if False.
        """
        if item and not item.get_location().get('allow_request', False):
            return False, [_('Item location disallows request.')]
        return True, []

    def transaction_location_validator(self, location_pid):
        """Validate that the given transaction location PID is valid.

        Add additional validation later if needed.

        :param location_pid: location pid to validate.
        :returns: True if valid location otherwise false.
        """
        return Location.record_pid_exists(location_pid)


class LocationsIndexer(IlsRecordsIndexer):
    """Holdings indexing class."""

    record_cls = Location

    def bulk_index(self, record_id_iterator):
        """Bulk index records.

        :param record_id_iterator: Iterator yielding record UUIDs.
        """
        super().bulk_index(record_id_iterator, doc_type='loc')


def search_locations_by_pid(organisation_pid=None, library_pid=None,
                            is_online=False, is_pickup=False,
                            sort_by_field='location_name', sort_order='asc',
                            preserve_order=False):
    """Retrieve locations attached to the given organisation or library.

    :param organisation_pid: Organisation pid.
    :param library_pid: Library pid.
    :param is_online: Filter only on online location.
    :param is_pickup: Filter only on pickup location.
    :param sort_by_field: Location field used for sort.
    :param sort_order: Sort order `asc` or `desc`.
    :param preserve_order: Preserve order.
    :returns: - A Search object.
    """
    search = LocationsSearch()

    if organisation_pid:
        search = search.filter('term', organisation__pid=organisation_pid)
    elif library_pid:
        search = search.filter('term', library__pid=library_pid)
    else:
        raise MissingRequiredParameterError(
            "One of the parameters 'organisation_pid' "
            "or 'library_pid' is required."
        )

    if is_online:
        search = search.filter('term', is_online=is_online)

    if is_pickup:
        search = search.filter('term', is_pickup=is_pickup)

    if sort_by_field:
        search = search.sort({sort_by_field: {'order': sort_order}})
        if preserve_order:
            search = search.params(preserve_order=True)
    return search


def search_location_by_pid(loc_pid):
    """Search location for the given location pid."""
    loc_search = LocationsSearch().filter('term', pid=loc_pid)
    for location in loc_search.scan():
        return location
