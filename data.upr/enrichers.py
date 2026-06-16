# -*- coding: utf-8 -*-
"""Enriquecimiento de entidades locales con fuentes de autoridad externas.

Cada fuente es una función ``f(query, etype, ctx)`` que devuelve un dict con la
etiqueta canónica, un ``identifier`` válido para el esquema y campos opcionales
(nombres alternativos, fechas), o ``None`` si no hay coincidencia.

Cadenas por tipo (se consultan en orden, gana el primer match):

    Person       → VIAF, BNE, ORCID, Wikidata
    Topic        → LCSH, BNE, GND, UNESCO, Wikidata
    Place        → GeoNames, GND, Wikidata
    Organisation → VIAF, ROR, GND, ISNI, Wikidata
    Work         → VIAF, WorldCat, OpenLibrary, Wikidata
    Temporal     → Wikidata, GND

El esquema ``identifier`` solo admite ``type`` en {bf:Local, IdRef, GND, RERO};
por eso GND usa ``type: GND`` y el resto ``type: bf:Local`` con ``source``.

La caché en disco (``<output>/.enrich_cache/<source>.json``) hace el proceso
reanudable: reejecutar no repite llamadas ya resueltas.
"""

import json
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

USER_AGENT = 'rero-ils-upr-entity-enricher/1.0 (library authority control)'

SOURCE_LABEL = {
    'viaf': 'VIAF', 'bne': 'BNE', 'orcid': 'ORCID', 'wikidata': 'Wikidata',
    'lcsh': 'LCSH', 'gnd': 'GND', 'unesco': 'UNESCO', 'geonames': 'GeoNames',
    'ror': 'ROR', 'isni': 'ISNI', 'worldcat': 'WorldCat',
    'openlibrary': 'OpenLibrary',
}

# Intervalo mínimo entre llamadas a cada fuente (segundos).
THROTTLE = {
    'viaf': 0.3, 'geonames': 1.1, 'wikidata': 0.3, 'lcsh': 0.3, 'gnd': 0.3,
    'unesco': 0.3, 'orcid': 0.3, 'ror': 0.3, 'isni': 0.5, 'worldcat': 0.5,
    'bne': 0.5, 'openlibrary': 0.3,
}

CHAINS = {
    'bf:Person': ['viaf', 'bne', 'orcid', 'wikidata'],
    'bf:Topic': ['lcsh', 'bne', 'gnd', 'unesco', 'wikidata'],
    'bf:Place': ['geonames', 'gnd', 'wikidata'],
    'bf:Organisation': ['viaf', 'ror', 'gnd', 'isni', 'wikidata'],
    'bf:Work': ['viaf', 'worldcat', 'openlibrary', 'wikidata'],
    'bf:Temporal': ['wikidata', 'gnd'],
}

# Nombres cortos de --enrich-types → tipo bibframe.
TYPE_ALIASES = {
    'person': 'bf:Person', 'topic': 'bf:Topic', 'organisation': 'bf:Organisation',
    'place': 'bf:Place', 'temporal': 'bf:Temporal', 'work': 'bf:Work',
}


# ==============================================================================
# Infraestructura: caché, throttling y HTTP
# ==============================================================================

class Cache:
    """Caché en disco, un fichero JSON por fuente, cargada de forma perezosa."""

    def __init__(self, base):
        self.base = base
        os.makedirs(base, exist_ok=True)
        self._data = {}

    def _path(self, source):
        return os.path.join(self.base, f'{source}.json')

    def _bucket(self, source):
        if source not in self._data:
            path = self._path(source)
            if os.path.exists(path):
                with open(path, encoding='utf-8') as f:
                    self._data[source] = json.load(f)
            else:
                self._data[source] = {}
        return self._data[source]

    def has(self, source, key):
        return key in self._bucket(source)

    def get(self, source, key):
        return self._bucket(source).get(key)

    def set(self, source, key, value):
        self._bucket(source)[key] = value

    def flush(self):
        for source, data in self._data.items():
            with open(self._path(source), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)


def _throttle(ctx, source):
    interval = THROTTLE.get(source, 0.3)
    last = ctx['last'].get(source, 0.0)
    wait = interval - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    ctx['last'][source] = time.time()


def _fetch(url, accept='application/json', timeout=20, retries=3):
    """GET con reintentos y backoff. Devuelve texto crudo o None."""
    req = urllib.request.Request(
        url, headers={'User-Agent': USER_AGENT, 'Accept': accept})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def _fetch_json(url, timeout=20, retries=3):
    raw = _fetch(url, 'application/json', timeout, retries)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _identifier(source, value):
    """Construye un identifier válido para el esquema common/identifier."""
    if source == 'gnd':
        return {'type': 'GND', 'value': str(value)}
    return {'type': 'bf:Local', 'value': str(value), 'source': SOURCE_LABEL[source]}


def _q(value):
    return urllib.parse.quote(value)


# ==============================================================================
# Fuentes
# ==============================================================================

