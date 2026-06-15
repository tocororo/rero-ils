import os
import re
import xml.etree.ElementTree as ET

# Paths relative to this file so the script works regardless of CWD.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_DIR = os.path.join(BASE_DIR, 'legacy')
DB_DIR = os.path.join(LEGACY_DIR, 'db')

DATABASES = ['BCT', 'BECSH', 'FCF', 'FCP']

# Default 008 used when the value is missing or cannot be parsed.
DEFAULT_008 = '200101b' + ' ' * 33  # exactly 40 chars


def load_countries():
    path = os.path.join(LEGACY_DIR, 'countries.xml')
    tree = ET.parse(path)
    root = tree.getroot()
    countries = root.find('{info:lc/xmlns/codelist-v1}countries')
    return [c.find('{info:lc/xmlns/codelist-v1}code').text
            for c in countries.findall('{info:lc/xmlns/codelist-v1}country')]


def load_languages():
    path = os.path.join(LEGACY_DIR, 'languages.xml')
    tree = ET.parse(path)
    root = tree.getroot()
    languages = root.find('{info:lc/xmlns/codelist-v1}languages')
    return [c.find('{info:lc/xmlns/codelist-v1}code').text
            for c in languages.findall('{info:lc/xmlns/codelist-v1}language')]


def get_substrings(value: str, min_size=2, max_size=3):
    subs = []
    for i in range(len(value)):
        for j in range(i + min_size, min(i + max_size + 1, len(value) + 1)):
            subs.append(value[i:j])
    return subs


def index_reversed(value, sub):
    """Return the last index where sub starts in value, or -1 if not found."""
    if not sub:
        return -1
    step = len(sub)
    for i in range(len(value) - step, -1, -1):
        if value[i:i + step] == sub:
            return i
    return -1


