#!/usr/bin/env python3
"""Envía un mail con adjuntos por la API de Gmail (HTTPS). Solo biblioteca estándar.

Uso:
  mail.py --para DIRECCION [--cc DIRECCION] --asunto TEXTO --html ARCHIVO.html [--adjunto RUTA ...] [--simular DIR]

Credenciales (variables de entorno del entorno de Claude Code, ver docs/configurar-gmail.md):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

Si los adjuntos superan ~18 MB se reparten en varios mails ("parte 1 de N"). Los adjuntos
repetidos (mismo contenido) se mandan una sola vez.
Códigos de salida: 0 enviado, 3 faltan credenciales, 4 error de la API.
"""
import argparse, base64, hashlib, json, mimetypes, os, sys, urllib.parse, urllib.request
from email.message import EmailMessage

LOTE = 18 * 2**20  # Gmail admite 25 MB por mail contando la codificación base64


def token():
    try:
        datos = {'client_id': os.environ['GMAIL_CLIENT_ID'], 'client_secret': os.environ['GMAIL_CLIENT_SECRET'],
                 'refresh_token': os.environ['GMAIL_REFRESH_TOKEN'], 'grant_type': 'refresh_token'}
    except KeyError as e:
        print(f'Falta la variable de entorno {e}: no se puede mandar con adjuntos', file=sys.stderr)
        sys.exit(3)
    r = urllib.request.urlopen('https://oauth2.googleapis.com/token', urllib.parse.urlencode(datos).encode(), timeout=60)
    return json.load(r)['access_token']


def lotes(adjuntos):
    vistos, actual, peso, out = set(), [], 0, []
    for p in adjuntos:
        b = open(p, 'rb').read()
        h = hashlib.sha256(b).hexdigest()
        if h in vistos:
            continue
        vistos.add(h)
        if actual and peso + len(b) > LOTE:
            out.append(actual); actual, peso = [], 0
        actual.append((p, b)); peso += len(b)
    return out + [actual] if actual or not out else out


def armar(para, asunto, cuerpo, adjuntos, cc=None):
    m = EmailMessage()
    m['To'], m['Subject'] = para, asunto
    if cc:
        m['Cc'] = cc
    m.set_content('Este mail tiene formato HTML.')
    m.add_alternative(cuerpo, subtype='html')
    for p, b in adjuntos:
        tipo = (mimetypes.guess_type(p)[0] or 'application/octet-stream').split('/')
        m.add_attachment(b, maintype=tipo[0], subtype=tipo[1], filename=os.path.basename(p))
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--para', required=True); ap.add_argument('--asunto', required=True)
    ap.add_argument('--cc', help='direcciones en copia, separadas por coma')
    ap.add_argument('--html', required=True); ap.add_argument('--adjunto', action='append', default=[])
    ap.add_argument('--simular', help='en vez de enviar, guarda los .eml en este directorio')
    a = ap.parse_args()
    cuerpo = open(a.html).read()
    partes = lotes(a.adjunto)
    tok = None if a.simular else token()
    for i, adj in enumerate(partes, 1):
        asunto = a.asunto + (f' (parte {i} de {len(partes)})' if len(partes) > 1 else '')
        m = armar(a.para, asunto, cuerpo if i == 1 else f'<p>Continuación de los adjuntos: {asunto}</p>', adj, a.cc)
        if a.simular:
            os.makedirs(a.simular, exist_ok=True)
            open(os.path.join(a.simular, f'mail_{i}.eml'), 'wb').write(bytes(m))
            print(f'simulado {asunto}: {len(adj)} adjunto(s)')
            continue
        rq = urllib.request.Request('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                                    json.dumps({'raw': base64.urlsafe_b64encode(bytes(m)).decode()}).encode(),
                                    {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'})
        try:
            r = json.load(urllib.request.urlopen(rq, timeout=180))
        except urllib.error.HTTPError as e:
            print(f'Error de la API de Gmail {e.code}: {e.read().decode()[:500]}', file=sys.stderr)
            sys.exit(4)
        print(f"enviado {asunto}: {len(adj)} adjunto(s), id {r.get('id')}")


if __name__ == '__main__':
    main()
