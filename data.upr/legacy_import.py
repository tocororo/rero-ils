import re
import xml.etree.ElementTree as ET
import traceback

# 190617#m cuaf##o0010dspa
# 190708#m       cu af##o0010d        spa#

def load_countries():
    result = []
    tree = ET.parse('/home/malayo/dev/rero/rero-ils/data/upr/countries.xml')
    root = tree.getroot()
    countries = root.find('{info:lc/xmlns/codelist-v1}countries')
    for c in countries.findall('{info:lc/xmlns/codelist-v1}country'):
        result.append(c.find('{info:lc/xmlns/codelist-v1}code').text)
    return result


def load_languages():
    result = []
    tree = ET.parse('/home/malayo/dev/rero/rero-ils/data/upr/languages.xml')
    root = tree.getroot()
    languages = root.find('{info:lc/xmlns/codelist-v1}languages')
    for c in languages.findall('{info:lc/xmlns/codelist-v1}language'):
        result.append(c.find('{info:lc/xmlns/codelist-v1}code').text)
    return result


def get_substrings(value: str, min_size=2, max_size=3):
    subs = []
    for i in range(len(value)):
        for j in range(i + min_size, min(i + max_size + 1, len(value) + 1)):
            if j - i <= max_size:
                s = value[i:j]
                subs.append(s)
    return subs


def index_reversed(value, sub):
    """ busca el indice donde empieza sub en value, pero en reversa
    ejemplo:
    value='190617#m cuafspa##o0010dspadd'
    sub='spa'
    return 24

    retorna -1 si sub no es subcadena de value

    """
    end = len(value)
    step = len(sub)
    start = len(value) - step
    for i in range(start):
        cad = value[start - i:end - i]
        if cad == sub:
            return start - i

    return -1