def fix_upr_tag8(value: str, countries, languages):
    """Attempt to build a valid 40-character MARC21 008 from a malformed value.

    Returns a 40-character string on success, or DEFAULT_008 when the value
    is too short or unrecognisable.
    """

    # Normalise a known error variant
    if 'English' in value:
        value = value.replace('English', 'eng')

    # ------------------------------------------------------------------ #
    # Pattern 1: value starts with 6 digits (YYMMDD entry date)           #
    # ------------------------------------------------------------------ #
    if re.match(r'^\d{6}', value):
        c00_05_date = value[0:6]
        rest = value[6:]

        subs = get_substrings(rest)

        c15_17_country = ''
        for sub in subs:
            if sub in countries:
                c15_17_country = sub
                break

        subs_rev = list(reversed(subs))
        c35_37_language = ''
        for sub in subs_rev:
            if sub in languages:
                c35_37_language = sub
                break

        # If country or language could not be detected, return default.
        if not c15_17_country or not c35_37_language:
            return DEFAULT_008

        # Search for country starting after the entry date (pos 6) so the
        # code cannot accidentally match bytes inside the 6-digit date prefix.
        country_start = value.index(c15_17_country, 6)
        lang_start = index_reversed(value, c35_37_language)

        # The language code must appear after the country code.
        if lang_start <= country_start:
            return DEFAULT_008

        # Bytes between entry date and country code should hold positions
        # 06-14 (type of date + two dates). Preserve them when legible.
        c06_14_raw = value[6:country_start].ljust(9)[:9]
        valid_date_types = set('abcdeikmnpqrstu|')
        if c06_14_raw[0] not in valid_date_types:
            c06_14_raw = 'b' + c06_14_raw[1:]
        c06_14 = c06_14_raw

        # Material-specific bytes (pos 18-34) live between the END of the
        # country code and the START of the language code.
        c18_34 = value[country_start + len(c15_17_country):lang_start]

        # Parse material-specific bytes from right to left, tolerating a
        # string that is shorter than expected.
        def safe_right(pos_from_end, valid_chars, default='|'):
            idx = len(c18_34) - pos_from_end
            if idx >= 0 and len(c18_34) > idx and c18_34[idx] in valid_chars:
                return c18_34[idx]
            return default

        try:
            step = 1
            c34 = safe_right(step, '#abcd|'); step += 1
            c33 = safe_right(step, '01cdefhijmpsu|'); step += 1
            c32 = '|'; step += 1
            c31 = safe_right(step, '01|'); step += 1
            c30 = safe_right(step, '01|'); step += 1
            c29 = safe_right(step, '01|'); step += 1
            c28 = safe_right(step, '#acfilmosu z|'); step += 1
            c24_27 = ''
            for _ in range(4):
                c24_27 += safe_right(step, '#abcdefijklmnopqrstuvwz2|', '#')
                step += 1
            c24_27 = c24_27[::-1]  # collected right-to-left, reverse
            c23 = safe_right(step, '#abcdfrs|'); step += 1
            c22 = safe_right(step, '#abcdefgj|', '#'); step += 1
            c18_21 = ''
            for _ in range(4):
                c18_21 += safe_right(step, '#abcdefghijklmop|', '|')
                step += 1
            c18_21 = c18_21[::-1]

            c38_39 = value[lang_start + len(c35_37_language):]
            c38 = '#'
            c39 = 'd'
            if len(c38_39) >= 2:
                if c38_39[0] in '#sdxro|':
                    c38 = c38_39[0]
                if c38_39[1] in '#cdu|':
                    c39 = c38_39[1]
            elif len(c38_39) == 1:
                if c38_39[0] in '#cdu|':
                    c39 = c38_39[0]

            result = (c00_05_date + c06_14 + c15_17_country.ljust(3) +
                      c18_21 + c22 + c23 + c24_27 + c28 + c29 + c30 +
                      c31 + c32 + c33 + c34 +
                      c35_37_language.ljust(3) + c38 + c39)
            return result if len(result) == 40 else DEFAULT_008

        except Exception:
            return DEFAULT_008

    # ------------------------------------------------------------------ #
    # Pattern 2: DD/MM or DD/YYYY (thesis dates)                          #
    # ------------------------------------------------------------------ #
    m = re.match(r'^(\d{1,2})\s*/\s*(\d{2,4})', value)
    if m:
        day, year_part = m.group(1), m.group(2)
        day = day.zfill(2)
        year_suffix = year_part[-2:] if len(year_part) >= 2 else '00'
        result = '{0}{1}01b'.format(year_suffix, day)
        return result.ljust(40)

    # ------------------------------------------------------------------ #
    # Pattern 3: plain 4-digit year (e.g. "2011")                        #
    # ------------------------------------------------------------------ #
    m = re.match(r'^(\d{4})$', value.strip())
    if m:
        year = m.group(1)
        result = '{0}0101b'.format(year[2:])
        return result.ljust(40)

    # ------------------------------------------------------------------ #
    # Catch-all: value is unrecognisable — use a neutral default          #
    # ------------------------------------------------------------------ #
    return DEFAULT_008


def _write_xml_collection(records, output_path):
    """Write a list of record elements as a MARC21 collection XML file."""
    ET.register_namespace('', 'http://www.loc.gov/MARC21/slim')
    root = ET.Element('collection', {'xmlns': 'http://www.loc.gov/MARC21/slim'})
    tree = ET.ElementTree(root)
    for rec in records:
        root.append(rec)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)


