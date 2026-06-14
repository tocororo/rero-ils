#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extraer entidades locales desde archivos MARC XML.
Procesa múltiples archivos y genera un único JSON con todas las entidades únicas.
"""

import os
import sys
import json
import re
import argparse
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

# Configuración de Namespaces de MARC21
NAMESPACES = {'marc': 'http://www.loc.gov/MARC21/slim'}

def normalize_text(text):
    """Normaliza el texto para usarlo como clave de deduplicación."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip().lower()

# ==============================================================================
# EXTRACCIÓN DE PERSONAS (Campos 100, 700)
# ==============================================================================

def extract_persons(record, entities_dict):
    """Extrae personas de los campos MARC 100 y 700."""
    
    def parse_dates(dates_str):
        """Parsea el subcampo $d de MARC para extraer birth/death."""
        if not dates_str:
            return None, None
        
        dates_str = dates_str.strip()
        birth = None
        death = None
        
        if '-' in dates_str and not dates_str.startswith('-'):
            parts = dates_str.split('-')
            if len(parts) == 2:
                birth_year = re.search(r'\d{4}', parts[0])
                death_year = re.search(r'\d{4}', parts[1])
                if birth_year:
                    birth = birth_year.group(0)
                if death_year:
                    death = death_year.group(0)
        elif 'b.' in dates_str.lower():
            match = re.search(r'\d{4}', dates_str)
            if match:
                birth = match.group(0)
        elif 'd.' in dates_str.lower():
            match = re.search(r'\d{4}', dates_str)
            if match:
                death = match.group(0)
        
        return birth, death
    
    def build_authorized_access_point(name, dates, qualifier=None, numeration=None):
        """Construye el authorized_access_point según reglas RDA."""
        aap = name
        if qualifier and qualifier not in [name, '']:
            aap += f", {qualifier}"
        if numeration and numeration not in [name, '']:
            aap += f", {numeration}"
        if dates:
            aap += f", {dates}"
        return aap
    
    for tag in ['100', '700']:
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            name_sf = df.find('marc:subfield[@code="a"]', NAMESPACES)
            numeration_sf = df.find('marc:subfield[@code="b"]', NAMESPACES)
            titles_sf = df.find('marc:subfield[@code="c"]', NAMESPACES)
            dates_sf = df.find('marc:subfield[@code="d"]', NAMESPACES)
            fuller_sf = df.find('marc:subfield[@code="q"]', NAMESPACES)
            non_std_sf = df.find('marc:subfield[@code="g"]', NAMESPACES)
            
            if name_sf is None or not name_sf.text:
                continue
            
            raw_name = name_sf.text.strip()
            
            if ';' in raw_name:
                names = [n.strip() for n in raw_name.split(';') if n.strip()]
            else:
                names = [raw_name]
            
            for name in names:
                norm_key = normalize_text(name)
                if not norm_key or norm_key in entities_dict:
                    continue
                
                numeration = numeration_sf.text.strip() if numeration_sf is not None and numeration_sf.text else None
                qualifier = titles_sf.text.strip() if titles_sf is not None and titles_sf.text else None
                dates = dates_sf.text.strip() if dates_sf is not None and dates_sf.text else None
                fuller = fuller_sf.text.strip() if fuller_sf is not None and fuller_sf.text else None
                
                if non_std_sf is not None and non_std_sf.text:
                    if qualifier:
                        qualifier += f", {non_std_sf.text.strip()}"
                    else:
                        qualifier = non_std_sf.text.strip()
                
                birth, death = parse_dates(dates)
                
                dates_str = None
                if birth and death:
                    dates_str = f"{birth}-{death}"
                elif birth:
                    dates_str = f"{birth}-"
                elif death:
                    dates_str = f"-{death}"
                
                aap = build_authorized_access_point(name, dates_str, qualifier, numeration)
                pid = f"pers_{len(entities_dict) + 1:05d}"
                
                entity = {
                    "$schema": "https://bib.upr.edu.cu/schemas/local_entities/person-v0.0.1.json",
                    "pid": pid,
                    "type": "bf:Person",
                    "name": name,
                    "authorized_access_point": aap
                }
                
                if birth:
                    entity["date_of_birth"] = birth
                if death:
                    entity["date_of_death"] = death
                if qualifier:
                    entity["qualifier"] = qualifier
                if numeration:
                    entity["numeration"] = numeration
                if fuller:
                    entity["fuller_form_of_name"] = fuller
                
                entity["source_catalog"] = "upr_legacy"
                entities_dict[norm_key] = entity