def fix_upr_tag8(value: str, countries, languages):

    result = ''

    '''
    hay unos records que tienen este error'''
    if 'English' in value:
        print(value)
        value = value.replace('English', 'eng')
        print(value)

    '''
    Las posiciones 00-17 y 35-39 están definidas en igual forma para todos los tipos de
    materiales, con una consideración especial para la posición 06. La definición de las
    posiciones 18-34 se hizo en forma independiente para cada tipo de material,
    '''

    # 1- si los primeros 6 caracteres son numeros
    p_digits = r"^\d{6}"
    if bool(re.match(p_digits, value)):
        '''se refieren a la fecha y se queda tal cual
        00-05 – Fecha de ingreso del registro'''
        c00_05_date = value[0:6]

        '''buscar en el resto del value si aparece algun codigo pais o de lenguaje
        el problema es que puede aparecer mas de un pais o lenguaje
        que en realidad son sub cadenas que se forman, pero no constituyen codigos
        por tanto... lo mas probable es que la primera subcadena que se encuentre que es un
        codigo pais entonces es el pais..
        en el caso del lenguaje es al reves, o sea, como el idioma aparece al final, comienzo
        buscando en las subcadenas en reversa, y la primera que aparezca como un idioma,
        lo tomo como correcto.
        esto, como es logico, puede estar sujeto a errores.'''
        subs = get_substrings(value[6: len(value)])

        # 15:17
        c15_17_country = ''
        # 35:37
        c35_37_language = ''

        for sub in subs:
            if sub in countries:
                # el codigo puede ser de dos caracteres
                c15_17_country = sub
                break
        subs.reverse()
        for sub in subs:
            if sub in languages:
                c35_37_language = sub
                break
        subs.reverse()

        '''
        06 – Tipo de fecha/Estado de la publicación
        valores posibles: b,c,d,e,i,k,m,n,p,q,r,s,t,u,|
        si aparece alguno de estos valores en value, entre date y country
        entonces se lo asigno a c06
        07-10 - Fecha 1
        11-14 - Fecha 2
        en ambos casos los valores posibles son:
        1-9 – Dígitos de la fecha
        #, u, |
        parsear la subcadena entre la fecha y el pais de 06:14
        c06_14 = value[0:value.index(c15_17_country)]
        en realidad para los datos que hay lo mejor es simplemente poner un valor por defecto
        que en este caso seria b y 8 caracteres de relleno'''
        c06_14 = 'b'.ljust(9)

        '''
        parsear la subcadena entre el el pais y el idioma
        podemos asumir que todos los registros se refieren a libros, por tando,
        los caracteres aqui se refieren a:
        18-21 – Ilustraciones
        22 – Audiencia
        23 – Forma del material
        24-27 – Naturaleza del contenido
        28 – Publicación gubernamental
        29 – Conferencia
        30 – Homenaje
        31 – Indice
        32 – No definido
        33 – Forma literaria
        34 – Biografía'''
        start = value.index(c15_17_country)
        end = index_reversed(value, c35_37_language)
        c18_34 = value[start:end]
        c18_34_len = len(c18_34)
        step = 1
        c34 = '|'
        if c18_34[c18_34_len - step] in ['#', 'a', 'b', 'c', 'd', '|']:
            c34 = c18_34[c18_34_len - step]
            step = step + 1
        c33 = '|'
        if c18_34[c18_34_len - step] in ['0', '1', 'c', 'd', 'e', 'f', 'h', 'i', 'j', 'm', 'p',
                                         's', 'u', '|']:
            c33 = c18_34[c18_34_len - step]
            step = step + 1
        c32 = '|'
        c31 = '|'
        if c18_34[c18_34_len - step] in ['0', '1', '|']:
            c31 = c18_34[c18_34_len - step]
            step = step + 1
        c30 = '|'
        if c18_34[c18_34_len - step] in ['0', '1', '|']:
            c30 = c18_34[c18_34_len - step]
            step = step + 1
        c29 = '|'
        if c18_34[c18_34_len - step] in ['0', '1', '|']:
            c29 = c18_34[c18_34_len - step]
            step = step + 1
        c28 = '|'
        if c18_34[c18_34_len - step] in ['#', 'a', 'c', 'f', 'i', 'l', 'm', 'o', 's', 'u', 'z',
                                         '|']:
            c28 = c18_34[c18_34_len - step]
            step = step + 1
        c24_27 = ''
        for i in range(0, 4):
            if c18_34[c18_34_len - step] in ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'i', 'j', 'k',
                                             'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                                             'v', 'w', 'z', '2', '|']:
                c24_27 = c24_27 + c18_34[c18_34_len - step]
            else:
                c24_27 = c24_27 + '#'
            step = step + 1
        c23 = '|'
        if c18_34[c18_34_len - step] in ['#', 'a', 'b', 'c', 'd', 'f', 'r', 's', '|']:
            c23 = c18_34[c18_34_len - step]
            step = step + 1
        c22 = '#'
        if c18_34[c18_34_len - step] in ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'j', '|']:
            c22 = c18_34[c18_34_len - step]
            step = step + 1

        c18_21 = ''
        for i in range(0, 4):
            if c18_34[c18_34_len - step] in ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
                                             'k', 'l', 'm', 'o', 'p', '|']:
                c18_21 = c18_21 + c18_34[c18_34_len - step]
            else:
                c18_21 = c18_21 + '|'
            step = step + 1

        '''
        parsear la subcadena entre el idioma y el final
        '''
        c38_39 = value[index_reversed(value, c35_37_language) + len(c35_37_language): len(value)]
        c39 = 'd'
        c38 = '#'
        if len(c38_39) == 2:
            if c38_39[1] in ['#', 'c', 'd', 'u', '|']:
                c39 = c38_39[1]
            if c38_39[0] in ['#', 's', 'd', 'x', 'r', 'o', '|']:
                c38 = c38_39[0]
        if len(c38_39) == 1:
            if c38_39[0] in ['#', 'c', 'd', 'u', '|']:
                c39 = c38_39[0]
            if c38_39[0] in ['#', 's', 'd', 'x', 'r', 'o', '|']:
                c38 = c38_39[0]

        result = (c00_05_date + c06_14 + c15_17_country.ljust(3) +
                  c18_21 + c22 + c23 + c24_27 + c28 + c29 + c30 + c31 + c32 + c33 + c34 +
                  c35_37_language.ljust(3) + c38 + c39)

        return result

    # existe una cantidad de records que tienen esta forma
    # 02/14 o 02/2013 rrefi
    # al parecer se trata de las tesis.
    p_date = r"\d{2}/\d{2,4}"
    if bool(re.match(p_date, value)):
        dates = value.split('/')
        c02_03 = dates[0]
        c00_01 = '  '
        if len(dates[1]) == 2:
            c00_01 = dates[1]
        elif len(dates[1]) == 4:
            c00_01 = dates[1][2:4]
        else:
            c00_01 = 20

        result = '{0}{1}01b'.format(c00_01, c02_03)
        result = result.ljust(40)
        return result
    p_date = r"\d{1}/\d{2}"
    if bool(re.match(p_date, value)):
        dates = value.split('/')
        result = '{0}0{1}01b'.format(dates[1], dates[0])
        result = result.ljust(40)
        return result



def load_document(xml_file):
    ET.register_namespace('', "http://www.loc.gov/MARC21/slim")
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return tree, root


