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

"""Tests REST API documents."""
import json
from copy import deepcopy
from datetime import datetime, timedelta

import mock
from flask import url_for
from invenio_accounts.testutils import login_user_via_session
from utils import VerifyRecordPermissionPatch, get_json, mock_response, \
    postdata

from rero_ils.modules.documents.utils import clean_text, get_remote_cover
from rero_ils.modules.documents.views import can_request, \
    record_library_pickup_locations
from rero_ils.modules.utils import get_ref_for_pid


def test_documents_permissions(client, document, json_header):
    """Test record retrieval."""
    item_url = url_for('invenio_records_rest.doc_item', pid_value='doc1')

    res = client.get(item_url)
    assert res.status_code == 200

    res, _ = postdata(
        client,
        'invenio_records_rest.doc_list',
        {}
    )
    assert res.status_code == 401

    res = client.put(
        url_for('invenio_records_rest.doc_item', pid_value='doc1'),
        data={},
        headers=json_header
    )

    res = client.delete(item_url)
    assert res.status_code == 401


def test_documents_newacq_filters(app, client,
                                  system_librarian_martigny,
                                  rero_json_header, document,
                                  holding_lib_martigny, holding_lib_saxon,
                                  loc_public_saxon,
                                  item_lib_martigny_data,
                                  ):
    login_user_via_session(client, system_librarian_martigny.user)

    # compute useful date
    today = datetime.today()
    past = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    future = (today + timedelta(days=10)).strftime('%Y-%m-%d')
    future_1 = (today + timedelta(days=11)).strftime('%Y-%m-%d')
    today = today.strftime('%Y-%m-%d')

    # Add a new items with acq_date
    new_acq1 = deepcopy(item_lib_martigny_data)
    new_acq1['pid'] = 'itemacq1'
    new_acq1['acquisition_date'] = today
    del new_acq1['barcode']
    res, data = postdata(client, 'invenio_records_rest.item_list', new_acq1)
    assert res.status_code == 201

    new_acq2 = deepcopy(item_lib_martigny_data)
    new_acq2['pid'] = 'itemacq2'
    new_acq2['acquisition_date'] = future
    new_acq2['location']['$ref'] = get_ref_for_pid('loc', loc_public_saxon.pid)
    del new_acq2['barcode']
    res, data = postdata(client, 'invenio_records_rest.item_list', new_acq2)
    assert res.status_code == 201

    # check item creation and indexation
    doc_list = url_for(
        'invenio_records_rest.doc_list',
        view='global', pid='doc1'
    )
    res = client.get(doc_list, headers=rero_json_header)
    data = get_json(res)
    assert len(data['hits']['hits']) == 1
    data = data['hits']['hits'][0]['metadata']
    assert len(data['holdings']) == 2
    assert len(data['holdings'][0]['items']) == 1
    assert len(data['holdings'][1]['items']) == 1

    # check new_acquisition filters
    #   --> For org2, there is no new acquisition
    doc_list = url_for(
        'invenio_records_rest.doc_list',
        view='global',
        new_acquisition=':',
        organisation='org2'
    )
    res = client.get(doc_list, headers=rero_json_header)
    data = get_json(res)
    assert data['hits']['total']['value'] == 0

    #   --> for org1, there is 1 document with 2 new acquisition items
    doc_list = url_for(
        'invenio_records_rest.doc_list',
        view='global',
        new_acquisition='{0}:{1}'.format(past, future_1),
        organisation='org1'
    )
    res = client.get(doc_list, headers=rero_json_header)
    data = get_json(res)
    assert data['hits']['total']['value'] == 1
    assert len(data['hits']['hits'][0]['metadata']['holdings']) == 2

    #   --> for lib2, there is 1 document with 1 new acquisition items
    doc_list = url_for(
        'invenio_records_rest.doc_list',
        view='global',
        new_acquisition='{0}:{1}'.format(past, future_1),
        library='lib2'
    )
    res = client.get(doc_list, headers=rero_json_header)
    data = get_json(res)
    assert data['hits']['total']['value'] == 1

    #   --> for loc3, there is 1 document with 1 new acquisition items
    doc_list = url_for(
        'invenio_records_rest.doc_list',
        view='global',
        new_acquisition='{0}:{1}'.format(past, future_1),
        location='loc3'
    )
    res = client.get(doc_list, headers=rero_json_header)
    data = get_json(res)
    assert data['hits']['total']['value'] == 1

    #   --> for loc3, there is no document corresponding to range date
    doc_list = url_for(
        'invenio_records_rest.doc_list',
        view='global',
        new_acquisition='{0}:{1}'.format(past, today),
        location='loc3'
    )
    res = client.get(doc_list, headers=rero_json_header)
    data = get_json(res)
    assert data['hits']['total']['value'] == 0


