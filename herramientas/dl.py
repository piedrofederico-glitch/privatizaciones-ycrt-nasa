#!/usr/bin/env python3
"""Mail diario de las 09:00 a la lista DL-PDT: las entradas de registro.md que todavía no se le mandaron,
agrupadas por proceso de privatización "madre". Sin adjuntos: indica cada documento para que lo busquen en la fuente.

Uso:
  dl.py enviar [--esperar HH:MM] [--simular DIR]   manda un mail por proceso (con o sin novedades)
  dl.py marcar --empresa E [--registro ARCHIVO]     marca como ya enviadas todas las entradas (línea de base)

El estado queda en empresas/<empresa>/dl.json. Usa herramientas/mail.py para enviar.
"""
import argparse, datetime, hashlib, html, json, os, re, subprocess, sys, time

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARA, CC = 'DL-PDT@mitranicaballero.com', 'pedro.rossaroli@mitranicaballero.com'
GRUPOS = [('ENARSA', ['enarsa', 'termoelectricas']), ('NASA', ['nasa']), ('CNEA', ['cnea']),
          ('YCRT', ['ycrt']), ('Belgrano Cargas', ['belgrano-cargas'])]
BA = datetime.timezone(datetime.timedelta(hours=-3))
MARCA = '<!-- nuevas entradas debajo de esta línea -->'


def entradas(ruta):
    t = open(ruta).read()
    t = t.split(MARCA, 1)[1] if MARCA in t else t
    return [b.strip() for b in re.split(r'(?m)^(?=## )', t) if b.strip().startswith('## ')]


def clave(entrada):
    return hashlib.sha1(entrada.splitlines()[0].strip().encode()).hexdigest()[:16]


def estado(e):
    p = os.path.join(R, 'empresas', e, 'dl.json')
    return p, (json.load(open(p)) if os.path.exists(p) else {'enviadas': []})


def en_linea(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return re.sub(r'(https?://[^\s;|<]+)', r'<a href="\1">\1</a>', s)


def a_html(entrada):
    lineas = entrada.splitlines()
    out, items = [f'<h3>{en_linea(lineas[0][3:].strip())}</h3>'], []
    for l in lineas[1:]:
        l = l.strip()
        if not l.startswith('- '):
            if l and items:
                items[-1] += ' ' + en_linea(l)
            continue
        m = re.match(r'- \*\*PDF enviado por mail:\*\*\s*(.*)', l)
        if m:
            if m.group(1).strip().lower().startswith('no hay'):
                continue
            l = f'- **Documento:** {m.group(1).strip()} (no se adjunta: disponible en la fuente indicada)'
        items.append(en_linea(l[2:]))
    return '\n'.join(out + ['<ul>'] + [f'<li>{i}</li>' for i in items] + ['</ul>'])


def enviar(a):
    if a.esperar:
        h, m = map(int, a.esperar.split(':'))
        ahora = datetime.datetime.now(BA)
        falta = (ahora.replace(hour=h, minute=m, second=0, microsecond=0) - ahora).total_seconds()
        if 0 < falta <= 3600:
            print(f'esperando {int(falta)} s hasta las {a.esperar}', flush=True)
            time.sleep(falta)
    hoy = datetime.datetime.now(BA).strftime('%d/%m/%Y')
    salida = a.simular or '/home/user/salida/dl'
    os.makedirs(salida, exist_ok=True)
    error = False
    for nombre, empresas in GRUPOS:
        nuevas = []
        for e in empresas:
            p, est = estado(e)
            reg = os.path.join(R, 'empresas', e, 'registro.md')
            for x in entradas(reg) if os.path.exists(reg) else []:
                if clave(x) not in est['enviadas']:
                    nuevas.append((e, x))
        if nuevas:
            cuerpo = '\n'.join(a_html(x) for _, x in nuevas)
            asunto = f'[{nombre}] Novedades · {hoy}'
        else:
            cuerpo = '<p>Sin novedades desde el informe anterior.</p>'
            asunto = f'[{nombre}] Sin novedades · {hoy}'
        f = os.path.join(salida, f'{empresas[0]}.html')
        open(f, 'w').write(f'<div style="font-family:Arial,sans-serif">\n{cuerpo}\n</div>')
        cmd = [sys.executable, '-I', os.path.join(R, 'herramientas', 'mail.py'), '--para', PARA, '--cc', CC,
               '--asunto', asunto, '--html', f] + (['--simular', os.path.join(salida, empresas[0])] if a.simular else [])
        r = subprocess.run(cmd)
        if r.returncode:
            print(f'{nombre}: MAIL NO ENVIADO (código {r.returncode})'); error = True
            continue
        print(f'{nombre}: {len(nuevas)} novedad(es)')
        if a.simular:
            continue
        for e in empresas:
            p, est = estado(e)
            est['enviadas'] += [clave(x) for ee, x in nuevas if ee == e and clave(x) not in est['enviadas']]
            json.dump(est, open(p, 'w'), ensure_ascii=False, indent=1)
    sys.exit(4 if error else 0)


def marcar(a):
    p, est = estado(a.empresa)
    reg = a.registro or os.path.join(R, 'empresas', a.empresa, 'registro.md')
    est['enviadas'] = sorted(set(est['enviadas']) | {clave(x) for x in entradas(reg)})
    json.dump(est, open(p, 'w'), ensure_ascii=False, indent=1)
    print(f'{a.empresa}: {len(est["enviadas"])} entradas marcadas')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('enviar'); s.add_argument('--esperar'); s.add_argument('--simular')
    s = sub.add_parser('marcar'); s.add_argument('--empresa', required=True); s.add_argument('--registro')
    a = ap.parse_args()
    {'enviar': enviar, 'marcar': marcar}[a.cmd](a)


if __name__ == '__main__':
    main()
