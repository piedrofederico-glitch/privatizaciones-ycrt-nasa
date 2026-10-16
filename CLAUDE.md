# Seguimiento de privatizaciones: termoeléctricas, ENARSA, NASA, CNEA, YCRT

Cinco agentes independientes (tareas programadas de Claude Code, lunes a viernes) siguen cada uno una empresa. Cada corrida recibe el nombre de su carpeta en `empresas/` y sigue `docs/corrida-diaria.md`.

Destinatario: Pedro, estudiante de derecho en un estudio jurídico de Buenos Aires. Usa los mails como insumo propio y decide qué lleva al Comité del estudio.

## Estructura
- `empresas/<empresa>/config.json`: términos de búsqueda en CONTRAT.AR y en el BORA, y procesos excluidos.
- `empresas/<empresa>/contexto.md`: situación de base, búsquedas web y jurisdicciones a vigilar. Actualizalo cuando un hecho cambie la situación de base.
- `empresas/<empresa>/registro.md`: historial de novedades. Cada entrada resume lo que dice el documento. **Los PDF no se guardan en el repo**: se mandan por mail.
- `empresas/<empresa>/estado.json`: memoria de las herramientas (avisos y documentos ya vistos). Lo escriben los scripts; no lo edites a mano salvo para corregir un error.
- `herramientas/contratar.py`, `herramientas/bora.py`, `herramientas/mail.py`: solo biblioteca estándar de Python. Correlos con `python3 -I`.

## Reglas de redacción (registro y mails)
- Solo hechos: qué pasó y qué va a pasar (próximos pasos con fecha). Nada de lo que alguien piensa, dice, analiza u opina.
- Español rioplatense, registro impersonal. Negrita solo en el núcleo de cada hecho. Nunca uses guion largo (raya) como conector. Sin preámbulos, saludos ni cierres tipo "En resumen".
- Citá número y fecha de cada norma, expediente, proceso o proyecto. Si un dato difiere entre fuentes, indicá la discrepancia. Si algo es solo anunciado o trascendido, decilo.
- Parafraseá: no transcribas copetes ni párrafos de notas periodísticas.

## Qué es novedad
1. Actos que inician o hacen avanzar un procedimiento de privatización: decretos o resoluciones que lo autorizan o lo llaman, pliegos, número de proceso, circulares, cronogramas, prórrogas, consultas, interesados, presentación y apertura de ofertas, ejercicio de derechos de preferencia, dictámenes de evaluación, preadjudicación, adjudicación, transferencia de acciones, tasaciones, cambios societarios orientados a la venta, iniciativas privadas.
2. Presentaciones judiciales contra el procedimiento o que lo absorban: amparos, cautelares, denuncias penales. Incluí versiones periodísticas de que se van a presentar, aclarando que son anunciadas.
3. Iniciativas legislativas contra el procedimiento o que lo absorban: proyectos de ley (Congreso y legislaturas) y de ordenanza o presentaciones de concejos deliberantes. Incluí versiones de que se van a presentar, aclarando que son anunciadas.

## Qué NO es novedad
Accidentes y fallas operativas, despidos, retiros, recortes de estructura, paros, protestas, manifestaciones o declaraciones a favor o en contra, pedidos de informes, proyectos de resolución o de declaración, notas de opinión o análisis sin hecho nuevo, y hechos que ya figuran en `contexto.md` o `registro.md` sin movimiento nuevo.

## Fuentes periodísticas preferidas
Perfil, La Nación, Clarín, iProfesional, Infobae, Parlamentario.com, Palabras del Derecho, Diario Judicial, Página 12, La Prensa, Bichos de Campo, Reuters, Bloomberg, TN, C5N y La Voz del Interior. Complementá con medios regionales o sectoriales cuando estos no cubran un hecho.