@mock.patch('invenio_records_rest.views.verify_record_permission',
            mock.MagicMock(return_value=VerifyRecordPermissionPatch))
def test_documents_facets(
    client, document, document2_ref, ebook_1, ebook_2, ebook_3, ebook_4,
    item_lib_martigny, rero_json_header
):
    """Test record retrieval."""
    # STEP#1 :: CHECK FACETS ARE PRESENT INTO SEARCH RESULT
    url = url_for('invenio_records_rest.doc_list', view='global')
    res = client.get(url, headers=rero_json_header)
    data = get_json(res)
    facet_keys = [
        'document_type', 'author', 'language', 'subject_no_fiction',
        'subject_fiction', 'genreForm', 'intendedAudience',
        'year', 'status'
    ]
    assert all(key in data['aggregations'] for key in facet_keys)

    params = {'view': 'global', 'facets': ''}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url, headers=rero_json_header)
    data = get_json(res)
    assert not data['aggregations']

    params = {'view': 'global', 'facets': 'document_type'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url, headers=rero_json_header)
    data = get_json(res)
    assert list(data['aggregations'].keys()) == ['document_type']

    params = {'view': 'org1', 'facets': 'document_type'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url, headers=rero_json_header)
    data = get_json(res)
    assert list(data['aggregations'].keys()) == ['document_type']

    # test the patch that the library facet is computed by the serializer
    params = {'view': 'org1', 'facets': 'document_type,library,author'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url, headers=rero_json_header)
    data = get_json(res)
    aggs = data['aggregations']
    assert set(aggs.keys()) == {'document_type', 'library', 'author'}

    # TEST FILTERS
    # Each filter checks is a tuple. First tuple element is argument used to
    # call the API, second tuple argument is the number of document that
    # should be return by the API call.
    checks = [
        ({'view': 'global', 'author': 'Peter James'}, 2),
        ({'view': 'global', 'author': 'Great Edition'}, 1),
        ({'view': 'global', 'author': 'J.K. Rowling'}, 1),
        ({'view': 'global', 'author': ['Great Edition', 'Peter James']}, 1),
        ({'view': 'global', 'author': ['J.K. Rowling', 'Peter James']}, 0),
        # i18n facets
        ({'view': 'global', 'author': 'Nebehay, Christian Michael'}, 2),
        ({'view': 'global',
          'author': 'Nebehay, Christian Michael, 1909-2003', 'lang': 'de'}, 1),
        ({'view': 'global',
          'author': 'Nebehay, Christian Michael', 'lang': 'thl'}, 2),
    ]
    for params, value in checks:
        url = url_for('invenio_records_rest.doc_list', **params)
        res = client.get(url)
        data = get_json(res)
        assert data['hits']['total']['value'] == value


@mock.patch('invenio_records_rest.views.verify_record_permission',
            mock.MagicMock(return_value=VerifyRecordPermissionPatch))
def test_documents_organisation_facets(
    client, document, item_lib_martigny, rero_json_header
):
    """Test record retrieval."""
    list_url = url_for('invenio_records_rest.doc_list', view='global')

    res = client.get(list_url, headers=rero_json_header)
    data = get_json(res)
    aggs = data['aggregations']

    assert 'organisation' in aggs


@mock.patch('invenio_records_rest.views.verify_record_permission',
            mock.MagicMock(return_value=VerifyRecordPermissionPatch))
def test_documents_library_location_facets(
    client, document, org_martigny, item_lib_martigny, rero_json_header
):
    """Test record retrieval."""
    list_url = url_for('invenio_records_rest.doc_list', view='org1')

    res = client.get(list_url, headers=rero_json_header)
    data = get_json(res)
    aggs = data['aggregations']

    assert 'library' in aggs

    # Test if location sub-buckets exists under each Library hit
    for hit in aggs['library']['buckets']:
        assert 'location' in hit


@mock.patch('invenio_records_rest.views.verify_record_permission',
            mock.MagicMock(return_value=VerifyRecordPermissionPatch))
