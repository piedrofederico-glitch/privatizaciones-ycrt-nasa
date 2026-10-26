#!/usr/bin/env python3
"""Mail único de las 09:00 para la lista DL-PDT, ordenado por proceso de privatización "madre".
Lo redacta la sesión del turno DL (docs/dl.md); esta herramienta da las entradas pendientes y envía.

Uso:
  dl.py pendientes                         entradas de registro.md todavía no informadas, por proceso
  dl.py enviar --html ARCHIVO [--esperar HH:MM] [--simular DIR]
                                           manda el mail y marca como informadas las entradas pendientes
  dl.py marcar --empresa E [--registro ARCHIVO]   marca todas las entradas como informadas (línea de base)

El estado queda en empresas/<empresa>/dl.json. Usa herramientas/mail.py para enviar.
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys, time

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Se manda a la cuenta del estudio; una regla de Outlook lo reenvía a DL-PDT@mitranicaballero.com
PARA, ASUNTO = 'pedro.rossaroli@mitranicaballero.com', 'Privatizaciones'
GRUPOS = [('ENARSA', ['enarsa', 'termoelectricas']), ('NASA', ['nasa']), ('CNEA', ['cnea']),
          ('YCRT', ['ycrt']), ('BCyL', ['belgrano-cargas'])]
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


def pendientes():
    out = []
    for nombre, empresas in GRUPOS:
        for e in empresas:
            _, est = estado(e)
            reg = os.path.join(R, 'empresas', e, 'registro.md')
            out += [(nombre, e, x) for x in (entradas(reg) if os.path.exists(reg) else []) if clave(x) not in est['enviadas']]
    return out


def listar(a):
    p = pendientes()
    for nombre, _ in GRUPOS:
        xs = [x for n, _, x in p if n == nombre]
        print(f'# {nombre}: {len(xs)} entrada(s) pendiente(s)\n')
        print('\n\n'.join(xs) + ('\n' if xs else ''))


def enviar(a):
    p = pendientes()
    if a.esperar:
        h, m = map(int, a.esperar.split(':'))
        ahora = datetime.datetime.now(BA)
        falta = (ahora.replace(hour=h, minute=m, second=0, microsecond=0) - ahora).total_seconds()
        if 0 < falta <= 3600:
            print(f'esperando {int(falta)} s hasta las {a.esperar}', flush=True)
            time.sleep(falta)
    cmd = [sys.executable, '-I', os.path.join(R, 'herramientas', 'mail.py'), '--para', PARA,
           '--asunto', ASUNTO, '--html', a.html] + (['--simular', a.simular] if a.simular else [])
    r = subprocess.run(cmd)
    if r.returncode:
        print(f'DL NO ENVIADO (código {r.returncode})'); sys.exit(4)
    if a.simular:
        return
    for _, empresas in GRUPOS:
        for e in empresas:
            ruta, est = estado(e)
            est['enviadas'] += [clave(x) for _, ee, x in p if ee == e]
            json.dump(est, open(ruta, 'w'), ensure_ascii=False, indent=1)
    print(f'enviado: {len(p)} entrada(s) informadas')


def marcar(a):
    p, est = estado(a.empresa)
    reg = a.registro or os.path.join(R, 'empresas', a.empresa, 'registro.md')
    est['enviadas'] = sorted(set(est['enviadas']) | {clave(x) for x in entradas(reg)})
    json.dump(est, open(p, 'w'), ensure_ascii=False, indent=1)
    print(f'{a.empresa}: {len(est["enviadas"])} entradas marcadas')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('pendientes')
    s = sub.add_parser('enviar'); s.add_argument('--html', required=True); s.add_argument('--esperar'); s.add_argument('--simular')
    s = sub.add_parser('marcar'); s.add_argument('--empresa', required=True); s.add_argument('--registro')
    a = ap.parse_args()
    {'pendientes': listar, 'enviar': enviar, 'marcar': marcar}[a.cmd](a)


if __name__ == '__main__':
    main()