# ==============================================================================
# EXTRACCIÓN DE TÓPICOS/MATERIAS (Campos 650, 655)
# ==============================================================================

def extract_topics(record, entities_dict):
    """
    Extrae materias (tópicos) de los campos MARC 650 y 655.
    - 650: Materias temáticas (genreForm: false)
    - 655: Términos de género/forma (genreForm: true)
    """
    
    def build_topic_string(df):
        """Construye la cadena completa del tópico concatenando subdivisiones."""
        parts = []
        for code in ['a', 'b', 'x', 'z', 'v']:
            sf = df.find(f'marc:subfield[@code="{code}"]', NAMESPACES)
            if sf is not None and sf.text:
                parts.append(sf.text.strip())
        return " - ".join(parts) if parts else None
    
    def extract_single_topic(df, is_genre_form):
        """Extrae un tópico individual de un datafield."""
        topic_str = build_topic_string(df)
        
        if not topic_str:
            return
        
        norm_key = normalize_text(topic_str)
        if not norm_key or norm_key in entities_dict:
            return
        
        pid = f"top_{len(entities_dict) + 1:05d}"
        
        entity = {
            "$schema": "https://bib.upr.edu.cu/schemas/local_entities/topic-v0.0.1.json",
            "pid": pid,
            "type": "bf:Topic",
            "name": topic_str,
            "authorized_access_point": topic_str,
            "genreForm": is_genre_form,
            "source_catalog": "upr_legacy"
        }
        
        entities_dict[norm_key] = entity
    
    for df in record.findall('.//marc:datafield[@tag="650"]', NAMESPACES):
        extract_single_topic(df, is_genre_form=False)
    
    for df in record.findall('.//marc:datafield[@tag="655"]', NAMESPACES):
        extract_single_topic(df, is_genre_form=True)

# ==============================================================================
# EXTRACCIÓN DE ORGANIZACIONES (Campos 110, 710)
# ==============================================================================