def process_database(db_name, countries, languages):
    """Pre-process one library's MARC21 XML export.

    Reads  legacy/db/<db_name>/marc21.mrcxml
    Writes legacy/db/<db_name>/marc21.fix.mrcxml  (valid/fixed records)
           legacy/db/<db_name>/marc21.fix.error.mrcxml  (unfixable records)

    Returns (total_count, good_records, error_records, stats_dict).
    """
    input_path = os.path.join(DB_DIR, db_name, 'marc21.test.mrcxml')
    ET.register_namespace('', 'http://www.loc.gov/MARC21/slim')
    tree = ET.parse(input_path)
    root = tree.getroot()

    good = []
    errors = []
    stats = dict(total=0, already_ok=0, fixed=0, default_added=0, unfixable=0, no_id=0)

    for record in root.findall('{http://www.loc.gov/MARC21/slim}record'):
        stats['total'] += 1

        # Add <library> tag with the db name
        lib_tag = ET.Element('library')
        lib_tag.text = db_name
        record.append(lib_tag)

        # Prefix 001 with REROILS:
        cf001 = record.find('{http://www.loc.gov/MARC21/slim}controlfield[@tag="001"]')
        if cf001 is not None and not cf001.text.startswith('REROILS:'):
            cf001.text = 'REROILS:' + cf001.text

        # Add document-type field 339
        cf006 = record.find('{http://www.loc.gov/MARC21/slim}controlfield[@tag="006"]')
        is_thesis = (
            record.find('{http://www.loc.gov/MARC21/slim}datafield[@tag="502"]') is not None or
            (cf006 is not None and cf006.text == 'Tesis')
        )
        df339 = ET.SubElement(record, '{http://www.loc.gov/MARC21/slim}datafield',
                              tag='339', ind1=' ', ind2=' ')
        ET.SubElement(df339, '{http://www.loc.gov/MARC21/slim}subfield',
                      code='a').text = 'docmaintype_book'
        ET.SubElement(df339, '{http://www.loc.gov/MARC21/slim}subfield',
                      code='b').text = 'docsubtype_thesis' if is_thesis else 'docsubtype_other_book'

        # Normalise 008
        cf008 = record.find('{http://www.loc.gov/MARC21/slim}controlfield[@tag="008"]')
        if cf008 is None:
            # No 008 at all — add a neutral default
            cf008 = ET.SubElement(record, '{http://www.loc.gov/MARC21/slim}controlfield',
                                  tag='008')
            cf008.text = DEFAULT_008
            stats['default_added'] += 1
            good.append(record)
        elif len(cf008.text) == 40:
            stats['already_ok'] += 1
            good.append(record)
        else:
            fixed = fix_upr_tag8(cf008.text, countries, languages)
            if fixed and len(fixed) == 40:
                cf008.text = fixed
                stats['fixed'] += 1
                good.append(record)
            else:
                stats['unfixable'] += 1
                errors.append(record)

        if cf001 is None:
            stats['no_id'] += 1

    fix_path = os.path.join(DB_DIR, db_name, 'marc21.fix.mrcxml')
    err_path = os.path.join(DB_DIR, db_name, 'marc21.fix.error.mrcxml')
    _write_xml_collection(good, fix_path)
    _write_xml_collection(errors, err_path)

    return good, errors, stats


def main():
    countries = load_countries()
    languages = load_languages()

    all_good = []
    all_errors = []
    grand_stats = {}

    print(f"{'DB':<8} {'total':>7} {'ok':>7} {'fixed':>7} {'default':>8} {'error':>7}")
    print('-' * 50)

    for db in DATABASES:
        good, errors, stats = process_database(db, countries, languages)
        all_good.extend(good)
        all_errors.extend(errors)
        grand_stats[db] = stats
        print(f"{db:<8} {stats['total']:>7} {stats['already_ok']:>7} "
              f"{stats['fixed']:>7} {stats['default_added']:>8} {stats['unfixable']:>7}")

    print('-' * 50)
    totals = {k: sum(s[k] for s in grand_stats.values())
              for k in ['total', 'already_ok', 'fixed', 'default_added', 'unfixable']}
    print(f"{'TOTAL':<8} {totals['total']:>7} {totals['already_ok']:>7} "
          f"{totals['fixed']:>7} {totals['default_added']:>8} {totals['unfixable']:>7}")

    # Write combined output for marc21tojson conversion
    combined_fix = os.path.join(LEGACY_DIR, 'marc21.fix.mrcxml')
    combined_err = os.path.join(LEGACY_DIR, 'marc21.fix.error.mrcxml')
    _write_xml_collection(all_good, combined_fix)
    _write_xml_collection(all_errors, combined_err)

    print(f'\nOutputs written:')
    print(f'  {combined_fix}  ({len(all_good)} records)')
    print(f'  {combined_err}  ({len(all_errors)} records)')
    print()
    print('Next step — convert to rero-ils JSON (per database):')
    print('  uv run scripts/import_legacy.upr')
    print()
    print('  Or manually for each DB:')
    for db in DATABASES:
        input_path = os.path.join(DB_DIR, db, 'marc21.fix.mrcxml')
        output_path = os.path.join(DB_DIR, db, 'marc21.fix.json')
        err_path = os.path.join(DB_DIR, db, 'marc21.tojson.error.mrcxml')
        print(f'  invenio reroils documents marc21tojson -t rero -v -r \\')
        print(f'    {input_path} \\')
        print(f'    {output_path} \\')
        print(f'    {err_path}')


if __name__ == '__main__':
    main()
