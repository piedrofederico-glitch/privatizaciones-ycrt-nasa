# Orquestador: corrida de todas las empresas

Corre de lunes a viernes en tres turnos. La hora límite es la hora a la que tiene que haber salido cada mail. El servidor suele arrancar la tarea entre 5 y 10 minutos después del horario programado:

| Turno | Arranque | Hora límite del mail | `--dias` del BORA |
|---|---|---|---|
| Mañana | 05:20 | 06:00 | 3 los lunes, 1 el resto |
| Tarde | 14:50 | 15:30 | 0 |
| Noche | 17:20 | 18:00 | 0 |

Empresas: `termoelectricas`, `enarsa`, `nasa`, `cnea`, `ycrt`, `belgrano-cargas` (todas las carpetas de `empresas/`).

## 1. Repo
El repo `piedrofederico-glitch/privatizaciones-ycrt-nasa` tiene que estar en `/home/user/privatizaciones-ycrt-nasa` con permiso de escritura. Pasá a main y actualizá: `git checkout main && git pull --rebase origin main`. Si no está clonado y existe la herramienta `mcp__claude-code-remote__add_repo`, usala (access "push") y clonalo.
Verificá el permiso de escritura antes de empezar: `git push --dry-run origin main`. Si falla con 403, seguí igual (los mails salen), pero el estado no se va a guardar: avisalo al principio del resumen final con "SIN PUSH:".

## 2. BORA (una sola pasada para todas)
```
cd /home/user/privatizaciones-ycrt-nasa
python3 -I herramientas/bora.py escanear $(for e in empresas/*/; do printf -- '--empresa %s ' "$e"; done) --salida /home/user/salida --dias D
```
Deja `/home/user/salida/<empresa>/bora.json` con las coincidencias nuevas de cada empresa.
Revisa la primera sección completa y, de la segunda (sociedades), los edictos cuya razón social coincide con los términos. Si el BORA no responde (desde el 21/10/2026 corta las conexiones de los entornos cloud), usa el PDF del día de ARSAT (texto oficial de las dos secciones, solo la edición del día) y, si eso también falla, BOA para la primera sección (resúmenes sin texto oficial). Cuando el BORA vuelve, el escáner retrocede solo hasta el último día que pudo leer (máximo 7). Si se usó un respaldo, empezá el resumen final con "BORA CAÍDO: revisado en ARSAT" (o "en BOA").
Como ARSAT solo tiene la edición del día, **el turno de la mañana es el único que garantiza leer el BORA del día**: si falla, el de la tarde lo reintenta.

## 3. Subagentes en paralelo
Lanzá con la herramienta Agent un subagente por empresa, **todos en el mismo mensaje** para que corran en paralelo. Prompt de cada uno:
> Sos el agente de seguimiento de <nombre de la empresa según empresas/E/config.json>. E=<carpeta>. Hora límite del mail: <HH:MM> (hora de Buenos Aires). Seguí al pie de la letra /home/user/privatizaciones-ycrt-nasa/docs/corrida-diaria.md con E=<carpeta>, respetando las reglas de /home/user/privatizaciones-ycrt-nasa/CLAUDE.md. No hagas commit ni push.

Si a 5 minutos de la hora límite un subagente no terminó, no lo esperes para el resto de los pasos y mencionalo en el resumen.

## 4. Commit y push
```
cd /home/user/privatizaciones-ycrt-nasa && git add empresas && git commit -m "corrida DD/MM/AAAA HH:MM" && git pull --rebase origin main && git push origin main
```
Commiteá siempre que haya cambios en `estado.json`, aunque no haya novedades: es la memoria de la próxima corrida. Si el push falla por un conflicto, repetí `git pull --rebase origin main` y `git push` (hasta 4 intentos).

## 5. Resumen final
Una línea por empresa (novedades o "sin novedades", mail enviado y adjuntos; el mail sale siempre), más errores. Si algún subagente devolvió "MAIL NO ENVIADO", empezá el resumen con eso y las novedades con sus links. Ese resumen llega como notificación al celular.