def test_documents_post_put_delete(
    client, document_chinese_data, json_header, rero_json_header
):
    """Test record retrieval."""
    # Create record / POST
    item_url = url_for('invenio_records_rest.doc_item', pid_value='4')
    list_url = url_for('invenio_records_rest.doc_list', q='pid:4')

    document_chinese_data['pid'] = '4'
    res, data = postdata(
        client,
        'invenio_records_rest.doc_list',
        document_chinese_data
    )

    assert res.status_code == 201

    # Check that the returned record matches the given data
    test_data = data['metadata']
    test_data.pop('sort_title', None)
    assert clean_text(test_data) == document_chinese_data

    res = client.get(item_url)
    assert res.status_code == 200
    data = get_json(res)

    test_data = data['metadata']
    test_data.pop('sort_title', None)
    assert clean_text(test_data) == document_chinese_data
    expected_title = [
        {
            '_text': '\u56fd\u9645\u6cd5 : subtitle (Chinese). '
                     'Part Number (Chinese), Part Name (Chinese) = '
                     'International law (Chinese) : '
                     'Parallel Subtitle (Chinese). '
                     'Parallel Part Number (Chinese), '
                     'Parallel Part Name (Chinese) = '
                     'Parallel Title 2 (Chinese) : '
                     'Parallel Subtitle 2 (Chinese)',
            'mainTitle': [
                    {'value': 'Guo ji fa'},
                    {
                        'value': '\u56fd\u9645\u6cd5',
                        'language': 'chi-hani'
                    }
            ],
            'subtitle': [
                {'value': 'subtitle (Latin)'},
                {
                    'value': 'subtitle (Chinese)',
                    'language': 'chi-hani'
                }
            ],
            'part': [{
                'partNumber': [
                    {'value': 'Part Number (Latin)'},
                    {
                        'value': 'Part Number (Chinese)',
                        'language': 'chi-hani'
                    }
                ],
                'partName': [
                    {'value': 'Part Name (Latin)'},
                    {
                        'language': 'chi-hani',
                        'value': 'Part Name (Chinese)'
                    }
                ]
            }],
            'type': 'bf:Title'
        },
        {
            'mainTitle': [
                {'value': 'International law (Latin)'},
                {
                    'value': 'International law (Chinese)',
                    'language': 'chi-hani'
                }
            ],
            'subtitle': [
                {'value': 'Parallel Subtitle (Latin)'},
                {
                    'value': 'Parallel Subtitle (Chinese)',
                    'language': 'chi-hani'
                }
            ],
            'part': [{
                'partNumber': [
                    {'value': 'Parallel Part Number (Latin)'},
                    {
                        'value': 'Parallel Part Number (Chinese)',
                        'language': 'chi-hani'
                    }
                ],
                'partName': [
                    {'value': 'Parallel Part Name (Latin)'},
                    {
                        'language': 'chi-hani',
                        'value': 'Parallel Part Name (Chinese)'
                    }
                ]
            }],

            'type': 'bf:ParallelTitle'
        },
        {
            'mainTitle': [
                {'value': 'Parallel Title 2 (Latin)'},
                {
                    'value': 'Parallel Title 2 (Chinese)',
                    'language': 'chi-hani'
                }
            ],
            'subtitle': [
                {'value': 'Parallel Subtitle 2 (Latin)'},
                {
                    'value': 'Parallel Subtitle 2 (Chinese)',
                    'language': 'chi-hani'
                }
            ],
            'type': 'bf:ParallelTitle'
        },
        {
            'mainTitle': [{'value': 'Guojifa'}],
            'type': 'bf:VariantTitle'
        }
    ]

    # Update record/PUT
    data = document_chinese_data
    res = client.put(
        item_url,
        data=json.dumps(data),
        headers=rero_json_header
    )
    assert res.status_code == 200
    # assert res.headers['ETag'] != '"{}"'.format(librarie.revision_id)

    # Check that the returned record matches the given data
    data = get_json(res)
    assert data['metadata']['title'] == expected_title
    assert data['metadata']['ui_title_variants'] == ['Guojifa']
    assert data['metadata']['ui_title_altgr'] == \
        ['Guo ji fa : subtitle (Latin). Part Number (Latin), Part Name (Latin)'
         ' = International law (Latin) : Parallel Subtitle (Latin).'
         ' Parallel Part Number (Latin), Parallel Part Name (Latin)'
         ' = Parallel Title 2 (Latin) : Parallel Subtitle 2 (Latin)']
    assert data['metadata']['ui_responsibilities'] == [
        '梁西原著主编, 王献枢副主编',
        'Liang Xi yuan zhu zhu bian, Wang Xianshu fu zhu bian'
    ]

    res = client.get(item_url)
    assert res.status_code == 200

    # Delete record/DELETE
    res = client.delete(item_url)
    assert res.status_code == 204

    res = client.get(item_url)
    assert res.status_code == 410


