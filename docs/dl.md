# Mail de las 09:00 a DL-PDT

Lo manda el turno de las 08:20 de la tarea orquestadora, de lunes a viernes. No hay corridas de búsqueda: reenvía lo que ya está en los `registro.md`.

- **Destinatario:** DL-PDT@mitranicaballero.com, con copia a pedro.rossaroli@mitranicaballero.com.
- **Un mail por proceso madre:** ENARSA (incluye las termoeléctricas), NASA, CNEA, YCRT y Belgrano Cargas. Asunto `[<Proceso>] Novedades · DD/MM/AAAA` o `[<Proceso>] Sin novedades · DD/MM/AAAA`.
- **Contenido:** las entradas del registro que todavía no se les mandaron (ventana: desde el mail de las 09:00 anterior; los lunes, desde el viernes). Sin ironías y **sin adjuntos**: cada documento se nombra para que lo busquen en la fuente.
- **Estado:** `empresas/<empresa>/dl.json` (claves de las entradas ya enviadas). Si un mail falla, sus entradas quedan pendientes para el día siguiente.

Los mails a Pedro de las 06:00, 15:30 y 18:00 no cambian.

## Pasos
```
cd /home/user/privatizaciones-ycrt-nasa && git checkout main && git pull --rebase origin main
python3 -I herramientas/dl.py enviar --esperar 09:00
git add empresas && git commit -m "DL 09:00 DD/MM/AAAA" && git pull --rebase origin main && git push origin main
```
`--esperar 09:00` frena el envío hasta las 09:00 de Buenos Aires. Si `dl.py` sale con código 4, algún mail no salió: decilo en el resumen final con "DL NO ENVIADO" y el proceso afectado.
