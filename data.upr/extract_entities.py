#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae entidades locales desde archivos MARC21 XML.

Genera Person, Topic, Organisation, Place, Temporal y Work a partir de los
registros bibliográficos heredados. La salida es una carpeta con dos JSON por
tipo: ``<tipo>.json`` (no enriquecidas) y ``<tipo>.enriched.json`` (enriquecidas
desde una fuente de autoridad externa cuando se usa ``--enrich``).
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

NAMESPACES = {'marc': 'http://www.loc.gov/MARC21/slim'}
SCHEMA_BASE = 'https://bib.upr.edu.cu/schemas/local_entities'

# Dash used as a subject-subdivision separator: not surrounded by digits, so a
# year range such as "1853-1895" is left intact.
SUBDIV_DASH = re.compile(r'(?<!\d)\s*-\s*(?!\d)')

# A 650/600 value that is really a personal name: "Surname, Given ... 1853-1895".
# The character after the first comma must be a letter (a given name), which
# rules out events like "Guerra de independencia, 1895-1898".
PERSON_IN_SUBJECT = re.compile(r'^[^,]+,\s*[A-Za-zÀ-ÿ].*?\b\d{3,4}\b')

# Year or year range at the end of a personal-name string.
TRAILING_DATES = re.compile(r'(\d{3,4})\s*-\s*(\d{0,4})\s*$')


