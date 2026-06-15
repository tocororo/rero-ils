# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019-2022 RERO
# Copyright (C) 2019-2022 UCLouvain
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

"""SRU (Search/Retrieve via URL) and CQL (Contextual Query Language) support.

Implements the SRU 1.1 protocol for searching documents via standard CQL queries,
including query parsing, Elasticsearch translation, and result set management.

See Also:
    - SRU Standard: http://www.loc.gov/standards/sru/
    - CQL Specification: http://www.loc.gov/standards/sru/cql/
"""
