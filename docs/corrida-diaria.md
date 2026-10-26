# Corrida de una empresa (subagente)

Lo ejecuta un subagente lanzado por el orquestador (`docs/orquestador.md`), uno por empresa y en paralelo. `E` es la carpeta de la empresa (`termoelectricas`, `enarsa`, `nasa`, `cnea`, `ycrt`, `belgrano-cargas`, `aysa` o `intercargo`). El repo está en `/home/user/privatizaciones-ycrt-nasa` (en adelante `R`). Los documentos bajados van a `/home/user/salida/E/`, **fuera del repo**: nunca los commitees. **No hagas commit ni push**: lo hace el orquestador al final.

El orquestador te pasa la **hora límite del mail** (06:00, 15:30 o 18:00). El mail tiene que salir antes de esa hora aunque no hayas terminado las búsquedas web: priorizá BORA y CONTRAT.AR.

Leé antes `R/empresas/E/contexto.md` y las últimas entradas de `R/empresas/E/registro.md`.

## 1. Boletín Oficial
El orquestador ya escaneó el BORA para todas las empresas: la primera sección completa y, de la segunda sección (sociedades), los edictos cuya razón social coincide con tus términos (asambleas, reformas de estatuto, aumentos de capital, cambios de directorio). Leé `/home/user/salida/E/bora.json`: `coincidencias` trae solo los avisos que coinciden con tus términos y que nunca se habían visto, con el texto (`.txt`) y el PDF ya bajados.
Por cada coincidencia, leé el `.txt` y decidí si es novedad según `CLAUDE.md`. Muchas coincidencias son ruido (por ejemplo, designaciones de personal en la CNEA): descartalas sin registrar.

**Si el BORA no respondió** (mirá `errores` y `fechas_revisadas` en `bora.json`), el escáner usa respaldos en este orden:
1. **PDF del día de ARSAT** (`"fuente": "ARSAT"`): es el PDF oficial completo de la primera y la segunda sección que publica el BORA en el CDN de ARSAT. Trae el **texto oficial**, y `pdf` es el recorte de las páginas del aviso (puede incluir partes de avisos vecinos). Solo existe la edición del día y no incluye los anexos que se publican solo en la web: aclaralo si el aviso remite a anexos. Tratalo como fuente oficial.
2. **BOA** (`"fuente": "BOA"`, solo primera sección y solo si ARSAT también falló): resumen privado hecho con IA, sin texto oficial ni PDF. En el registro y en el mail aclará "según el resumen de BOA; texto oficial no verificado" y poné el link `pdf_url` en lugar del adjunto.
3. **Segunda sección sin ARSAT:** BOA no la publica. Buscá con WebSearch edictos societarios de la empresa de los últimos días (por ejemplo, "<razón social> edicto Boletín Oficial asamblea", "<razón social> aumento de capital estatuto"). Si la prensa menciona un edicto, registralo como "reportado por prensa; aviso del BORA no verificado".

## 2. CONTRAT.AR
```
python3 -I R/herramientas/contratar.py revisar --empresa R/empresas/E --salida /home/user/salida/E/contratar
```
- `candidatos`: procesos que aparecieron en las búsquedas y nunca se evaluaron. Si uno corresponde a la empresa (normalmente de la unidad 504/2 ATEP), seguilo y volvé a correr `revisar`, que en esa pasada baja todos sus documentos:
  `python3 -I R/herramientas/contratar.py seguir --empresa R/empresas/E --numero <N> --termino "<termino>"`
  Si no corresponde (obras, compras rutinarias), descartalo para no volver a evaluarlo:
  `python3 -I R/herramientas/contratar.py descartar --empresa R/empresas/E --numero <N>`
- `procesos`: para cada proceso seguido, `nuevos` lista solo los documentos que no se habían visto (circulares, anexos, actos administrativos, actas de apertura, dictámenes) y `estado_anterior` permite detectar cambios de estado. Leé `ficha.txt` para el cronograma y los textos o PDF nuevos (`pdftotext`).
- Si un archivo supera 20 MB no se baja: `nota` lo indica. Mencioná su nombre para que Pedro lo baje desde la ficha.
- `errores`: el portal es inestable y el script ya reintenta. Si persiste, mencionalo en el mail en una línea.