def extract_organizations(record, entities_dict):
    """
    Extrae organizaciones de los campos MARC 110 y 710.
    Detecta automáticamente si es conferencia basado en $c, $d, $n.
    """
    
    def build_authorized_access_point(name, subordinate_units, is_conference, 
                                     conf_place=None, conf_date=None, conf_numbering=None):
        """Construye el authorized_access_point según reglas RDA."""
        if is_conference:
            aap = name
            conf_parts = []
            if conf_numbering:
                conf_parts.append(conf_numbering)
            if conf_date:
                conf_parts.append(conf_date)
            if conf_place:
                conf_parts.append(conf_place)
            
            if conf_parts:
                aap += f" ({' : '.join(conf_parts)})"
            
            return aap
        else:
            aap = name
            if subordinate_units:
                for unit in subordinate_units:
                    aap += f". {unit}"
            return aap
    
    def extract_single_organization(df):
        """Extrae una organización individual de un datafield 110 o 710."""
        
        name_sf = df.find('marc:subfield[@code="a"]', NAMESPACES)
        if name_sf is None or not name_sf.text:
            return
        
        name = name_sf.text.strip()
        
        subordinate_units = []
        for b_sf in df.findall('marc:subfield[@code="b"]', NAMESPACES):
            if b_sf.text:
                subordinate_units.append(b_sf.text.strip())
        
        conf_place_sf = df.find('marc:subfield[@code="c"]', NAMESPACES)
        conf_date_sf = df.find('marc:subfield[@code="d"]', NAMESPACES)
        conf_numbering_sf = df.find('marc:subfield[@code="n"]', NAMESPACES)
        
        conf_place = conf_place_sf.text.strip() if conf_place_sf is not None and conf_place_sf.text else None
        conf_date = conf_date_sf.text.strip() if conf_date_sf is not None and conf_date_sf.text else None
        conf_numbering = conf_numbering_sf.text.strip() if conf_numbering_sf is not None and conf_numbering_sf.text else None
        
        is_conference = bool(conf_date or conf_numbering)
        
        norm_key = normalize_text(name)
        if not norm_key or norm_key in entities_dict:
            return
        
        pid = f"org_{len(entities_dict) + 1:05d}"
        
        aap = build_authorized_access_point(
            name, subordinate_units, is_conference,
            conf_place, conf_date, conf_numbering
        )
        
        entity = {
            "$schema": "https://bib.upr.edu.cu/schemas/local_entities/organisation-v0.0.1.json",
            "pid": pid,
            "type": "bf:Organisation",
            "name": name,
            "authorized_access_point": aap,
            "conference": is_conference,
            "source_catalog": "upr_legacy"
        }
        
        if subordinate_units:
            entity["subordinate_units"] = subordinate_units
        if conf_place:
            entity["conference_place"] = conf_place
        if conf_date:
            entity["conference_date"] = conf_date
        if conf_numbering:
            entity["conference_numbering"] = conf_numbering
        
        entities_dict[norm_key] = entity
    
    for tag in ['110', '710']:
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            extract_single_organization(df)

# ==============================================================================
# EXTRACCIÓN DE LUGARES (Campos 151, 751)
# ==============================================================================

def extract_places(record, entities_dict):
    """
    Extrae lugares geográficos de los campos MARC 151 y 751.
    Estos son lugares independientes, no subdivisiones dentro de materias.
    """
    
    def build_place_string(df):
        """Construye la cadena completa del lugar."""
        parts = []
        for code in ['a', 'z']:
            sf = df.find(f'marc:subfield[@code="{code}"]', NAMESPACES)
            if sf is not None and sf.text:
                parts.append(sf.text.strip())
        return " - ".join(parts) if parts else None
    
    def extract_single_place(df):
        """Extrae un lugar individual de un datafield 151 o 751."""
        place_str = build_place_string(df)
        
        if not place_str:
            return
        
        norm_key = normalize_text(place_str)
        if not norm_key or norm_key in entities_dict:
            return
        
        pid = f"plc_{len(entities_dict) + 1:05d}"
        
        entity = {
            "$schema": "https://bib.upr.edu.cu/schemas/local_entities/place-v0.0.1.json",
            "pid": pid,
            "type": "bf:Place",
            "name": place_str,
            "authorized_access_point": place_str,
            "source_catalog": "upr_legacy"
        }
        
        entities_dict[norm_key] = entity
    
    for tag in ['151', '751']:
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            extract_single_place(df)

# ==============================================================================
# EXTRACCIÓN DE TÉRMINOS TEMPORALES (Campos 148, 758)
# ==============================================================================