def modificar_registros(root, fi, db):

    countries = load_countries()
    languages = load_languages()

    print(fi, db)
    tag8 = dict(ok01_ok08_40=[], ok01_ok08_40err=[], ok01_ok08_40fix=[], no01_ok08_40=[],
                no01_ok08_40err=[],
                ok01_no08=[], no01_no08=[])
    recs = dict(ok01_ok08_40=[], ok01_ok08_40err=[], ok01_ok08_40fix=[], no01_ok08_40=[],
                no01_ok08_40err=[],
                ok01_no08=[], no01_no08=[])

    count = 0
    co008 = 0
    co008none = 0
    tag_library = ET.Element("library")
    tag_library.text = db

    for record in root.findall('{http://www.loc.gov/MARC21/slim}record'):
        count = count + 1
        record.append(tag_library)
        controlfield_001 = record.find('{http://www.loc.gov/MARC21/slim}controlfield[@tag="001"]')
        if controlfield_001 is not None:
            # Añadir el prefijo "REROILS:"
            controlfield_001.text = "REROILS:" + controlfield_001.text

        is_tesis = False
        # Verificar si el record tiene un controlfield con tag="006" y valor "Tesis"
        tesis_field = record.find('{http://www.loc.gov/MARC21/slim}controlfield[@tag="006"]')
        datafield_502 = record.find('{http://www.loc.gov/MARC21/slim}datafield[@tag="502"]')
        datafield_500 = record.find('{http://www.loc.gov/MARC21/slim}datafield[@tag="500"]')
        if (tesis_field is not None and tesis_field.text == "Tesis" or datafield_502 is not None
            or datafield_500 is not None):
            # Añadir datafield para tesis
            new_datafield_tesis = ET.Element('{http://www.loc.gov/MARC21/slim}datafield', tag="339",
                                             ind1=" ", ind2=" ")
            subfield_a = ET.SubElement(new_datafield_tesis,
                                       '{http://www.loc.gov/MARC21/slim}subfield', code="a")
            subfield_a.text = "docmaintype_book"
            subfield_b = ET.SubElement(new_datafield_tesis,
                                       '{http://www.loc.gov/MARC21/slim}subfield', code="b")
            subfield_b.text = "docsubtype_thesis"
            record.append(new_datafield_tesis)
            is_tesis = True

        # Si ninguna condición se cumple, añadir datafield para otro tipo de libro
        new_datafield_other = ET.Element('{http://www.loc.gov/MARC21/slim}datafield', tag="339",
                                         ind1=" ", ind2=" ")
        subfield_a = ET.SubElement(new_datafield_other, '{http://www.loc.gov/MARC21/slim}subfield',
                                   code="a")
        subfield_a.text = "docmaintype_book"
        subfield_b = ET.SubElement(new_datafield_other, '{http://www.loc.gov/MARC21/slim}subfield',
                                   code="b")
        subfield_b.text = "docsubtype_other_book"
        record.append(new_datafield_other)

        controlfield_008 = record.find('{http://www.loc.gov/MARC21/slim}controlfield[@tag="008"]')
        if controlfield_008 is not None and controlfield_001 is not None:
            co008 = co008 + 1
            text = "{0}---{1}---{2}---{3}---{4}".format(fi, controlfield_001.text,
                                                        len(controlfield_008.text),
                                                        controlfield_008.text, is_tesis)
            if len(controlfield_008.text) == 40:
                recs['ok01_ok08_40'].append(record)
                tag8['ok01_ok08_40'].append(text)
            else:
                try:
                    tag8_fixed_text = fix_upr_tag8(controlfield_008.text, countries, languages)
                    if len(tag8_fixed_text) == 40:
                        tag8['ok01_ok08_40fix'].append('{0}---{1}'.
                                                       format(controlfield_008.text,
                                                              tag8_fixed_text))
                        controlfield_008.text = tag8_fixed_text
                        recs['ok01_ok08_40fix'].append(record)

                        text = "{0}---{1}---{2}---{3}---{4}".format(fi, controlfield_001.text,
                                                                    len(controlfield_008.text),
                                                                    controlfield_008.text, is_tesis)
                        recs['ok01_ok08_40'].append(record)
                        tag8['ok01_ok08_40'].append(text)

                    else:
                        recs['ok01_ok08_40err'].append(record)
                        tag8['ok01_ok08_40err'].append(text)
                except Exception as e:
                    exception_name = e.__class__.__name__
                    recs['ok01_ok08_40err'].append(record)
                    tag8['ok01_ok08_40err'].append('exc:{0}---{1}'.format(traceback.format_exc(),
                                                                          text))
                # if is_tesis:
                #     recs['tesis'].append(record)
                #     tag8['tesis'].append(text)
        if controlfield_008 is not None and controlfield_001 is None:
            co008 = co008 + 1
            text = "{0}---{1}---{2}---{3}".format(fi, 'noid',
                                                  len(controlfield_008.text),
                                                  controlfield_008.text)
            if len(controlfield_008.text) == 40:
                recs['no01_ok08_40'].append(record)
                tag8['no01_ok08_40'].append(text)
            else:
                recs['no01_ok08_40err'].append(record)
                tag8['no01_ok08_40err'].append(text)
                # if is_tesis:
                #     recs['tesis'].append(record)
                #     tag8['tesis'].append(text)
        if controlfield_008 is None and controlfield_001 is not None:
            co008 = co008 + 1
            tag_008 = ET.Element("controlfield", attrib=dict(tag='008'))
            tag_008.text = '200101b'.ljust(40)
            record.append(tag_008)
            recs['ok01_no08'].append(record)
            tag8['ok01_no08'].append("{0}---{1}---".format(fi, controlfield_001.text))
            text = "{0}---{1}---{2}---{3}---{4}".format(fi, controlfield_001.text,
                                                        len(tag_008.text),
                                                        tag_008.text, is_tesis)
            recs['ok01_ok08_40'].append(record)
            tag8['ok01_ok08_40'].append(text)

        if controlfield_008 is None and controlfield_001 is None:
            co008 = co008 + 1
            tag_008 = ET.Element("controlfield", attrib=dict(tag='008'))
            tag_008.text = '200101b'.ljust(40)
            record.append(tag_008)
            recs['no01_no08'].append(record)
            tag8['no01_no08'].append("{0}---{1}---".format(fi, ' '.join(record.itertext()).strip()))

    print('===counts===')
    print(count)
    print(co008)

    # print(len(tag8['good']) + len(tag8['error']) + len(tag8['none']) + len(tag8['noid']))

    return count, dict(recs=recs, tag8=tag8)