VIAF_NAMETYPE = {
    'bf:Person': 'personal', 'bf:Organisation': 'corporate',
    'bf:Work': 'uniformtitle',
}


def viaf(query, etype, ctx):
    wanted = VIAF_NAMETYPE.get(etype)
    data = _fetch_json(f'https://viaf.org/viaf/AutoSuggest?query={_q(query)}')
    for hit in (data or {}).get('result') or []:
        if wanted and hit.get('nametype') != wanted:
            continue
        return {'label': hit.get('term'),
                'identifier': _identifier('viaf', hit['viafid'])}
    return None


def wikidata(query, etype, ctx):
    url = ('https://www.wikidata.org/w/api.php?action=wbsearchentities'
           f'&search={_q(query)}&language=es&uselang=es&format=json&limit=1')
    data = _fetch_json(url)
    hits = (data or {}).get('search') or []
    if not hits:
        return None
    hit = hits[0]
    result = {'label': hit.get('label'),
              'identifier': _identifier('wikidata', hit['id'])}
    if hit.get('aliases'):
        result['alt_names'] = hit['aliases']
    return result


def lcsh(query, etype, ctx):
    # Sugerencias OpenSearch de id.loc.gov: ["q",[labels],[],[uris]]
    data = _fetch_json(
        f'https://id.loc.gov/authorities/subjects/suggest/?q={_q(query)}')
    if not data or len(data) < 4 or not data[3]:
        return None
    uri = data[3][0]
    label = data[1][0] if data[1] else None
    return {'label': label, 'identifier': _identifier('lcsh', uri.rstrip('/').split('/')[-1])}


def gnd(query, etype, ctx):
    url = f'https://lobid.org/gnd/search?q={_q(query)}&size=1&format=json'
    data = _fetch_json(url)
    members = (data or {}).get('member') or []
    if not members:
        return None
    m = members[0]
    result = {'label': m.get('preferredName'),
              'identifier': _identifier('gnd', m['gndIdentifier'])}
    if m.get('variantName'):
        result['alt_names'] = m['variantName'][:10]
    return result


def unesco(query, etype, ctx):
    url = ('https://vocabularies.unesco.org/browser/rest/v1/thesaurus/search'
           f'?query={_q(query)}&lang=es&maxhits=1')
    data = _fetch_json(url)
    results = (data or {}).get('results') or []
    if not results:
        return None
    r = results[0]
    return {'label': r.get('prefLabel'),
            'identifier': _identifier('unesco', r['uri'])}


def geonames(query, etype, ctx):
    user = ctx.get('geonames_user')
    if not user:
        return None
    url = (f'http://api.geonames.org/searchJSON?q={_q(query)}'
           f'&maxRows=1&username={_q(user)}')
    data = _fetch_json(url)
    rows = (data or {}).get('geonames') or []
    if not rows:
        return None
    g = rows[0]
    result = {'label': g.get('name'),
              'identifier': _identifier('geonames', g['geonameId'])}
    alt = [g.get('toponymName'), g.get('countryName')]
    alt = [a for a in alt if a and a != g.get('name')]
    if alt:
        result['alt_names'] = alt
    return result


def orcid(query, etype, ctx):
    url = f'https://pub.orcid.org/v3.0/expanded-search/?q={_q(query)}&rows=1'
    data = _fetch_json(url)
    rows = (data or {}).get('expanded-result') or []
    if not rows:
        return None
    r = rows[0]
    name = ' '.join(p for p in (r.get('family-names'), r.get('given-names')) if p)
    return {'label': name or query,
            'identifier': _identifier('orcid', r['orcid-id'])}


def ror(query, etype, ctx):
    data = _fetch_json(f'https://api.ror.org/organizations?query={_q(query)}')
    items = (data or {}).get('items') or []
    if not items:
        return None
    item = items[0]
    result = {'label': item.get('name'),
              'identifier': _identifier('ror', item['id'])}
    if item.get('aliases'):
        result['alt_names'] = item['aliases']
    return result


def openlibrary(query, etype, ctx):
    url = f'https://openlibrary.org/search.json?q={_q(query)}&limit=1'
    data = _fetch_json(url)
    docs = (data or {}).get('docs') or []
    if not docs:
        return None
    doc = docs[0]
    return {'label': doc.get('title'),
            'identifier': _identifier('openlibrary', doc['key'])}


def isni(query, etype, ctx):
    # SRU (XML). Best-effort: primer ISNI del resultado.
    url = ('https://isni.oclc.org/sru?operation=searchRetrieve&version=1.1'
           f'&query=pica.nw%3D%22{_q(query)}%22&maximumRecords=1')
    raw = _fetch(url, 'application/xml')
    if not raw:
        return None
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None
    for el in root.iter():
        if el.tag.endswith('isniUnformatted') and el.text:
            return {'label': query, 'identifier': _identifier('isni', el.text.strip())}
    return None