def extract_temporals(record, entities_dict):
    """
    Extrae términos temporales/cronológicos de los campos MARC 148 y 758.
    Estos son términos independientes, no subdivisiones dentro de materias.
    """
    
    def build_temporal_string(df):
        """Construye la cadena completa del término temporal."""
        parts = []
        for code in ['a', 'y']:
            sf = df.find(f'marc:subfield[@code="{code}"]', NAMESPACES)
            if sf is not None and sf.text:
                parts.append(sf.text.strip())
        return " - ".join(parts) if parts else None
    
    def extract_single_temporal(df):
        """Extrae un término temporal individual de un datafield 148 o 758."""
        temporal_str = build_temporal_string(df)
        
        if not temporal_str:
            return
        
        norm_key = normalize_text(temporal_str)
        if not norm_key or norm_key in entities_dict:
            return
        
        pid = f"tmp_{len(entities_dict) + 1:05d}"
        
        entity = {
            "$schema": "https://bib.upr.edu.cu/schemas/local_entities/temporal-v0.0.1.json",
            "pid": pid,
            "type": "bf:Temporal",
            "name": temporal_str,
            "authorized_access_point": temporal_str,
            "source_catalog": "upr_legacy"
        }
        
        entities_dict[norm_key] = entity
    
    for tag in ['148', '758']:
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            extract_single_temporal(df)

# ==============================================================================
# EXTRACCIÓN DE OBRAS / TÍTULOS UNIFORMES (Campos 130, 630, 730)
# ==============================================================================

def extract_works(record, entities_dict):
    """
    Extrae obras (títulos uniformes) de los campos MARC 130, 630 y 730.
    El creator se obtiene del campo 100 del mismo registro (si existe).
    """
    
    # Primero, buscar el autor principal del registro (100 $a)
    creator = None
    author_100 = record.find('.//marc:datafield[@tag="100"]', NAMESPACES)
    if author_100 is not None:
        name_sf = author_100.find('marc:subfield[@code="a"]', NAMESPACES)
        if name_sf is not None and name_sf.text:
            creator = name_sf.text.strip()
    
    def build_work_title(df):
        """
        Construye el título completo del Work.
        Concatena $a (título), $n (número de sección), $p (nombre de sección).
        """
        parts = []
        title_sf = df.find('marc:subfield[@code="a"]', NAMESPACES)
        if title_sf is not None and title_sf.text:
            parts.append(title_sf.text.strip())
        
        for code in ['n', 'p']:
            for sf in df.findall(f'marc:subfield[@code="{code}"]', NAMESPACES):
                if sf.text:
                    parts.append(sf.text.strip())
        
        return ". ".join(parts) if parts else None
    
    def build_authorized_access_point(title, creator, date=None):
        """
        Construye el authorized_access_point según reglas RDA.
        Formato: "Creator. Title (Date)" o "Title (Date)"
        """
        if creator:
            aap = f"{creator}. {title}"
        else:
            aap = title
        
        if date:
            aap += f" ({date})"
        
        return aap
    
    def extract_single_work(df):
        """Extrae un Work individual de un datafield 130, 630 o 730."""
        title = build_work_title(df)
        
        if not title:
            return
        
        date_sf = df.find('marc:subfield[@code="f"]', NAMESPACES)
        date = date_sf.text.strip() if date_sf is not None and date_sf.text else None
        
        dedup_key = normalize_text(title)
        if creator:
            dedup_key = f"{dedup_key}||{normalize_text(creator)}"
        
        if not dedup_key or dedup_key in entities_dict:
            return
        
        pid = f"wrk_{len(entities_dict) + 1:05d}"
        
        aap = build_authorized_access_point(title, creator, date)
        
        entity = {
            "$schema": "https://bib.upr.edu.cu/schemas/local_entities/work-v0.0.1.json",
            "pid": pid,
            "type": "bf:Work",
            "title": title,
            "authorized_access_point": aap,
            "source_catalog": "upr_legacy"
        }
        
        if creator:
            entity["creator"] = creator
        
        entities_dict[dedup_key] = entity
    
    for tag in ['130', '630', '730']:
        for df in record.findall(f'.//marc:datafield[@tag="{tag}"]', NAMESPACES):
            extract_single_work(df)

# ==============================================================================
# DETECCIÓN DE POSIBLES DUPLICADOS
# ==============================================================================

