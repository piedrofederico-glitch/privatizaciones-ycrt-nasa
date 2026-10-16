#!/usr/bin/env python3
"""Scraper de la vista pública (ciudadano) de CONTRAT.AR. Solo biblioteca estándar.

Uso:
  contratar.py buscar TEXTO [TEXTO ...]
  contratar.py ficha --nombre TEXTO [--numero N | --fila 1] [--descargar DIR]
  contratar.py revisar --empresa DIR_EMPRESA --salida DIR

`revisar` es el modo diario: busca los términos de <empresa>/config.json, lista los procesos
candidatos que todavía no están en estado.json y, para cada proceso seguido, abre la ficha y
baja SOLO los documentos que no figuran como vistos. Actualiza estado.json e imprime un JSON
con las novedades. Para empezar a seguir o descartar un candidato:
  contratar.py seguir --empresa DIR --numero N --termino TEXTO
  contratar.py descartar --empresa DIR --numero N

Usar siempre www.contratar.gob.ar: el dominio sin www corta la conexión.
La búsqueda rápida por número no devuelve resultados en la vista pública: se busca por nombre
y se filtra por número.
"""
import argparse, datetime, html, http.cookiejar, json, os, re, sys, time, urllib.parse, urllib.request

BASE = 'https://www.contratar.gob.ar/'
BUSCAR = 'BuscarAvanzado.aspx'
MAX_MB = 20  # tope por archivo: el mail admite 25 MB en total
UA = [('User-Agent', 'Mozilla/5.0')]
AJAX = UA + [('X-MicrosoftAjax', 'Delta=true'), ('X-Requested-With', 'XMLHttpRequest')]
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


class Grande(Exception):
    pass


def log(*a):
    print(*a, file=sys.stderr)


def req(url, data=None, ajax=False, raw=False, intentos=4):
    url = urllib.parse.urljoin(BASE, url)
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    op.addheaders = AJAX if ajax else UA
    for i in range(intentos):
        try:
            r = op.open(url, body, timeout=90)
            largo = int(r.headers.get('Content-Length') or 0)
            if raw and largo > MAX_MB * 2**20:
                r.close()
                raise Grande(f'{largo / 2**20:.0f} MB', r.headers)
            b = r.read()
            return (b, r.headers) if raw else b.decode('utf-8', 'ignore')
        except Grande:
            raise
        except Exception as e:
            if i == intentos - 1:
                raise
            log(f'[reintento {i + 1}] {url[:80]}: {e}')
            time.sleep(2 ** (i + 1))


def texto(h):
    h = re.sub(r'(?s)<script.*?</script>|<style.*?</style>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d)>', '\n', h)
    h = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    return '\n'.join(re.sub(r'[ \t\xa0]+', ' ', l).strip() for l in h.splitlines() if l.strip())


