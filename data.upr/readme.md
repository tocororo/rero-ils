# Proyecto Biblioteca de Vueltabajo (UPR)

El sistema funciona como una nube bibliotecaria para las instituciones de la
provincia de Pinar del Río, Cuba. La Universidad de Pinar del Río (UPR) es la
entidad ejecutora y la primera organización incorporada.

## Configuración inicial

Los ficheros JSON de esta carpeta inicializan las entidades estructurales del
sistema. El script `scripts/setup.upr` los carga en el orden correcto de
dependencias:

```
organisations → libraries → locations → item_types → patron_types
→ circulation_policies → users → budgets
```

Ejecutar con:

```bash
uv run scripts/setup.upr
```

---

## Importación del catálogo legacy

El directorio `legacy/db/` contiene los registros exportados del sistema
bibliográfico anterior en formato MARC21 XML (`marc21.mrcxml`), uno por
biblioteca (BCT, BECSH, FCF, FCP).

El script `legacy_import.py` pre-procesa esos ficheros antes de cargarlos
en rero-ils.

### Paso 0 - Extraer entidades legacy

El script extract_entities.py se encarga de extraer las entidades del los ficheros MARC XML. 

Se ejecuta el siguiente comando. 

python extract_entities.py -i legacy/db/BCT/marc21.mrcxml legacy/db/BECSH/marc21.mrcxml legacy/db/FCF/marc21.mrcxml legacy/db/FCP/marc21.mrcxml -o local_entities_orig.json

### Paso 1 — Pre-procesar el MARC21 XML

```bash
python data.upr/legacy_import.py
```

El script lee los `marc21.mrcxml` de cada biblioteca y por cada registro:

- Prefija el campo 001 con `REROILS:` para evitar colisiones de PIDs
- Normaliza el campo 008 a exactamente 40 caracteres (lo repara si está malformado)
- Añade el campo 339 con el tipo de documento (`docmaintype_book` / `docsubtype_thesis`)
- Asigna un 008 por defecto (`200101b` + 33 espacios) a los registros sin ese campo

Genera en `data.upr/legacy/`:

| Fichero | Contenido |
|---|---|
| `marc21.fix.mrcxml` | Todos los registros válidos combinados (4 BDs) |
| `marc21.fix.error.mrcxml` | Registros con campo 008 irreparable |
| `db/<BD>/marc21.fix.mrcxml` | Registros válidos por biblioteca |
| `db/<BD>/marc21.fix.error.mrcxml` | Errores por biblioteca |

Al terminar imprime estadísticas con el conteo por columnas:
`total / ya ok / reparados / default añadido / error`.

---

### Paso 2 — Convertir MARC21 a JSON rero-ils (por BD)

Tras el paso 1, cada biblioteca tiene su propio `marc21.fix.mrcxml` en
`legacy/db/<BD>/`. La conversión a JSON se ejecuta **por separado** para
cada base de datos:

```bash
# BCT
invenio reroils documents marc21tojson \
  -t rero -v -r \
  data.upr/legacy/db/BCT/marc21.fix.mrcxml \
  data.upr/legacy/db/BCT/marc21.fix.json \
  data.upr/legacy/db/BCT/marc21.tojson.error.mrcxml

# BECSH
invenio reroils documents marc21tojson \
  -t rero -v -r \
  data.upr/legacy/db/BECSH/marc21.fix.mrcxml \
  data.upr/legacy/db/BECSH/marc21.fix.json \
  data.upr/legacy/db/BECSH/marc21.tojson.error.mrcxml

# FCF
invenio reroils documents marc21tojson \
  -t rero -v -r \
  data.upr/legacy/db/FCF/marc21.fix.mrcxml \
  data.upr/legacy/db/FCF/marc21.fix.json \
  data.upr/legacy/db/FCF/marc21.tojson.error.mrcxml

# FCP
invenio reroils documents marc21tojson \
  -t rero -v -r \
  data.upr/legacy/db/FCP/marc21.fix.mrcxml \
  data.upr/legacy/db/FCP/marc21.fix.json \
  data.upr/legacy/db/FCP/marc21.tojson.error.mrcxml
```

| Flag | Efecto |
|---|---|
| `-t rero` | Transformación RERO (convierte campos MARC21 al esquema rero-ils) |
| `-v` | Verbose — muestra progreso y errores por consola |
| `-r` | Requiere PID en cada registro; sin campo 001 van al fichero de error |

Genera por cada BD:

| Fichero | Contenido |
|---|---|
| `db/<BD>/marc21.fix.json` | Documentos en formato JSON rero-ils, listos para cargar |
| `db/<BD>/marc21.tojson.error.mrcxml` | Registros que fallaron la conversión |

---

### Paso 3 — Pausar el worker de portadas

Evita carga innecesaria durante la importación masiva:

```bash
invenio reroils documents cover-url-queue-worker pause
```