def normalize_text(text):
    """Normaliza el texto para usarlo como clave de deduplicación."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip().lower()


def sf_text(df, code):
    """Devuelve el texto del primer subcampo ``code`` o None."""
    sf = df.find(f'marc:subfield[@code="{code}"]', NAMESPACES)
    return sf.text.strip() if sf is not None and sf.text and sf.text.strip() else None


def sf_all(df, code):
    """Devuelve la lista de textos de todos los subcampos ``code``."""
    out = []
    for sf in df.findall(f'marc:subfield[@code="{code}"]', NAMESPACES):
        if sf.text and sf.text.strip():
            out.append(sf.text.strip())
    return out


# ==============================================================================
# ALMACÉN DE ENTIDADES (un diccionario por tipo, deduplicado y con PID propio)
# ==============================================================================

class EntityStore:
    """Acumula entidades por tipo, deduplicadas, con PID secuencial por tipo."""

    PREFIX = {
        'bf:Person': 'pers',
        'bf:Topic': 'top',
        'bf:Organisation': 'org',
        'bf:Place': 'plc',
        'bf:Temporal': 'tmp',
        'bf:Work': 'wrk',
    }
    FILENAME = {
        'bf:Person': 'persons',
        'bf:Topic': 'topics',
        'bf:Organisation': 'organisations',
        'bf:Place': 'places',
        'bf:Temporal': 'temporals',
        'bf:Work': 'works',
    }

    def __init__(self):
        self.by_type = {etype: {} for etype in self.PREFIX}

    def add(self, etype, key, entity):
        """Inserta ``entity`` bajo ``key`` si no existe ya. Devuelve la entidad
        almacenada (nueva o previa) o None si la clave es vacía."""
        bucket = self.by_type[etype]
        if not key:
            return None
        if key in bucket:
            return bucket[key]
        entity['pid'] = f'{self.PREFIX[etype]}_{len(bucket) + 1:05d}'
        bucket[key] = entity
        return entity


def make_entity(etype, schema_name, **fields):
    """Construye el esqueleto de una entidad con el orden de campos habitual."""
    entity = {
        '$schema': f'{SCHEMA_BASE}/{schema_name}-v0.0.1.json',
        'type': etype,
    }
    entity.update(fields)
    entity['source_catalog'] = 'upr_legacy'
    return entity


# ==============================================================================
# PERSONAS (campos 100, 700, 600 y entradas 650 reclasificadas)
# ==============================================================================

def parse_dates(dates_str):
    """Parsea fechas de nacimiento/muerte de un texto tipo ``1853-1895``."""
    if not dates_str:
        return None, None
    dates_str = dates_str.strip()
    birth = death = None
    if '-' in dates_str and not dates_str.startswith('-'):
        parts = dates_str.split('-')
        if len(parts) == 2:
            b = re.search(r'\d{4}', parts[0])
            d = re.search(r'\d{4}', parts[1])
            if b:
                birth = b.group(0)
            if d:
                death = d.group(0)
    elif 'b.' in dates_str.lower():
        m = re.search(r'\d{4}', dates_str)
        if m:
            birth = m.group(0)
    elif 'd.' in dates_str.lower():
        m = re.search(r'\d{4}', dates_str)
        if m:
            death = m.group(0)
    return birth, death


def person_access_point(name, dates, qualifier=None, numeration=None):
    """Construye el authorized_access_point de una persona según RDA."""
    aap = name
    if qualifier and qualifier not in (name, ''):
        aap += f', {qualifier}'
    if numeration and numeration not in (name, ''):
        aap += f', {numeration}'
    if dates:
        aap += f', {dates}'
    return aap


def add_person(store, name, dates=None, qualifier=None, numeration=None,
               fuller=None):
    """Crea y almacena una persona a partir de sus componentes."""
    name = name.strip(' ,')
    norm_key = normalize_text(name)
    if not norm_key:
        return
    birth, death = parse_dates(dates)
    dates_str = None
    if birth and death:
        dates_str = f'{birth}-{death}'
    elif birth:
        dates_str = f'{birth}-'
    elif death:
        dates_str = f'-{death}'
    aap = person_access_point(name, dates_str, qualifier, numeration)
    entity = make_entity('bf:Person', 'person', name=name,
                         authorized_access_point=aap)
    if birth:
        entity['date_of_birth'] = birth
    if death:
        entity['date_of_death'] = death
    if qualifier:
        entity['qualifier'] = qualifier
    if numeration:
        entity['numeration'] = numeration
    if fuller:
        entity['fuller_form_of_name'] = fuller
    store.add('bf:Person', norm_key, entity)


def extract_persons(record, store):
    """Extrae personas de los campos 100, 700 y 600."""
    for tag in ('100', '700', '600'):
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            raw_name = sf_text(df, 'a')
            if not raw_name:
                continue
            numeration = sf_text(df, 'b')
            qualifier = sf_text(df, 'c')
            dates = sf_text(df, 'd')
            fuller = sf_text(df, 'q')
            non_std = sf_text(df, 'g')
            if non_std:
                qualifier = f'{qualifier}, {non_std}' if qualifier else non_std

            names = [n.strip() for n in raw_name.split(';') if n.strip()] \
                if ';' in raw_name else [raw_name]
            for name in names:
                # En 600 las fechas suelen venir embebidas en $a, no en $d.
                local_dates = dates
                if not local_dates:
                    m = TRAILING_DATES.search(name)
                    if m:
                        local_dates = m.group(0)
                        name = name[:m.start()].strip(' ,')
                add_person(store, name, local_dates, qualifier, numeration, fuller)


# ==============================================================================
# TÓPICOS / LUGARES / TEMPORALES (campos 650, 653, 655, 651, 648)
# ==============================================================================

def split_subject_terms(value):
    """Divide un valor de materia en términos individuales.

    Separa por ``;`` y por el guion de subdivisión, pero conserva intactos los
    rangos de año (``1853-1895``).
    """
    terms = []
    for chunk in re.split(r'\s*;\s*', value):
        for part in SUBDIV_DASH.split(chunk):
            part = part.strip(' -')
            if part:
                terms.append(part)
    return terms


def add_topic(store, term, genre_form):
    norm_key = normalize_text(term)
    if not norm_key:
        return
    entity = make_entity('bf:Topic', 'topic', name=term,
                         authorized_access_point=term, genreForm=genre_form)
    # Reordenar source_catalog tras genreForm para respetar propertiesOrder.
    store.add('bf:Topic', norm_key, entity)


def add_simple(store, etype, schema_name, term):
    norm_key = normalize_text(term)
    if not norm_key:
        return
    entity = make_entity(etype, schema_name, name=term,
                         authorized_access_point=term)
    store.add(etype, norm_key, entity)


def extract_subjects(record, store):
    """Extrae tópicos, lugares y temporales de 650/653/655/651/648.

    - ``650 $a``  → personas (si parece nombre con fechas) o tópicos
    - ``650 $b``  → tópicos adicionales (uso local del export)
    - ``650 $x``  → tópicos (subdivisión general)
    - ``650 $z`` / ``651`` → lugares
    - ``650 $y`` / ``648`` → temporales
    - ``650 $v`` / ``655`` → tópicos genreForm
    - ``653 $a``  → tópicos no controlados
    """
    for df in record.findall('.//marc:datafield[@tag="650"]', NAMESPACES):
        main = sf_text(df, 'a')
        if main:
            if PERSON_IN_SUBJECT.match(main) and '-' in main:
                m = TRAILING_DATES.search(main)
                dates = m.group(0) if m else None
                name = main[:m.start()].strip(' ,') if m else main
                add_person(store, name, dates)
            else:
                for term in split_subject_terms(main):
                    add_topic(store, term, genre_form=False)
        for extra in sf_all(df, 'b') + sf_all(df, 'x'):
            for term in split_subject_terms(extra):
                add_topic(store, term, genre_form=False)
        for place in sf_all(df, 'z'):
            add_simple(store, 'bf:Place', 'place', place)
        for temporal in sf_all(df, 'y'):
            add_simple(store, 'bf:Temporal', 'temporal', temporal)
        for form in sf_all(df, 'v'):
            add_topic(store, form, genre_form=True)

    for df in record.findall('.//marc:datafield[@tag="653"]', NAMESPACES):
        for term in sf_all(df, 'a'):
            for t in split_subject_terms(term):
                add_topic(store, t, genre_form=False)

    for df in record.findall('.//marc:datafield[@tag="655"]', NAMESPACES):
        for term in sf_all(df, 'a'):
            add_topic(store, term, genre_form=True)

    for df in record.findall('.//marc:datafield[@tag="651"]', NAMESPACES):
        for code in ('a', 'z'):
            for place in sf_all(df, code):
                add_simple(store, 'bf:Place', 'place', place)

    for df in record.findall('.//marc:datafield[@tag="648"]', NAMESPACES):
        for code in ('a', 'y'):
            for temporal in sf_all(df, code):
                add_simple(store, 'bf:Temporal', 'temporal', temporal)


# ==============================================================================
# ORGANIZACIONES (campos 110, 710, 111, 711, 610, 611)
# ==============================================================================

def org_access_point(name, subordinate_units, is_conference,
                     conf_place=None, conf_date=None, conf_numbering=None):
    """Construye el authorized_access_point de una organización según RDA."""
    if is_conference:
        aap = name
        conf_parts = [p for p in (conf_numbering, conf_date, conf_place) if p]
        if conf_parts:
            aap += f" ({' : '.join(conf_parts)})"
        return aap
    aap = name
    for unit in subordinate_units:
        aap += f'. {unit}'
    return aap


def extract_organizations(record, store):
    """Extrae organizaciones de 110/710/610 (cuerpos) y 111/711/611 (congresos)."""
    corporate_tags = ('110', '710', '610')
    conference_tags = ('111', '711', '611')

    for df in record.findall('.//marc:datafield', NAMESPACES):
        tag = df.get('tag')
        if tag not in corporate_tags + conference_tags:
            continue
        name = sf_text(df, 'a')
        if not name:
            continue
        subordinate_units = sf_all(df, 'b')
        conf_place = sf_text(df, 'c')
        conf_date = sf_text(df, 'd')
        conf_numbering = sf_text(df, 'n')
        is_conference = tag in conference_tags or bool(conf_date or conf_numbering)

        norm_key = normalize_text(name)
        if not norm_key:
            continue
        aap = org_access_point(name, subordinate_units, is_conference,
                               conf_place, conf_date, conf_numbering)
        entity = make_entity('bf:Organisation', 'organisation', name=name,
                             authorized_access_point=aap)
        if subordinate_units:
            entity['subordinate_units'] = subordinate_units
        if conf_place:
            entity['conference_place'] = conf_place
        if conf_date:
            entity['conference_date'] = conf_date
        if conf_numbering:
            entity['conference_numbering'] = conf_numbering
        entity['conference'] = is_conference
        store.add('bf:Organisation', norm_key, entity)


# ==============================================================================
# OBRAS / TÍTULOS UNIFORMES (campos 130, 630, 730, 240)
# ==============================================================================

def extract_works(record, store):
    """Extrae obras (títulos uniformes) de 130/630/730/240."""
    creator = None
    author_100 = record.find('.//marc:datafield[@tag="100"]', NAMESPACES)
    if author_100 is not None:
        creator = sf_text(author_100, 'a')

    def build_title(df):
        parts = []
        title = sf_text(df, 'a')
        if title:
            parts.append(title)
        for code in ('n', 'p'):
            parts.extend(sf_all(df, code))
        return '. '.join(parts) if parts else None

    for tag in ('130', '630', '730', '240'):
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            title = build_title(df)
            if not title:
                continue
            date = sf_text(df, 'f')
            dedup_key = normalize_text(title)
            if creator:
                dedup_key = f'{dedup_key}||{normalize_text(creator)}'
            aap = f'{creator}. {title}' if creator else title
            if date:
                aap += f' ({date})'
            entity = make_entity('bf:Work', 'work', title=title,
                                 authorized_access_point=aap)
            if creator:
                entity['creator'] = creator
            store.add('bf:Work', dedup_key, entity)


# ==============================================================================
# DETECCIÓN DE POSIBLES DUPLICADOS
# ==============================================================================

def find_potential_duplicates(store, similarity_threshold=0.85):
    """Encuentra posibles duplicados por similitud de texto dentro de cada tipo."""
    duplicates = []
    for etype, bucket in store.by_type.items():
        entities = list(bucket.values())
        if len(entities) < 2:
            continue
        print(f'  Buscando duplicados en {etype} ({len(entities)} entidades)...')
        field = 'title' if etype == 'bf:Work' else 'name'
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                t1 = entities[i].get(field, '')
                t2 = entities[j].get(field, '')
                if not t1 or not t2:
                    continue
                similarity = SequenceMatcher(None, t1.lower(), t2.lower()).ratio()
                if similarity_threshold <= similarity < 1.0:
                    duplicates.append({
                        'type': etype,
                        'entity1': entities[i],
                        'entity2': entities[j],
                        'similarity': similarity,
                    })
    return duplicates


# ==============================================================================
# PROCESAMIENTO DE ARCHIVOS
# ==============================================================================

def process_file(xml_path, store, total_records_processed):
    """Procesa un archivo XML y extrae todas las entidades."""
    print(f'\n📄 Procesando: {xml_path}')
    try:
        root = ET.parse(xml_path).getroot()
    except Exception as e:
        print(f'  ❌ Error al leer el archivo: {e}')
        return 0

    records = root.findall('.//marc:record', NAMESPACES)
    print(f'  Registros encontrados: {len(records)}')

    for record in records:
        total_records_processed += 1
        if total_records_processed % 1000 == 0:
            total = sum(len(b) for b in store.by_type.values())
            print(f'  ... {total_records_processed} registros. Entidades: {total}')
        extract_persons(record, store)
        extract_subjects(record, store)
        extract_organizations(record, store)
        extract_works(record, store)

    total = sum(len(b) for b in store.by_type.values())
    print(f'  ✅ Archivo completado. Entidades únicas hasta ahora: {total}')
    return len(records)


# ==============================================================================
# SALIDA
# ==============================================================================

def write_output(store, output_dir):
    """Escribe dos JSON por tipo: ``<tipo>.json`` y ``<tipo>.enriched.json``."""
    os.makedirs(output_dir, exist_ok=True)
    summary = {}
    for etype, bucket in store.by_type.items():
        plain, enriched = [], []
        for entity in bucket.values():
            entity = dict(entity)
            if entity.pop('_enriched', False):
                enriched.append(entity)
            else:
                plain.append(entity)
        name = EntityStore.FILENAME[etype]
        with open(os.path.join(output_dir, f'{name}.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(plain, f, ensure_ascii=False, indent=2)
        with open(os.path.join(output_dir, f'{name}.enriched.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
        summary[etype] = (len(plain), len(enriched))
    return summary


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Extrae entidades locales desde archivos MARC21 XML.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Extracción base (sin red): una carpeta con dos JSON por tipo
  python extract_entities.py -i legacy/db/*/marc21.mrcxml -o legacy/entities

  # Con enriquecimiento externo acotado para pruebas
  python extract_entities.py -i legacy/db/BCT/marc21.mrcxml -o /tmp/ent \\
      --enrich --enrich-limit 20 --geonames-user MIUSER
        """,
    )
    parser.add_argument('-i', '--input', nargs='+', required=True,
                        help='Uno o más archivos MARC21 XML de entrada.')
    parser.add_argument('-o', '--output', required=True,
                        help='Carpeta de salida (dos JSON por tipo de entidad).')
    parser.add_argument('--similarity', type=float, default=0.85,
                        help='Umbral de similitud para el reporte de duplicados.')
    parser.add_argument('--no-duplicates-report', action='store_true',
                        help='No generar el reporte de posibles duplicados.')
    parser.add_argument('--enrich', action='store_true',
                        help='Enriquecer las entidades con fuentes externas.')
    parser.add_argument('--enrich-types', default=None,
                        help='Tipos a enriquecer, separados por coma '
                             '(person,topic,organisation,place,temporal,work).')
    parser.add_argument('--enrich-limit', type=int, default=None,
                        help='Máximo de entidades a enriquecer por tipo (pruebas).')
    parser.add_argument('--geonames-user', default=os.environ.get('GEONAMES_USER'),
                        help='Usuario de GeoNames (o variable GEONAMES_USER).')
    parser.add_argument('--worldcat-key', default=os.environ.get('WORLDCAT_KEY'),
                        help='Clave de la WorldCat Search API (o WORLDCAT_KEY).')
    args = parser.parse_args()

    for xml_path in args.input:
        if not os.path.exists(xml_path):
            print(f'❌ Error: El archivo no existe: {xml_path}')
            sys.exit(1)

    print('=' * 80)
    print('🚀 EXTRACCIÓN DE ENTIDADES LOCALES DESDE MARC21 XML')
    print('=' * 80)
    print(f'\nArchivos de entrada: {len(args.input)}')
    print(f'Carpeta de salida: {args.output}')

    store = EntityStore()
    total_records = 0
    for xml_path in args.input:
        total_records += process_file(xml_path, store, total_records)

    if args.enrich:
        from enrichers import enrich_store
        enrich_store(store, types=args.enrich_types, limit=args.enrich_limit,
                     geonames_user=args.geonames_user,
                     worldcat_key=args.worldcat_key)

    summary = write_output(store, args.output)

    print('\n' + '=' * 80)
    print('📊 ESTADÍSTICAS FINALES')
    print('=' * 80)
    print(f'Total de registros procesados: {total_records}')
    print('\nEntidades por tipo (no enriquecidas / enriquecidas):')
    for etype in sorted(summary):
        plain, enriched = summary[etype]
        print(f'  {etype}: {plain} / {enriched}')

    if not args.no_duplicates_report:
        print('\n' + '=' * 80)
        print('🔍 ANÁLISIS DE POSIBLES DUPLICADOS')
        print('=' * 80)
        duplicates = find_potential_duplicates(store, args.similarity)
        if duplicates:
            print(f'\n⚠️  {len(duplicates)} posibles duplicados (primeros 20):')
            for i, dup in enumerate(duplicates[:20], 1):
                field = 'title' if dup['type'] == 'bf:Work' else 'name'
                print(f"  {i}. [{dup['type']}] "
                      f"{dup['entity1'].get(field)} ≈ {dup['entity2'].get(field)} "
                      f"({dup['similarity']:.2%})")
            report_path = os.path.join(args.output, 'duplicates.json')
            report = [{
                'type': d['type'],
                'similarity': d['similarity'],
                'entity1_pid': d['entity1']['pid'],
                'entity2_pid': d['entity2']['pid'],
            } for d in duplicates]
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f'\n💾 Reporte completo: {report_path}')
        else:
            print('\n✅ No se encontraron posibles duplicados')

    print('\n' + '=' * 80)
    print('✅ ¡PROCESO COMPLETADO!')
    print('=' * 80)
    print(f'\nCarpeta de entidades: {args.output}\n')


if __name__ == '__main__':
    main()