def test_documents_get_resolve_rero_json(
    client, document_ref, contribution_person_data, rero_json_header,
):
    """Test record get with resolve and mimetype rero+json."""
    api_url = url_for('invenio_records_rest.doc_item', pid_value='doc2',
                      resolve='1')
    res = client.get(api_url, headers=rero_json_header)
    assert res.status_code == 200
    metadata = get_json(res).get('metadata', {})
    pid = metadata['contribution'][0]['agent']['pid']
    assert pid == contribution_person_data['pid']


def test_document_can_request_view(
        client, item_lib_fully,
        loan_pending_martigny, document,
        patron_martigny,
        patron2_martigny,
        item_type_standard_martigny,
        circulation_policies,
        librarian_martigny,
        item_lib_martigny,
        item_lib_saxon,
        item_lib_sion,
        loc_public_martigny
):
    """Test can request on document view."""
    login_user_via_session(client, patron_martigny.user)

    with mock.patch(
        'rero_ils.modules.documents.views.current_user',
        patron_martigny.user
    ), mock.patch(
        'rero_ils.modules.documents.views.current_patrons',
        [patron_martigny]
    ):
        can, _ = can_request(item_lib_fully)
        assert can
        can, _ = can_request(item_lib_sion)
        assert not can

    with mock.patch(
        'rero_ils.modules.documents.views.current_user',
        patron2_martigny.user
    ), mock.patch(
        'rero_ils.modules.documents.views.current_patrons',
        [patron2_martigny]
    ):
        can, _ = can_request(item_lib_fully)
        assert not can

    picks = record_library_pickup_locations(item_lib_fully)
    assert len(picks) == 3

    picks = record_library_pickup_locations(item_lib_martigny)
    assert len(picks) == 3


def test_document_boosting(client, ebook_1, ebook_4):
    """Test document boosting."""
    list_url = url_for(
        'invenio_records_rest.doc_list',
        q='maison'
    )
    res = client.get(list_url)
    hits = get_json(res)['hits']
    assert hits['total']['value'] == 2
    data = hits['hits'][0]['metadata']
    assert data['pid'] == ebook_1.pid

    list_url = url_for(
        'invenio_records_rest.doc_list',
        q='autocomplete_title:maison AND' +
          'contribution.agent.authorized_access_point:James'
    )
    res = client.get(list_url)
    hits = get_json(res)['hits']
    assert hits['total']['value'] == 1
    data = hits['hits'][0]['metadata']
    assert data['pid'] == ebook_1.pid


@mock.patch('requests.get')
def test_documents_resolve(
        mock_contributions_mef_get, client, loc_public_martigny, document_ref,
        contribution_person_response_data
):
    """Test document detailed view with items filter."""
    res = client.get(url_for(
        'invenio_records_rest.doc_item',
        pid_value='doc2'
    ))
    assert res.json['metadata']['contribution'] == [{
        'agent': {
            '$ref': 'https://mef.rero.ch/api/agents/rero/A017671081',
            'pid': 'cont_pers',
            'type': 'bf:Person'
            },
        'role': ['aut']
    }]
    assert res.status_code == 200

    mock_contributions_mef_get.return_value = mock_response(
        json_data=contribution_person_response_data
    )
    res = client.get(url_for(
        'invenio_records_rest.doc_item',
        pid_value='doc2',
        resolve='1'
    ))
    assert res.json['metadata'][
        'contribution'][0]['agent']['authorized_access_point_fr']
    assert res.status_code == 200


