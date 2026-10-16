# Credenciales de Gmail para mandar mails con adjuntos

`herramientas/mail.py` manda los mails por la API de Gmail desde la cuenta que autorices (por ejemplo, piedrofederico@gmail.com). Necesita tres variables de entorno: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` y `GMAIL_REFRESH_TOKEN`. Se configura una sola vez.

## 1. Proyecto y API (console.cloud.google.com)
1. Creá un proyecto nuevo (por ejemplo, "seguimiento-privatizaciones").
2. **APIs y servicios > Biblioteca**: buscá **Gmail API** y habilitala.

## 2. Pantalla de consentimiento
1. **APIs y servicios > Pantalla de consentimiento de OAuth** (o "Google Auth Platform"): tipo **Externo**.
2. Completá nombre de la app y tu mail como contacto. En **Permisos (scopes)** agregá `https://www.googleapis.com/auth/gmail.send`.
3. En **Usuarios de prueba** agregá la cuenta que va a mandar los mails.
4. **Publicá la app (estado "En producción")**. Si queda en "Prueba", el token vence a los 7 días y los mails dejan de salir. Al estar sin verificar, Google muestra una advertencia al autorizar: es esperable porque la app es tuya.

## 3. Credencial OAuth
1. **APIs y servicios > Credenciales > Crear credenciales > ID de cliente de OAuth**.
2. Tipo: **Aplicación web**. En **URI de redireccionamiento autorizados** agregá `https://developers.google.com/oauthplayground`.
3. Guardá el **ID de cliente** y el **Secreto del cliente**.

## 4. Refresh token (developers.google.com/oauthplayground)
1. Engranaje (arriba a la derecha): tildá **Use your own OAuth credentials** y pegá el ID y el secreto.
2. En "Input your own scopes" escribí `https://www.googleapis.com/auth/gmail.send` y tocá **Authorize APIs**. Entrá con la cuenta que va a mandar los mails y aceptá.
3. Tocá **Exchange authorization code for tokens** y copiá el **Refresh token**.

## 5. Cargar las variables en el entorno de Claude Code
En la sesión de Claude Code: menú del entorno en la barra de título > **Edit** > variables de entorno (o "Network secrets" si aparece esa sección). Cargá:
```
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
```
Las sesiones nuevas (incluidas las de las tareas programadas) las toman automáticamente. No pegues estos valores en el chat.

## Prueba
En una sesión nueva:
```
echo '<p>Prueba</p>' > /tmp/p.html
python3 -I herramientas/mail.py --para pedro.rossaroli@mitranicaballero.com --asunto "Prueba seguimiento" --html /tmp/p.html
```
Mientras falten las credenciales, los agentes mandan el mail por el conector de Gmail con links en lugar de adjuntos.
