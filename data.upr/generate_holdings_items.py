"""Generate holdings.json and items.json from per-library marc21.fix.mrcxml files.

Each subfolder in legacy/db/ corresponds to a library.  Every record in that
folder is a physical copy that must appear as a holding + item in that library.

Usage:
    python data.upr/generate_holdings_items.py

Output (in data.upr/legacy/):
    holdings.json   — one holding per document per library
    items.json      — one item per holding

Load into rero-ils afterwards with:
    invenio reroils fixtures create --pid_type hold \
        --schema 'https://bib.upr.edu.cu/schemas/holdings/holding-v0.0.1.json' \
        --append --dont-stop data.upr/legacy/holdings.json
    invenio reroils fixtures create --pid_type item \
        --schema 'https://bib.upr.edu.cu/schemas/items/item-v0.0.1.json' \
        --append --dont-stop data.upr/legacy/items.json
    invenio reroils index reindex -t hold --yes-i-know
    invenio reroils index reindex -t item --yes-i-know
    invenio reroils index run --raise-on-error
"""
import json
import os
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_DIR = os.path.join(BASE_DIR, 'legacy')
DB_DIR = os.path.join(LEGACY_DIR, 'db')

BASE_URL = 'https://bib.upr.edu.cu'
HOLD_SCHEMA = f'{BASE_URL}/schemas/holdings/holding-v0.0.1.json'
ITEM_SCHEMA = f'{BASE_URL}/schemas/items/item-v0.0.1.json'

MARC_NS = 'http://www.loc.gov/MARC21/slim'

# Maps each legacy DB folder to its rero-ils identifiers.
# location_pid → Sala General de cada biblioteca (primer punto de préstamo).
# item_type_pid → "Préstamo estándar" de la organización correspondiente.
DB_CONFIG = {
    'BCT':   {'lib': '1', 'org': '1', 'loc': '1', 'itty': '1'},
    'BECSH': {'lib': '2', 'org': '1', 'loc': '3', 'itty': '1'},
    'FCF':   {'lib': '3', 'org': '1', 'loc': '5', 'itty': '1'},
    'FCP':   {'lib': '4', 'org': '1', 'loc': '7', 'itty': '1'},
}


def ref(resource, pid):
    return {'$ref': f'{BASE_URL}/api/{resource}/{pid}'}


def extract_doc_pid(record):
    """Return the rero-ils document pid from field 001.

    The marc21tojson rero converter turns "REROILS:XXX" → pid "XXX".
    Returns None if the field is absent or has an unexpected format.
    """
    cf = record.find(f'{{{MARC_NS}}}controlfield[@tag="001"]')
    if cf is None or not cf.text:
        return None
    parts = cf.text.strip().split(':', 1)
    if len(parts) == 2 and parts[0] == 'REROILS':
        return parts[1]
    return None


def extract_call_number(record):
    """Return a call number from fields 082 (Dewey), 084, or 050 (LC)."""
    for tag, code in [('082', 'a'), ('084', 'a'), ('050', 'a')]:
        df = record.find(f'{{{MARC_NS}}}datafield[@tag="{tag}"]')
        if df is not None:
            sf = df.find(f'{{{MARC_NS}}}subfield[@code="{code}"]')
            if sf is not None and sf.text:
                return sf.text.strip()
    return None


def main():
    holdings = []
    items = []
    hold_pid = 1
    item_pid = 1
    stats = {}

    seen_doc_pids = {}   # doc_pid → first db that claimed it (collision detection)

    for db, cfg in DB_CONFIG.items():
        mrcxml = os.path.join(DB_DIR, db, 'marc21.fix.mrcxml')
        if not os.path.exists(mrcxml):
            print(f'  WARNING: {mrcxml} not found — skipping {db}')
            continue

        tree = ET.parse(mrcxml)
        root = tree.getroot()
        records = root.findall(f'{{{MARC_NS}}}record')

        count_ok = 0
        count_skip = 0
        count_collision = 0

        for record in records:
            doc_pid = extract_doc_pid(record)
            if doc_pid is None:
                count_skip += 1
                continue

            # Warn if the same doc_pid appears in more than one database.
            if doc_pid in seen_doc_pids:
                prev_db = seen_doc_pids[doc_pid]
                if prev_db != db:
                    print(f'  COLLISION: doc pid={doc_pid!r} appears in both '
                          f'{prev_db} and {db} — both holdings will be created')
                    count_collision += 1
            else:
                seen_doc_pids[doc_pid] = db

            call_number = extract_call_number(record)
            barcode = f'{db}-{doc_pid}'

            holding = {
                '$schema': HOLD_SCHEMA,
                'pid': str(hold_pid),
                'holdings_type': 'standard',
                'document': ref('documents', doc_pid),
                'organisation': ref('organisations', cfg['org']),
                'library': ref('libraries', cfg['lib']),
                'location': ref('locations', cfg['loc']),
                'circulation_category': ref('item_types', cfg['itty']),
            }
            if call_number:
                holding['call_number'] = call_number

            item = {
                '$schema': ITEM_SCHEMA,
                'pid': str(item_pid),
                'type': 'standard',
                'status': 'on_shelf',
                'barcode': barcode,
                'document': ref('documents', doc_pid),
                'holding': ref('holdings', str(hold_pid)),
                'organisation': ref('organisations', cfg['org']),
                'library': ref('libraries', cfg['lib']),
                'location': ref('locations', cfg['loc']),
                'item_type': ref('item_types', cfg['itty']),
            }
            if call_number:
                item['call_number'] = call_number

            holdings.append(holding)
            items.append(item)
            hold_pid += 1
            item_pid += 1
            count_ok += 1

        stats[db] = dict(ok=count_ok, skip=count_skip, collision=count_collision)

    # Write output files
    hold_path = os.path.join(LEGACY_DIR, 'holdings.json')
    item_path = os.path.join(LEGACY_DIR, 'items.json')

    with open(hold_path, 'w', encoding='utf-8') as f:
        json.dump(holdings, f, ensure_ascii=False, indent=2)
    with open(item_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print()
    print(f"{'DB':<8} {'ok':>7} {'sin 001':>8} {'colisión':>10}")
    print('-' * 38)
    for db, s in stats.items():
        print(f"{db:<8} {s['ok']:>7} {s['skip']:>8} {s['collision']:>10}")
    print('-' * 38)
    total_ok = sum(s['ok'] for s in stats.values())
    print(f"{'TOTAL':<8} {total_ok:>7}")
    print()
    print('Ficheros generados:')
    print(f'  {hold_path}  ({len(holdings)} holdings)')
    print(f'  {item_path}  ({len(items)} items)')
    print()
    print('Siguientes pasos:')
    print(f"  invenio reroils fixtures create --pid_type hold \\")
    print(f"    --schema '{HOLD_SCHEMA}' --append --dont-stop \\")
    print(f"    {hold_path}")
    print()
    print(f"  invenio reroils fixtures create --pid_type item \\")
    print(f"    --schema '{ITEM_SCHEMA}' --append --dont-stop \\")
    print(f"    {item_path}")
    print()
    print("  invenio reroils index reindex -t hold --yes-i-know")
    print("  invenio reroils index reindex -t item --yes-i-know")
    print("  invenio reroils index run --raise-on-error")


if __name__ == '__main__':
    main()
