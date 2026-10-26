# Mail de las 09:00 para DL-PDT

Lo manda el turno de las 08:20 de la tarea orquestadora, de lunes a viernes. No hace búsquedas nuevas: sintetiza lo que ya está en `contexto.md` y `registro.md`. Los mails a Pedro de las 06:00, 15:30 y 18:00 no cambian.

- **Destino:** un único mail a pedro.rossaroli@mitranicaballero.com con asunto `Privatizaciones - Resumen PDT`. Una regla de Outlook de esa cuenta (asunto que incluye "Resumen PDT") lo reenvía a DL-PDT@mitranicaballero.com (la lista rechaza remitentes externos).
- **Ventana:** las entradas del registro que todavía no se informaron (desde el mail de las 09:00 anterior; los lunes, desde el viernes). Estado en `empresas/<empresa>/dl.json`.

## Formato
Un párrafo por proceso madre, siempre en este orden y aunque no haya novedades: **ENARSA** (incluye las termoeléctricas), **NASA**, **CNEA**, **YCRT**, **BCyL**, **AySA**, **Intercargo**.
```
<p><b>BCyL:</b> Sin novedades. Las consultas finalizan el 28/10/2026. Las ofertas se presentan hasta el 11/11/2026. La apertura de ofertas es el 11/11/2026 a las 10:00.</p>
<p><b>NASA:</b> Sin novedades. No existe licitación abierta.</p>
```
- **Primero la novedad, después el estado.** Si hay novedad, reemplazá "Sin novedades." por una o dos oraciones con el hecho, su número y su fecha (por ejemplo, el amparo de la Municipalidad de Tafí Viejo contra la cesión de los talleres). Si es solo anunciada o trascendida, decilo.
- **Estado:** una o dos oraciones con la fase actual según la sección "Situación" de `contexto.md` y el registro: cronograma vigente con fechas y horas, o "No existe licitación abierta." Usá el dato más reciente; si el registro trae una prórroga o una circular que cambia fechas, manda el registro.
- **Filtro estricto:** solo hechos que afectan el procedimiento de privatización (actos, cronograma, ofertas, presentaciones judiciales o legislativas contra el procedimiento). Aunque estén en el registro o aludan a la privatización, no van accidentes, descarrilamientos, despidos, paros ni declaraciones.
- **Súper sintético:** nada de links, fuentes, adjuntos ni ironías. Rioplatense impersonal, sin raya, sin saludo ni cierre. Fechas DD/MM/AAAA y horas HH:MM.

## Pasos
```
cd /home/user/privatizaciones-ycrt-nasa && git checkout main && git pull --rebase origin main
python3 -I herramientas/dl.py pendientes
```
Leé la salida y la sección "Situación" de `contexto.md` de cada empresa. Escribí `/home/user/salida/dl.html` con el formato de arriba y mandalo (espera hasta las 09:00 de Buenos Aires):
```
python3 -I herramientas/dl.py enviar --html /home/user/salida/dl.html --esperar 09:00
git add empresas && git commit -m "DL 09:00 DD/MM/AAAA" && git pull --rebase origin main && git push origin main
```
Si `dl.py` sale con código 4, el mail no salió y las entradas quedan pendientes para el día siguiente: empezá el resumen final con "DL NO ENVIADO" y el motivo. Si salió, el resumen final es el texto del mail.
