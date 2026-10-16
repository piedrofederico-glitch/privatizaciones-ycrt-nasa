# Corrida diaria de un agente

`E` es la carpeta de la empresa (`termoelectricas`, `enarsa`, `nasa`, `cnea` o `ycrt`). El repo está clonado en `/home/user/privatizaciones-ycrt-nasa` (en adelante `R`). Los documentos bajados van a `/home/user/salida/E/`, **fuera del repo**: nunca los commitees.

Leé antes `R/empresas/E/contexto.md` y las últimas entradas de `R/empresas/E/registro.md`.

## 1. Boletín Oficial
```
python3 -I R/herramientas/bora.py escanear --empresa R/empresas/E --salida /home/user/salida/E/bora --dias D
```
`D` es 3 los lunes y 1 el resto de los días (cubre avisos que salieron después de la corrida anterior; los ya leídos se saltean solos).
Por cada coincidencia, leé el `.txt` y decidí si es novedad según `CLAUDE.md`. Muchas coincidencias son ruido (por ejemplo, designaciones de personal en la CNEA): descartalas sin registrar.

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
Hacé varias búsquedas con WebSearch (sugerencias en `contexto.md`) para hechos judiciales y legislativos de los últimos días, y para actos oficiales que no estén en el BORA ni en CONTRAT.AR. Leé con WebFetch las notas que uses; si un sitio no carga el cuerpo, usá título y copete. Descartá lo que ya figura en `registro.md`.

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

## 5. Mail (solo si hubo novedades)
Si no hubo ninguna novedad, no mandes mail.
Armá `/home/user/salida/E/mail.html` con un bloque por novedad (mismo contenido que el registro, en HTML simple: `<h3>`, `<p>`, `<ul>`, `<b>`, `<a>`) y una sección final "Fuentes" con el formato Medio | Título (con link) | DD/MM/AAAA. Mandalo con los PDF de las novedades:
```
python3 -I R/herramientas/mail.py --para pedro.rossaroli@mitranicaballero.com \
  --asunto "[<Nombre corto de la empresa>] <hecho principal> · DD/MM/AAAA" \
  --html /home/user/salida/E/mail.html --adjunto <pdf1> --adjunto <pdf2> ...
```
Adjuntá solo los PDF de lo que es novedad (no los del ruido descartado). Las circulares, actas y dictámenes de CONTRAT.AR que vienen como `.txt` van resumidas en el cuerpo del mail; si la circular trae un PDF anexo, adjuntalo.
Si `mail.py` sale con código 3 (faltan credenciales) o 4 (error de la API), mandá el mismo contenido con la herramienta de Gmail del conector (`send_message`, cargala con ToolSearch) **sin adjuntos**, poniendo en cada novedad el link para bajar el PDF (BORA: `https://www.boletinoficial.gob.ar/pdf/aviso/primera/<id>/<fecha>`; CONTRAT.AR: la `url_ficha`). Agregá al final una línea indicando que los adjuntos fallaron y el motivo.

## 6. Commit y push
```
cd R && git add empresas/E && git commit -m "E: corrida DD/MM/AAAA" && git pull --rebase origin main && git push origin main
```
Commiteá siempre que haya cambiado `estado.json`, aunque no haya novedades: es la memoria de la próxima corrida. Si el push choca con otro agente, repetí `git pull --rebase origin main` y `git push` (hasta 4 intentos).

## 7. Cierre
Terminá con un resumen de 2 o 3 líneas: novedades encontradas (o "sin novedades"), si se mandó el mail y con cuántos adjuntos, y cualquier error. Ese resumen llega como notificación al celular.
