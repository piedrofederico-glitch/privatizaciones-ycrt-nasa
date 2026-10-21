#!/usr/bin/env python3
"""Escáner de la primera sección del Boletín Oficial (boletinoficial.gob.ar). Solo biblioteca estándar.

Uso:
  bora.py escanear --empresa DIR_EMPRESA [--empresa OTRA ...] --salida DIR [--fecha AAAAMMDD] [--dias N]
  bora.py aviso ID AAAAMMDD [--salida DIR]      # texto de un aviso (y PDF con --salida)

`escanear` lee el sumario de cada fecha, abre una sola vez el texto completo de cada aviso y lo
compara contra las expresiones regulares `terminos_bora` del config.json de cada empresa. Para cada
aviso que coincide y no figura en el estado.json de esa empresa baja el texto (.txt) y el PDF
oficial a <salida>/<empresa>/bora/, lo marca como visto y deja el detalle en
<salida>/<empresa>/bora.json. Imprime un resumen por empresa. --dias N revisa también los N días anteriores
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


def escanear(empresas, salida, fecha, dias):
    """Escanea una vez el BORA y compara cada aviso con los términos de cada empresa.
    `salida` recibe una subcarpeta por empresa (<salida>/<empresa>/bora)."""
    limite = (datetime.date.today() - datetime.timedelta(days=20)).strftime('%Y%m%d')
    emp = {}
    for e in empresas:
        cfg = json.load(open(os.path.join(e, 'config.json')))
        pe = os.path.join(e, 'estado.json')
        est = json.load(open(pe)) if os.path.exists(pe) else {}
        est.setdefault('bora', {}).setdefault('vistos', {})
        rev = est['bora'].setdefault('revisados', {})  # leídos sin coincidencias, por fecha (20 días)
        for f in [f for f in rev if f < limite]:
            del rev[f]
        nombre_e = os.path.basename(os.path.normpath(e))
        emp[nombre_e] = {'ruta': pe, 'est': est, 'pats': [re.compile(p, re.I) for p in cfg['terminos_bora']],
                         'salida': os.path.join(salida, nombre_e, 'bora'),
                         'res': {'coincidencias': [], 'fechas_revisadas': [], 'errores': []}}
    base = datetime.datetime.strptime(fecha, '%Y%m%d').date()
    for d in range(dias, -1, -1):
        f = (base - datetime.timedelta(days=d)).strftime('%Y%m%d')
        try:
            items = sumario(f)
        except Exception as ex:
            for x in emp.values():
                x['res']['errores'].append(f'sumario {f}: {ex}')
            continue
        for x in emp.values():
            x['res']['fechas_revisadas'].append(f'{f} ({len(items)} avisos)')
        for id_, org, norma, cod in items:
            pend = {k: x for k, x in emp.items()
                    if id_ not in x['est']['bora']['vistos'] and id_ not in x['est']['bora']['revisados'].get(f, [])}
            if not pend:
                continue
            try:
                titulo, cuerpo = aviso(id_, f)
            except Exception as ex:
                for x in pend.values():
                    x['res']['errores'].append(f'aviso {id_}: {ex}')
                continue
            texto = f'{org}\n{norma}\n{cod}\n{titulo}\n{cuerpo}'
            nombre = re.sub(r'[^\w.\-]+', '_', f'{f}_{id_}_{norma or org}')[:100]
            pdf_b = None
            for k, x in pend.items():
                hits = sorted({m.group(0) for p in x['pats'] for m in p.finditer(texto)})
                if not hits:
                    x['est']['bora']['revisados'].setdefault(f, []).append(id_)
                    continue
                os.makedirs(x['salida'], exist_ok=True)
                open(os.path.join(x['salida'], nombre + '.txt'), 'w').write(f'{url_aviso(id_, f)}\n\n{texto}')
                pdf = None
                try:
                    if pdf_b is None:
                        pdf_b = get(f'/pdf/aviso/primera/{id_}/{f}', raw=True)
                    if pdf_b[:4] == b'%PDF':
                        pdf = os.path.join(x['salida'], nombre + '.pdf'); open(pdf, 'wb').write(pdf_b)
                except Exception as ex:
                    x['res']['errores'].append(f'pdf {id_}: {ex}')
                x['est']['bora']['vistos'][id_] = f
                x['res']['coincidencias'].append({'id': id_, 'fecha': f, 'organismo': org, 'norma': norma, 'codigo': cod,
                                                  'terminos': hits, 'url': url_aviso(id_, f),
                                                  'texto': os.path.join(x['salida'], nombre + '.txt'), 'pdf': pdf,
                                                  'anexos': 'tiene anexos: abrirlos desde la url' if 'Ver anexos' in cuerpo else ''})
    for k, x in emp.items():
        json.dump(x['est'], open(x['ruta'], 'w'), ensure_ascii=False, indent=1, sort_keys=True)
        os.makedirs(os.path.join(salida, k), exist_ok=True)
        json.dump(x['res'], open(os.path.join(salida, k, 'bora.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: {'coincidencias': len(x['res']['coincidencias']), 'errores': x['res']['errores'],
                          'archivo': os.path.join(salida, k, 'bora.json')} for k, x in emp.items()}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    es = sp.add_parser('escanear'); es.add_argument('--empresa', action='append', required=True)
    es.add_argument('--salida', required=True)
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
