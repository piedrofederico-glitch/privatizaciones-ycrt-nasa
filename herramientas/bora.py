#!/usr/bin/env python3
"""Escáner de la primera sección del Boletín Oficial (boletinoficial.gob.ar). Solo biblioteca estándar.

Uso:
  bora.py escanear --empresa DIR_EMPRESA --salida DIR [--fecha AAAAMMDD] [--dias N]
  bora.py aviso ID AAAAMMDD [--salida DIR]      # texto de un aviso (y PDF con --salida)

`escanear` lee el sumario de cada fecha, abre el texto completo de cada aviso y lo compara
contra las expresiones regulares `terminos_bora` de <empresa>/config.json. Para cada aviso que
coincide y no figura en estado.json baja el texto (.txt) y el PDF oficial, lo marca como visto
e imprime un JSON con las coincidencias. --dias N revisa también los N días anteriores
(útil los lunes o después de una corrida fallida).
"""
import argparse, datetime, html, json, os, re, sys, time, urllib.request

BASE = 'https://www.boletinoficial.gob.ar'
op = urllib.request.build_opener()
op.addheaders = [('User-Agent', 'Mozilla/5.0')]


def log(*a):
    print(*a, file=sys.stderr)


def get(url, raw=False, intentos=4):
    for i in range(intentos):
        try:
            b = op.open(BASE + url, timeout=90).read()
            return b if raw else b.decode('utf-8', 'ignore')
        except Exception as e:
            if i == intentos - 1:
                raise
            log(f'[reintento {i + 1}] {url}: {e}')
            time.sleep(2 ** (i + 1))


def limpio(h):
    h = re.sub(r'(?s)<script.*?</script>|<style.*?</style>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d)>', '\n', h)
    h = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    return '\n'.join(re.sub(r'[ \t\xa0]+', ' ', l).strip() for l in h.splitlines() if l.strip())


def sumario(fecha):
    """[(id, organismo, norma, codigo)] de la primera sección de esa fecha."""
    t = get(f'/seccion/primera/{fecha}')
    out = []
    for m in re.finditer(r'<a href="/detalleAviso/primera/(\d+)/(\d{8})"[^>]*>(.*?)</a>', t, re.S):
        if m.group(2) != fecha:
            continue
        ps = [limpio(p) for p in re.findall(r'(?s)<p[^>]*>(.*?)</p>', m.group(3))]
        out.append((m.group(1), *(ps + ['', '', ''])[:3]))
    return list(dict((o[0], o) for o in out).values())


def aviso(id_, fecha):
    t = get(f'/detalleAviso/primera/{id_}/{fecha}')
    i = t.find('id="tituloDetalleAviso"'); j = t.find('id="cuerpoDetalleAviso"')
    titulo = limpio(t[t.find('>', i) + 1:t.rfind('<', 0, j)]) if 0 < i < j else ''
    cuerpo = limpio(t[t.find('>', j) + 1:j + 400000]) if j > 0 else ''
    cuerpo = cuerpo[:cuerpo.find('Fecha de publicación')] if 'Fecha de publicación' in cuerpo else cuerpo
    return titulo, cuerpo


def url_aviso(id_, fecha):
    return f'{BASE}/detalleAviso/primera/{id_}/{fecha}'


def escanear(empresa, salida, fecha, dias):
    cfg = json.load(open(os.path.join(empresa, 'config.json')))
    pe = os.path.join(empresa, 'estado.json')
    est = json.load(open(pe)) if os.path.exists(pe) else {}
    vistos = est.setdefault('bora', {}).setdefault('vistos', {})
    # avisos ya leídos sin coincidencias, por fecha (se conservan 20 días)
    revisados = est['bora'].setdefault('revisados', {})
    limite = (datetime.date.today() - datetime.timedelta(days=20)).strftime('%Y%m%d')
    for f in [f for f in revisados if f < limite]:
        del revisados[f]
    pats = [re.compile(p, re.I) for p in cfg['terminos_bora']]
    base = datetime.datetime.strptime(fecha, '%Y%m%d').date()
    res = {'coincidencias': [], 'fechas_revisadas': [], 'errores': []}
    for d in range(dias, -1, -1):
        f = (base - datetime.timedelta(days=d)).strftime('%Y%m%d')
        try:
            items = sumario(f)
        except Exception as e:
            res['errores'].append(f'sumario {f}: {e}'); continue
        res['fechas_revisadas'].append(f'{f} ({len(items)} avisos)')
        for id_, org, norma, cod in items:
            if id_ in vistos or id_ in revisados.get(f, []):
                continue
            try:
                titulo, cuerpo = aviso(id_, f)
            except Exception as e:
                res['errores'].append(f'aviso {id_}: {e}'); continue
            texto = f'{org}\n{norma}\n{cod}\n{titulo}\n{cuerpo}'
            hits = sorted({m.group(0) for p in pats for m in p.finditer(texto)})
            if not hits:
                revisados.setdefault(f, []).append(id_)
                continue
            os.makedirs(salida, exist_ok=True)
            nombre = re.sub(r'[^\w.\-]+', '_', f'{f}_{id_}_{norma or org}')[:100]
            open(os.path.join(salida, nombre + '.txt'), 'w').write(f'{url_aviso(id_, f)}\n\n{texto}')
            pdf = None
            try:
                b = get(f'/pdf/aviso/primera/{id_}/{f}', raw=True)
                if b[:4] == b'%PDF':
                    pdf = os.path.join(salida, nombre + '.pdf'); open(pdf, 'wb').write(b)
            except Exception as e:
                res['errores'].append(f'pdf {id_}: {e}')
            vistos[id_] = f
            res['coincidencias'].append({'id': id_, 'fecha': f, 'organismo': org, 'norma': norma, 'codigo': cod,
                                         'terminos': hits, 'url': url_aviso(id_, f),
                                         'texto': os.path.join(salida, nombre + '.txt'), 'pdf': pdf,
                                         'anexos': 'tiene anexos: abrirlos desde la url' if 'Ver anexos' in cuerpo else ''})
    json.dump(est, open(pe, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    es = sp.add_parser('escanear'); es.add_argument('--empresa', required=True); es.add_argument('--salida', required=True)
    es.add_argument('--fecha', default=datetime.date.today().strftime('%Y%m%d')); es.add_argument('--dias', type=int, default=0)
    av = sp.add_parser('aviso'); av.add_argument('id'); av.add_argument('fecha'); av.add_argument('--salida')
    a = ap.parse_args()
    if a.cmd == 'escanear':
        escanear(a.empresa, a.salida, a.fecha, a.dias)
    else:
        titulo, cuerpo = aviso(a.id, a.fecha)
        print(f'{url_aviso(a.id, a.fecha)}\n{titulo}\n\n{cuerpo}')
        if a.salida:
            os.makedirs(a.salida, exist_ok=True)
            open(os.path.join(a.salida, f'{a.fecha}_{a.id}.pdf'), 'wb').write(get(f'/pdf/aviso/primera/{a.id}/{a.fecha}', raw=True))