def test_document_exclude_draft_records(client, document):
    """Test document exclude draft record."""
    list_url = url_for(
        'invenio_records_rest.doc_list',
        q='Lingliang'
    )
    res = client.get(list_url)
    hits = get_json(res)['hits']
    assert hits['total']['value'] == 1
    data = hits['hits'][0]['metadata']
    assert data['pid'] == document.get('pid')

    document['_draft'] = True
    document.update(document, dbcommit=True, reindex=True)

    list_url = url_for(
        'invenio_records_rest.doc_list',
        q='Lingliang'
    )
    res = client.get(list_url)
    hits = get_json(res)['hits']
    assert hits['total']['value'] == 0

    document['_draft'] = False
    document.update(document, dbcommit=True, reindex=True)

    list_url = url_for(
        'invenio_records_rest.doc_list',
        q='Lingliang'
    )
    res = client.get(list_url)
    hits = get_json(res)['hits']
    assert hits['total']['value'] == 1


@mock.patch('requests.get')
def test_get_remote_cover(mock_get_cover, app):
    """Test get remote cover."""
    mock_get_cover.return_value = mock_response(status=400)
    assert get_remote_cover('YYYYYYYYY') is None

    mock_get_cover.return_value = mock_response(
        content='thumb({'
                '    "success": true,'
                '    "image": "https://i.test.com/images/P/XXXXXXXXXX_.jpg"'
                '})'
    )
    cover = get_remote_cover('XXXXXXXXXX')
    assert cover == {
        'success': True,
        'image': 'https://i.test.com/images/P/XXXXXXXXXX_.jpg'
    }


def test_document_identifiers_search(client, document):
    """Test search on `identifiedBy` document."""

    def success(response_data):
        data = response_data['hits']
        return data['total']['value'] == 1 \
            and data['hits'][0]['metadata']['pid'] == document.pid

    def failure(response_data):
        return response_data['hits']['total']['value'] == 0

    # STEP#1 :: SEARCH FOR AN EXISTING IDENTIFIER
    #   Search for an existing encoded document identifier. The ISBN-13 is
    #   encoded into document data. Search on this specific value will return
    #   a record.
    params = {'identifiers': '(bf:Isbn)9782844267788'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))

    # STEP#2 :: SEARCH FOR AN ALTERNATIVE IDENTIFIER
    #   Search for the alternative of the encoded ISBN-13 value. During the
    #   document indexing process the corresponding ISBN-10 is appended to
    #   identifier list. A search on this value should return the same
    #   document. Additionally, search with hyphens to validate the specific
    #   identifier analyzer used for this field.
    params = {'identifiers': '(bf:Isbn)2-84426-778-5'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))

    # STEP#3 :: SEARCH WITH ONLY IDENTIFIER VALUE
    #   Search only about an identifier value without specified any identifier
    #   type.
    params = {'identifiers': 'R008745599'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))

    # STEP#4 :: SEARCH ON UNKNOWN IDENTIFIERS
    for id_value in ['dummy_identifiers', '(bf:Issn)9782844267788']:
        params = {'identifiers': id_value}
        url = url_for('invenio_records_rest.doc_list', **params)
        res = client.get(url)
        assert failure(get_json(res))

    # STEP#5 :: GROUPED SEARCH
    #   Use this filter in combination with other filter. In this test, the
    #   document isn't an harvested document, but it contains the correct
    #   specified identifier.
    params = {
        'identifiers': '(bf:Ean)9782844267788',
        'q': 'harvested:true'
    }
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert failure(get_json(res))

    params['q'] = 'harvested:false'
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))

    # STEP#6 :: SEARCH USING SHORTCUT ES KEYS
    #   'isbn' and 'issn' keys are added to the ES stored document. These key
    #   only contains the corresponding identifiers value ; but analyzer
    #   allows search using hyphens or not.
    url = url_for('invenio_records_rest.doc_list', q='isbn:2-84426-778-5')
    res = client.get(url)
    assert success(get_json(res))

    # STEP#7 :: WILDCARD SEARCH
    #    `identifiers` filter allow to search on a partial identifier string
    #    (only for the identifier value part).
    params = {'identifiers': 'R0087455*'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))

    params = {'identifiers': '(bf:Local)*87455*'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))

    params = {'identifiers': '*dummy_search*'}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert failure(get_json(res))

    # STEP#8 :: SEARCH WITH MULTIPLE IDENTIFIERS
    #    If we send multiple identifiers, an OR query will be used to search on
    #    each of them.
    params = {'identifiers': ['dummy', 'other_id', '(bf:Ean)9782844267788']}
    url = url_for('invenio_records_rest.doc_list', **params)
    res = client.get(url)
    assert success(get_json(res))