## 3. Prensa, Justicia y Legislaturas
Hacé varias búsquedas con WebSearch (sugerencias en `contexto.md`) para hechos judiciales y legislativos y para actos oficiales que no estén en el BORA ni en CONTRAT.AR. Ventana: desde la corrida anterior (las corridas son 06:00, 15:30 y 18:00 de lunes a viernes). Leé con WebFetch las notas que uses; si un sitio no carga el cuerpo, usá título y copete. **Descartá todo lo que ya figura en `registro.md`**, aunque salga en una nota nueva: es lo que evita repetir mails entre corridas del mismo día.

## 4. Registro
Por cada novedad, agregá una entrada en `R/empresas/E/registro.md` debajo de la marca `<!-- nuevas entradas debajo de esta línea -->` (la más reciente arriba):
```
## DD/MM/AAAA · <Tipo de documento o hecho> · <Número>
- **Fuente:** <BORA / CONTRAT.AR proceso N / medio> | <link>
- **Qué dice:** <síntesis de lo que dispone o informa: objeto, plazos, montos, porcentajes, partes, artículos clave>
- **Próximos pasos:** <con fecha, si los hay>
- **PDF enviado por mail:** <nombre de archivo o "no hay PDF">
```
Si un hecho cambia la situación de base, actualizá también `contexto.md`.

## 5. Mail
Siempre sale un mail, haya o no novedades.

**Sin novedades:** mandá un mail corto con una frase **inventada para esta corrida** sobre la empresa que seguís: su actividad, su historia, su geografía o el estado de su privatización según `contexto.md` y `registro.md`. Una sola oración, ingenio seco e inteligente, con un emoji al final. Evitá el juego de palabras obvio o de manual. Podés burlarte de lo que quieras (el Gobierno, la oposición, la empresa, los gremios, los compradores, el propio BORA): el mail es para uso personal de Pedro. `R/docs/frases-sin-novedades.txt` marca el tono; no copies esas frases.
No repitas: leé `R/empresas/E/frases-usadas.txt` (si no existe, crealo) y agregá al final tu frase en una línea con la fecha y el turno, por ejemplo `23/10/2026 18:00 · <frase>`. El orquestador lo commitea junto con el resto de `empresas/`.
Armá `/home/user/salida/E/mail.html` con la frase en un `<p>`, debajo una línea con lo revisado (por ejemplo "Revisado: BORA (o respaldo usado), CONTRAT.AR, prensa") y, si los hubo, los errores en una línea. La frase es la única excepción a las reglas de redacción de `CLAUDE.md`.
```
python3 -I R/herramientas/mail.py --para pedro.rossaroli@mitranicaballero.com \
  --asunto "[<Nombre corto de la empresa>] <la frase> · DD/MM/AAAA HH:MM" \
  --html /home/user/salida/E/mail.html
```

**Con novedades:**
Armá `/home/user/salida/E/mail.html` con un bloque por novedad (mismo contenido que el registro, en HTML simple: `<h3>`, `<p>`, `<ul>`, `<b>`, `<a>`) y una sección final "Fuentes" con el formato Medio | Título (con link) | DD/MM/AAAA. Mandalo con los documentos de las novedades:
```
python3 -I R/herramientas/mail.py --para pedro.rossaroli@mitranicaballero.com \
  --asunto "[<Nombre corto de la empresa>] <hecho principal> · DD/MM/AAAA HH:MM" \
  --html /home/user/salida/E/mail.html --adjunto <archivo1> --adjunto <archivo2> ...
```
Adjuntá solo los archivos de lo que es novedad (PDF, y planillas u otros anexos si los hay), no los del ruido descartado. Las circulares, actas y dictámenes de CONTRAT.AR que vienen como `.txt` van resumidas en el cuerpo del mail; si la circular trae un anexo, adjuntalo.
Si `mail.py` sale con código 3 (faltan credenciales) o 4 (error de la API), devolvé al orquestador "MAIL NO ENVIADO", el motivo y las novedades con sus links (BORA: `https://www.boletinoficial.gob.ar/pdf/aviso/primera/<id>/<fecha>`; CONTRAT.AR: la `url_ficha`). La entrada del registro se escribe igual.

## 6. Respuesta al orquestador
Devolvé en 2 o 3 líneas: novedades encontradas (o "sin novedades"), si se mandó el mail y con cuántos adjuntos, y cualquier error.