def find_potential_duplicates(entities_list, similarity_threshold=0.85):
    """
    Encuentra posibles duplicados basándose en similitud de texto.
    Solo compara entidades del mismo tipo.
    
    Args:
        entities_list: Lista de entidades extraídas
        similarity_threshold: Umbral de similitud (0.0 a 1.0)
    
    Returns:
        Lista de diccionarios con los posibles duplicados
    """
    duplicates = []
    
    # Agrupar entidades por tipo
    entities_by_type = {}
    for entity in entities_list:
        entity_type = entity['type']
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        entities_by_type[entity_type].append(entity)
    
    # Comparar entidades del mismo tipo
    for entity_type, entities in entities_by_type.items():
        print(f"  Buscando duplicados en {entity_type} ({len(entities)} entidades)...")
        
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                # Comparar por 'name' para Person, Topic, Organisation, Place, Temporal
                # Comparar por 'title' para Work
                if entity_type == 'bf:Work':
                    text1 = entities[i].get('title', '')
                    text2 = entities[j].get('title', '')
                else:
                    text1 = entities[i].get('name', '')
                    text2 = entities[j].get('name', '')
                
                if not text1 or not text2:
                    continue
                
                similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
                
                if similarity_threshold <= similarity < 1.0:
                    duplicates.append({
                        'type': entity_type,
                        'entity1': entities[i],
                        'entity2': entities[j],
                        'similarity': similarity
                    })
    
    return duplicates

# ==============================================================================
# PROCESAMIENTO DE ARCHIVOS
# ==============================================================================

def process_file(xml_path, entities_dict, total_records_processed):
    """
    Procesa un archivo XML y extrae todas las entidades.
    
    Args:
        xml_path: Ruta al archivo XML
        entities_dict: Diccionario global de entidades (se modifica in-place)
        total_records_processed: Contador de registros procesados
    
    Returns:
        Número de registros procesados en este archivo
    """
    print(f"\n📄 Procesando: {xml_path}")
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"  ❌ Error al leer el archivo: {e}")
        return 0
    
    records = root.findall('.//marc:record', NAMESPACES)
    file_records = len(records)
    
    print(f"  Registros encontrados: {file_records}")
    
    for i, record in enumerate(records):
        total_records_processed += 1
        
        if total_records_processed % 1000 == 0:
            print(f"  ... procesados {total_records_processed} registros en total. "
                  f"Entidades únicas: {len(entities_dict)}")
        
        extract_persons(record, entities_dict)
        extract_topics(record, entities_dict)
        extract_organizations(record, entities_dict)
        extract_places(record, entities_dict)
        extract_temporals(record, entities_dict)
        extract_works(record, entities_dict)
    
    print(f"  ✅ Archivo completado. Entidades únicas hasta ahora: {len(entities_dict)}")
    
    return file_records

# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Extrae entidades locales desde archivos MARC XML.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Procesar un solo archivo
  python extract_entities.py -i legacy/marc21.fix.mrcxml -o legacy/local_entities.json
  
  # Procesar múltiples archivos
  python extract_entities.py -i BCT.xml BECSH.xml FCF.xml -o legacy/local_entities.json
  
  # Usar patrón glob (requiere shell expansion)
  python extract_entities.py -i legacy/*.xml -o legacy/local_entities.json
  
  # Ajustar umbral de similitud para duplicados
  python extract_entities.py -i legacy/*.xml -o legacy/local_entities.json --similarity 0.90
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        nargs='+',
        required=True,
        help='Uno o más archivos XML de entrada (separados por espacio)'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Archivo JSON de salida con todas las entidades extraídas'
    )
    
    parser.add_argument(
        '--similarity',
        type=float,
        default=0.85,
        help='Umbral de similitud para detectar posibles duplicados (0.0 a 1.0, default: 0.85)'
    )
    
    parser.add_argument(
        '--no-duplicates-report',
        action='store_true',
        help='No generar reporte de posibles duplicados'
    )
    
    args = parser.parse_args()
    
    # Verificar que los archivos de entrada existan
    for xml_path in args.input:
        if not os.path.exists(xml_path):
            print(f"❌ Error: El archivo no existe: {xml_path}")
            sys.exit(1)
    
    print("=" * 80)
    print("🚀 EXTRACCIÓN DE ENTIDADES LOCALES DESDE MARC XML")
    print("=" * 80)
    print(f"\nArchivos de entrada: {len(args.input)}")
    print(f"Archivo de salida: {args.output}")
    print(f"Umbral de similitud: {args.similarity}")
    
    # Diccionario global de entidades
    entities_dict = {}
    total_records = 0
    
    # Procesar cada archivo
    for xml_path in args.input:
        records_in_file = process_file(xml_path, entities_dict, total_records)
        total_records += records_in_file
    
    # Convertir el diccionario a lista
    final_entities = list(entities_dict.values())
    
    # Crear directorio de salida si no existe
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Guardar en archivo JSON
    print(f"\n💾 Guardando entidades en: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(final_entities, f, ensure_ascii=False, indent=2)
    
    # Estadísticas finales
    print("\n" + "=" * 80)
    print("📊 ESTADÍSTICAS FINALES")
    print("=" * 80)
    print(f"Total de registros procesados: {total_records}")
    print(f"Total de entidades únicas extraídas: {len(final_entities)}")
    
    stats = {}
    for entity in final_entities:
        entity_type = entity['type']
        stats[entity_type] = stats.get(entity_type, 0) + 1
    
    print("\nEntidades por tipo:")
    for entity_type, count in sorted(stats.items()):
        print(f"  {entity_type}: {count}")
    
    # Reporte de posibles duplicados
    if not args.no_duplicates_report:
        print("\n" + "=" * 80)
        print("🔍 ANÁLISIS DE POSIBLES DUPLICADOS")
        print("=" * 80)
        print(f"Umbral de similitud: {args.similarity}")
        
        duplicates = find_potential_duplicates(final_entities, args.similarity)
        
        if duplicates:
            print(f"\n⚠️  Se encontraron {len(duplicates)} posibles duplicados:")
            
            # Mostrar primeros 20 duplicados
            for i, dup in enumerate(duplicates[:20], 1):
                print(f"\n  {i}. [{dup['type']}]")
                print(f"     Entidad 1: {dup['entity1'].get('name', dup['entity1'].get('title', 'N/A'))}")
                print(f"     Entidad 2: {dup['entity2'].get('name', dup['entity2'].get('title', 'N/A'))}")
                print(f"     Similitud: {dup['similarity']:.2%}")
            
            if len(duplicates) > 20:
                print(f"\n  ... y {len(duplicates) - 20} duplicados más")
            
            # Guardar reporte de duplicados en archivo separado
            duplicates_report_path = args.output.replace('.json', '_duplicates.json')
            print(f"\n💾 Guardando reporte completo de duplicados en: {duplicates_report_path}")
            
            duplicates_report = []
            for dup in duplicates:
                duplicates_report.append({
                    'type': dup['type'],
                    'similarity': dup['similarity'],
                    'entity1_pid': dup['entity1']['pid'],
                    'entity1_name': dup['entity1'].get('name', dup['entity1'].get('title')),
                    'entity2_pid': dup['entity2']['pid'],
                    'entity2_name': dup['entity2'].get('name', dup['entity2'].get('title'))
                })
            
            with open(duplicates_report_path, 'w', encoding='utf-8') as f:
                json.dump(duplicates_report, f, ensure_ascii=False, indent=2)
        else:
            print("\n✅ No se encontraron posibles duplicados")
    
    print("\n" + "=" * 80)
    print("✅ ¡PROCESO COMPLETADO!")
    print("=" * 80)
    print(f"\nArchivo de entidades: {args.output}")
    if not args.no_duplicates_report and duplicates:
        print(f"Reporte de duplicados: {duplicates_report_path}")
    print()

if __name__ == '__main__':
    main()