---

### Paso 4 — Cargar los documentos (por BD)

Cada biblioteca se carga de forma independiente:

```bash
# BCT
invenio reroils fixtures create \
  --pid_type doc \
  --schema 'https://bib.upr.edu.cu/schemas/documents/document-v0.0.1.json' \
  --append --dont-stop \
  data.upr/legacy/db/BCT/marc21.fix.json

# BECSH
invenio reroils fixtures create \
  --pid_type doc \
  --schema 'https://bib.upr.edu.cu/schemas/documents/document-v0.0.1.json' \
  --append --dont-stop \
  data.upr/legacy/db/BECSH/marc21.fix.json

# FCF
invenio reroils fixtures create \
  --pid_type doc \
  --schema 'https://bib.upr.edu.cu/schemas/documents/document-v0.0.1.json' \
  --append --dont-stop \
  data.upr/legacy/db/FCF/marc21.fix.json

# FCP
invenio reroils fixtures create \
  --pid_type doc \
  --schema 'https://bib.upr.edu.cu/schemas/documents/document-v0.0.1.json' \
  --append --dont-stop \
  data.upr/legacy/db/FCP/marc21.fix.json
```

| Flag | Efecto |
|---|---|
| `--pid_type doc` | Carga como registros bibliográficos |
| `--schema` | Valida cada registro contra el esquema JSON del sistema |
| `--append` | Añade a los registros existentes sin borrar ninguno |
| `--dont-stop` | Continúa si un registro individual falla |

> Para ficheros grandes (~35 000 registros) añade `--lazy` para leer el fichero
> en streaming sin cargarlo completo en memoria.

---

### Paso 5 — Reindexar documentos

```bash
invenio reroils index reindex -t doc --yes-i-know
invenio reroils index run --raise-on-error
```

---

### Paso 6 — Reactivar el worker de portadas

```bash
invenio reroils documents cover-url-queue-worker resume
```

---

### Paso 7 — Ejemplares y fondos (holdings / items)

El MARC21 exportado contiene únicamente registros bibliográficos. Los ejemplares
físicos y sus fondos **no se incluyen** en la exportación. Hay dos vías:

#### Opción A — Alta manual desde la interfaz profesional

Una vez cargados los documentos, cada bibliotecaria añade los ejemplares
directamente desde el panel de administración de rero-ils.

#### Opción B — Ficheros JSON preparados aparte

Si el sistema legacy exporta también datos de ejemplares (código de barras,
ubicación, signatura), preparar `data.upr/legacy/holdings.json` e
`data.upr/legacy/items.json` y cargarlos **después de los documentos**:

```bash
# Holdings primero (agrupan ejemplares por biblioteca y tipo de material)
invenio reroils fixtures create \
  --pid_type hold \
  --schema 'https://bib.upr.edu.cu/schemas/holdings/holding-v0.0.1.json' \
  --append data.upr/legacy/holdings.json

# Después los ejemplares (requieren referencia a holdings y documentos)
invenio reroils fixtures create \
  --pid_type item \
  --schema 'https://bib.upr.edu.cu/schemas/items/item-v0.0.1.json' \
  --append data.upr/legacy/items.json

invenio reroils index reindex -t hold --yes-i-know
invenio reroils index reindex -t item --yes-i-know
invenio reroils index run --raise-on-error
```

---

## Investigar registros con error

Los registros que fallen en el Paso 2 quedan en
`db/<BD>/marc21.tojson.error.mrcxml` por cada biblioteca.
La causa más frecuente es la ausencia del campo 245 (título).

```bash
# Cuántos registros fallaron por BD
for db in BCT BECSH FCF FCP; do
  echo -n "${db}: "
  grep -c '<record>' "data.upr/legacy/db/${db}/marc21.tojson.error.mrcxml" 2>/dev/null || echo "0"
done

# PIDs de los registros con error (todas las BD juntos)
grep -A2 'controlfield tag="001"' data.upr/legacy/db/*/marc21.tojson.error.mrcxml
```

---

## Script automatizado

El script `scripts/import_legacy.upr` ejecuta los pasos 2-6 por separado para
cada base de datos:

```bash
uv run scripts/import_legacy.upr          # todas las BD
uv run scripts/import_legacy.upr -d BCT    # solo una
uv run scripts/import_legacy.upr -r        # incluir reindex al final
uv run scripts/import_legacy.upr -c        # continuar si una BD falla
```

## Resumen del flujo

```
legacy_import.py
      │
      ▼
db/<BD>/marc21.fix.mrcxml   (4 BDs)
      │
      ▼  marc21tojson -t rero
      ├──▶ db/<BD>/marc21.fix.json ──────▶ fixtures create --pid_type doc
      │                                            │
      └──▶ db/<BD>/marc21.tojson.error.mrcxml      ▼
           (investigar manualmente)           reindex -t doc
```