def guardar_documento(tree, output_file):
    tree.write(output_file, encoding='utf-8', xml_declaration=True)


def main():
    files = ['db/BCT/marc21.mrcxml', 'db/BECSH/marc21.mrcxml', 'db/FCF/marc21.mrcxml',
             'db/FCP/marc21.mrcxml']
    dbs = ['BCT', 'BECSH', 'FCF', 'FCP']

    result = dict(
        tag8=dict(ok01_ok08_40=[], ok01_ok08_40err=[], ok01_ok08_40fix=[], no01_ok08_40=[],
                  no01_ok08_40err=[],
                  ok01_no08=[], no01_no08=[]),
        recs=dict(ok01_ok08_40=[], ok01_ok08_40err=[], ok01_ok08_40fix=[], no01_ok08_40=[],
                  no01_ok08_40err=[],
                  ok01_no08=[], no01_no08=[]))
    count = 0
    for db in dbs:
        fi = 'db/{0}/marc21.mrcxml'.format(db)
        tree, root = load_document(fi)
        c, out = modificar_registros(root, fi, db)

        count = count + c
        cc = 0
        for key1, value1 in result.items():
            for key2, value2 in value1.items():
                cc = cc + len(out[key1][key2])
                result[key1][key2].extend(out[key1][key2])
        print(c, cc / 2)
        # for a in ['recs', 'tag8']:
        #     for grp in ['good', 'error', 'tesis', 'none', 'noid']:

        # tag8['good'].extend(out['good'])
        # tag8['error'].extend(out['error'])
        # tag8['tesis'].extend(out['tesis'])
        # tag8['none'].extend(out['none'])

    print(count)
    for key3, value3 in result['tag8'].items():
        with open("{0}.txt".format(key3), "w") as output:
            for row in value3:
                output.write(str(row) + '\n')

    for key4, value4 in result['recs'].items():
        root = ET.Element("collection", {"xmlns": "http://www.loc.gov/MARC21/slim"})
        tree = ET.ElementTree(root)
        for row in value4:
            root.append(row)
        tree.write("{0}.xml".format(key4), encoding="utf-8")

    # with open("error.txt", "w") as output:
    #     for row in tag8['error']:
    #         output.write(str(row) + '\n')
    # with open("tesis.txt", "w") as output:
    #     for row in tag8['tesis']:
    #         output.write(str(row) + '\n')
    # with open("none.txt", "w") as output:
    #     for row in tag8['none']:
    #         output.write(str(row) + '\n')

    # input_file = 'db/BECSH/marc21.mrcxml'
    # output_file = 'marc21.fix.mrcxml'

    # Modificar los registros

    # Guardar el documento modificado
    # guardar_documento(tree, output_file)

    # print(f"El documento ha sido modificado y guardado como {output_file}")


if __name__ == "__main__":
    main()