def hidden(t):
    return {n: html.unescape(v) for n, v in
            re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', t)}


def delta(t):
    """Respuesta parcial de MS Ajax: len|tipo|id|contenido|"""
    out, i = [], 0
    while i < len(t):
        a = t.index('|', i); n = int(t[i:a])
        b = t.index('|', a + 1); c = t.index('|', b + 1)
        out.append((t[a + 1:b], t[b + 1:c], t[c + 1:c + 1 + n])); i = c + 2 + n
    return out


def postback(f, target, panel='ctl00$CPH1$UpdatePanel1'):
    f = dict(f, __EVENTTARGET=target, __EVENTARGUMENT='', __ASYNCPOST='true')
    f['ctl00$ScriptManager1'] = f'{panel}|{target}'
    d = delta(req(BUSCAR, f, ajax=True))
    for tipo, idd, c in d:
        if tipo == 'hiddenField':
            f[idd] = c
    return f, d


def form_busqueda(nombre):
    f = hidden(req(BUSCAR))
    f.update({'ctl00$CPH1$txtNombrePliego': nombre, 'ctl00$CPH1$txtNumeroProceso': '',
              'ctl00$CPH1$txtExpediente': '', 'ctl00$CPH1$ddlJurisdicion': '-2',
              'ctl00$CPH1$ddlUnidadEjecutora': '-2', 'ctl00$CPH1$ddlTipoProceso': '-2',
              'ctl00$CPH1$ddlEstadoProceso': '-2', 'ctl00$CPH1$ddlRubro': '-2',
              'ctl00$CPH1$ddlResultadoOrdenadoPor': 'aux.FechaActoApertura'})
    f, d = postback(f, 'ctl00$CPH1$btnListarPliegoAvanzado')
    return f, ''.join(c for t, _, c in d if t == 'updatePanel')


def filas(h):
    res = []
    for tr in re.findall(r'(?s)<tr>(.*?)</tr>', h[h.find('GridListaPliegos'):]):
        m = re.search(r"__doPostBack\(&#39;([^&]+lnkNumeroProceso)&#39;", tr)
        if not m:
            continue
        celdas = [texto(c).replace('\n', ' ') for c in re.findall(r'(?s)<td[^>]*>(.*?)</td>', tr)]
        res.append(dict(zip(['numero', 'nombre', 'tipo', 'apertura', 'estado', 'unidad'], celdas), _target=m.group(1)))
    return res


def buscar(nombre, numero=''):
    """Busca por nombre; con numero, filtra las filas por ese número de proceso."""
    for i in range(4):  # el portal a veces devuelve el panel vacío sin mensaje: se reintenta
        f, h = form_busqueda(nombre)
        rs = filas(h)
        if rs or 'No se han encontrado' in h:
            break
        time.sleep(3 * (i + 1))
    else:
        log(f'[aviso] {nombre!r}: respuesta vacía tras 4 intentos (portal inestable o búsqueda muy amplia)')
        rs = None
    if rs is None:
        return f, None
    return f, [r for r in rs if r['numero'] == numero] if numero else rs


def abrir_ficha(nombre, numero='', fila=1):
    f, rs = buscar(nombre, numero)
    if not rs:
        raise LookupError(f'Sin resultados para {nombre!r} {numero}')
    r = rs[min(fila, len(rs)) - 1]
    _, d = postback(f, r['_target'])
    url = urllib.parse.unquote(next(c for t, _, c in d if t == 'pageRedirect'))
    return r, url, req(url)


def seguro(n):
    return re.sub(r'[^\w.\-]+', '_', n)[:120]


def fila_de(t, marca):
    """Texto de la fila <tr> que contiene `marca` (sirve de clave estable del documento)."""
    i = t.find(marca)
    a = t.rfind('<tr', 0, i); b = t.find('</tr>', i)
    return re.sub(r'\s+', ' ', texto(t[a:b])).strip() if a >= 0 and b > 0 else ''


def items(t):
    """Documentos de la ficha, cada uno con una clave estable entre corridas."""
    out = []
    for clave_c in re.findall(r"VerCircularCiudadano\(&#39;([^&]+)&#39;", t):
        out.append({'tipo': 'circular', 'clave': 'circular:' + fila_de(t, clave_c), 'circ': clave_c})
    for patron, tipo in [(r"(ctl00\$CPH1\$UCVistaPreviaPliego\$UCAnexos\$rptAnexos\$[^&]+btnVerAnexo)", 'anexo'),
                         (r"(ctl00\$CPH1\$UCVistaPreviaPliego\$UC_ActosAdministrativos\$gvActosAdministrativos\$[^&]+btnVer)", 'acto'),
                         (r"(ctl00\$CPH1\$UCVistaPreviaPliego\$UC_CondicionesGenerales\$gvActosAdministrativos\$[^&]+btnVer)", 'condiciones_generales')]:
        for tg in dict.fromkeys(re.findall(patron, t)):
            out.append({'tipo': tipo, 'clave': f'{tipo}:' + fila_de(t, tg.replace('$', '_')), 'target': tg})
    for u in dict.fromkeys(re.findall(r'&quot;(/EVALUACIONOFERTA/[^&]+\.aspx\?qs=[^&]+)&quot;', t)):
        pag = u.split('?')[0].split('/')[-1]
        tipo = ('acta_apertura' if 'Acta' in pag else 'dictamen_preadjudicacion' if 'PreAdjudicar' in pag
                else 'dictamen_preseleccion' if 'Preseleccion' in pag else 'evaluacion')
        out.append({'tipo': tipo, 'clave': f'{tipo}:' + fila_de(t, u), 'url': u})
    # si dos filas quedan con el mismo texto, se desambiguan por orden
    vistos = {}
    for it in out:
        n = vistos[it['clave']] = vistos.get(it['clave'], 0) + 1
        if n > 1:
            it['clave'] += f' #{n}'
    return out


def bajar(it, url_ficha, t, destino):
    """Baja un documento a `destino`. Devuelve (archivo|None, nota)."""
    os.makedirs(destino, exist_ok=True)
    if it['tipo'] == 'circular':
        ct = texto(req('/PLIEGO/VistaPreviaCircularCiudadano.aspx?qs=' + urllib.parse.quote(it['circ'])))
        num = re.search(r'Número de circular\s*(\d+)', ct)
        fn = f"circular_{num.group(1) if num else seguro(it['circ'])}.txt"
        open(os.path.join(destino, fn), 'w').write(ct)
        return fn, ''
    if 'url' in it:
        fn = seguro(it['tipo'] + '_' + it['clave'].split(':', 1)[1][:60]) + '.txt'
        open(os.path.join(destino, fn), 'w').write(texto(req(it['url'])))
        return fn, ''
    f = dict(hidden(t), __EVENTTARGET=it['target'], __EVENTARGUMENT='')
    try:
        b, hd = req(url_ficha, f, raw=True)
    except Grande as g:
        m = re.search(r'filename=([^;]+)', g.args[1].get('Content-Disposition') or '')
        return None, f"{urllib.parse.unquote(m.group(1)).strip(chr(34)) if m else it['tipo']}: pesa {g.args[0]}, no se baja (tope {MAX_MB} MB)"
    m = re.search(r'filename=([^;]+)', hd.get('Content-Disposition') or '')
    if b[:4] != b'%PDF':
        return None, f"respuesta no PDF ({hd.get('Content-Type')})"
    fn = seguro(urllib.parse.unquote(m.group(1)).strip('"') if m else it['tipo'] + '.pdf')
    open(os.path.join(destino, fn), 'wb').write(b)
    return fn, ''


def ficha(nombre, numero='', fila=1, destino=None):
    meta, url, t = abrir_ficha(nombre, numero, fila)
    txt = texto(t)
    i = txt.find('Número del Proceso'); txt = txt[max(i, 0):]
    j = txt.find('Volver'); txt = txt[:j] if j > 0 else txt
    print(f"# {meta['numero']} | {meta['nombre']} | {meta['estado']} | {meta['unidad']}\n\n{txt}")
    if destino:
        os.makedirs(destino, exist_ok=True)
        open(os.path.join(destino, 'ficha.txt'), 'w').write(txt)
        for it in items(t):
            log(it['tipo'], *bajar(it, url, t, destino))


# ---------- modo diario por empresa ----------

def cargar(empresa):
    cfg = json.load(open(os.path.join(empresa, 'config.json')))
    p = os.path.join(empresa, 'estado.json')
    est = json.load(open(p)) if os.path.exists(p) else {}
    est.setdefault('contratar', {}).setdefault('procesos', {})
    est['contratar'].setdefault('descartados', [])
    return cfg, est


def guardar(empresa, est):
    json.dump(est, open(os.path.join(empresa, 'estado.json'), 'w'), ensure_ascii=False, indent=1, sort_keys=True)


def revisar(empresa, salida):
    cfg, est = cargar(empresa)
    c = est['contratar']
    conocidos = set(c['procesos']) | set(c['descartados']) | set(cfg.get('excluir_procesos', []))
    res = {'candidatos': [], 'procesos': [], 'errores': []}
    vistos_ahora = set()
    for q in cfg['terminos_contratar']:
        try:
            _, rs = buscar(q)
        except Exception as e:
            res['errores'].append(f'buscar {q!r}: {e}'); continue
        if rs is None:
            res['errores'].append(f'buscar {q!r}: el portal no respondió'); continue
        for r in rs:
            if r['numero'] not in conocidos and r['numero'] not in vistos_ahora:
                vistos_ahora.add(r['numero'])
                res['candidatos'].append({k: v for k, v in r.items() if k != '_target'} | {'termino': q})
    hoy = datetime.date.today().isoformat()
    for num, p in c['procesos'].items():
        if p.get('cerrado'):
            continue
        try:
            meta, url, t = abrir_ficha(p['termino'], num)
        except Exception as e:
            res['errores'].append(f'ficha {num}: {e}'); continue
        info = {'numero': num, 'nombre': meta['nombre'], 'estado': meta['estado'], 'url_ficha': urllib.parse.urljoin(BASE, url),
                'estado_anterior': p.get('estado'), 'nuevos': []}
        destino = os.path.join(salida, seguro(num))
        os.makedirs(destino, exist_ok=True)
        txt = texto(t)
        open(os.path.join(destino, 'ficha.txt'), 'w').write(txt[max(txt.find('Número del Proceso'), 0):])
        vistos = p.setdefault('vistos', {})
        for it in items(t):
            if it['clave'] in vistos:
                continue
            try:
                fn, nota = bajar(it, url, t, destino)
            except Exception as e:
                res['errores'].append(f"{num} {it['clave'][:60]}: {e}"); continue
            vistos[it['clave']] = hoy
            info['nuevos'].append({'tipo': it['tipo'], 'descripcion': it['clave'].split(':', 1)[1],
                                   'archivo': os.path.join(destino, fn) if fn else None, 'nota': nota})
        p.update(estado=meta['estado'], nombre=meta['nombre'], ultima_revision=hoy)
        res['procesos'].append(info)
    guardar(empresa, est)
    print(json.dumps(res, ensure_ascii=False, indent=1))


def seguir(empresa, numero, termino):
    cfg, est = cargar(empresa)
    est['contratar']['procesos'].setdefault(numero, {'termino': termino, 'desde': datetime.date.today().isoformat()})
    guardar(empresa, est)
    print(f'{numero} agregado: la próxima `revisar` baja todos sus documentos')


def descartar(empresa, numero):
    cfg, est = cargar(empresa)
    if numero not in est['contratar']['descartados']:
        est['contratar']['descartados'].append(numero)
    guardar(empresa, est)
    print(f'{numero} descartado')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('buscar').add_argument('textos', nargs='+')
    fi = sp.add_parser('ficha'); fi.add_argument('--nombre', required=True); fi.add_argument('--numero', default='')
    fi.add_argument('--fila', type=int, default=1); fi.add_argument('--descargar')
    rv = sp.add_parser('revisar'); rv.add_argument('--empresa', required=True); rv.add_argument('--salida', required=True)
    sg = sp.add_parser('seguir'); sg.add_argument('--empresa', required=True); sg.add_argument('--numero', required=True)
    sg.add_argument('--termino', required=True)
    ds = sp.add_parser('descartar'); ds.add_argument('--empresa', required=True); ds.add_argument('--numero', required=True)
    a = ap.parse_args()
    if a.cmd == 'buscar':
        for q in a.textos:
            _, rs = buscar(q)
            print(f"== {q}: {'sin respuesta del portal' if rs is None else f'{len(rs)} resultado(s)'}")
            for r in rs or []:
                print(' | '.join(r[k] for k in ['numero', 'nombre', 'tipo', 'apertura', 'estado', 'unidad']))
    elif a.cmd == 'ficha':
        ficha(a.nombre, a.numero, a.fila, a.descargar)
    elif a.cmd == 'revisar':
        revisar(a.empresa, a.salida)
    elif a.cmd == 'seguir':
        seguir(a.empresa, a.numero, a.termino)
    else:
        descartar(a.empresa, a.numero)