def bne(query, etype, ctx):
    # Reconciliación OpenRefine de datos.bne.es (best-effort).
    payload = json.dumps({'q0': {'query': query, 'limit': 1}})
    url = ('https://datos.bne.es/openrefine/reconcile?queries='
           + urllib.parse.quote(payload))
    data = _fetch_json(url)
    results = ((data or {}).get('q0') or {}).get('result') or []
    if not results:
        return None
    r = results[0]
    return {'label': r.get('name'), 'identifier': _identifier('bne', r['id'])}


def worldcat(query, etype, ctx):
    key = ctx.get('worldcat_key')
    if not key:
        return None
    url = ('http://www.worldcat.org/webservices/catalog/search/sru'
           f'?wskey={_q(key)}&query=srw.ti+all+%22{_q(query)}%22'
           '&maximumRecords=1')
    raw = _fetch(url, 'application/xml')
    if not raw:
        return None
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None
    for el in root.iter():
        if el.tag.endswith('controlfield') and el.get('tag') == '001' and el.text:
            return {'label': query,
                    'identifier': _identifier('worldcat', el.text.strip())}
    return None


SOURCES = {
    'viaf': viaf, 'bne': bne, 'orcid': orcid, 'wikidata': wikidata,
    'lcsh': lcsh, 'gnd': gnd, 'unesco': unesco, 'geonames': geonames,
    'ror': ror, 'isni': isni, 'worldcat': worldcat, 'openlibrary': openlibrary,
}


# ==============================================================================
# Orquestación
# ==============================================================================

def _norm(text):
    return ' '.join((text or '').split()).lower()


def _call_source(source, query, etype, ctx):
    """Llama a una fuente con caché y throttling. Devuelve el dict o None."""
    cache = ctx['cache']
    key = _norm(query)
    if cache.has(source, key):
        return cache.get(source, key)
    _throttle(ctx, source)
    try:
        result = SOURCES[source](query, etype, ctx)
    except Exception:
        result = None
    cache.set(source, key, result)
    return result


def _merge(entity, etype, source, result):
    """Vuelca el resultado de una fuente en la entidad (respetando el esquema)."""
    entity['identifier'] = result['identifier']
    entity['source_catalog'] = SOURCE_LABEL[source]
    entity['_enriched'] = True
    if etype != 'bf:Work' and result.get('alt_names'):
        existing = entity.get('alternative_names', [])
        merged, seen = [], {_norm(entity.get('name', ''))}
        for n in existing + result['alt_names']:
            if n and _norm(n) not in seen:
                seen.add(_norm(n))
                merged.append(n)
        if merged:
            entity['alternative_names'] = merged[:10]
    if etype == 'bf:Person':
        if result.get('birth') and 'date_of_birth' not in entity:
            entity['date_of_birth'] = result['birth']
        if result.get('death') and 'date_of_death' not in entity:
            entity['date_of_death'] = result['death']


def enrich_store(store, types=None, limit=None, geonames_user=None,
                 worldcat_key=None, cache_dir=None):
    """Enriquece las entidades del ``EntityStore`` consultando fuentes externas.

    Marca cada entidad enriquecida con ``_enriched`` (lo consume la escritura de
    salida para separar ``<tipo>.enriched.json``).
    """
    if cache_dir is None:
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'legacy', '.enrich_cache')
    ctx = {
        'cache': Cache(cache_dir),
        'last': {},
        'geonames_user': geonames_user,
        'worldcat_key': worldcat_key,
    }

    wanted_types = None
    if types:
        wanted_types = {TYPE_ALIASES.get(t.strip(), t.strip())
                        for t in types.split(',') if t.strip()}

    print('\n' + '=' * 80)
    print('🌐 ENRIQUECIMIENTO DESDE FUENTES EXTERNAS')
    print('=' * 80)
    if not geonames_user:
        print('  ⚠️  Sin --geonames-user: la fuente GeoNames se omite.')
    if not worldcat_key:
        print('  ⚠️  Sin --worldcat-key: la fuente WorldCat se omite.')

    for etype, chain in CHAINS.items():
        if wanted_types and etype not in wanted_types:
            continue
        bucket = store.by_type[etype]
        entities = list(bucket.values())
        if limit is not None:
            entities = entities[:limit]
        enriched = 0
        print(f'\n  {etype}: enriqueciendo {len(entities)} entidades '
              f'(fuentes: {", ".join(chain)})...')
        for n, entity in enumerate(entities, 1):
            query = entity.get('title') if etype == 'bf:Work' else entity.get('name')
            if not query:
                continue
            for source in chain:
                result = _call_source(source, query, etype, ctx)
                if result and result.get('identifier'):
                    _merge(entity, etype, source, result)
                    enriched += 1
                    break
            if n % 200 == 0:
                ctx['cache'].flush()
                print(f'    ... {n}/{len(entities)} (enriquecidas: {enriched})')
        print(f'  ✅ {etype}: {enriched}/{len(entities)} enriquecidas.')
        ctx['cache'].flush()

    ctx['cache'].flush()
