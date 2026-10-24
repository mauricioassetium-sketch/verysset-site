#!/usr/bin/env python3
"""Agrega el acceso a la consola (app.verysset.com) en todas las páginas del sitio.

Idempotente: si el enlace ya está, no toca nada. Se aplica sobre el HTML generado; si algún día
se regenera con build.py, volver a correrlo.
"""
from pathlib import Path

DESTINO = "https://app.verysset.com/panel"
ETIQUETA = "Console"
NAV = f'<a href="{DESTINO}" data-noi18n>{ETIQUETA}</a>'
MARCA = 'href="partners.html"'

cambiados = 0
for archivo in sorted(Path(".").glob("*.html")):
    texto = archivo.read_text(encoding="utf-8")
    if DESTINO in texto:
        continue
    # Menú de escritorio: después del último enlace del menú principal.
    if f'<nav class="nmenu"' in texto:
        i = texto.index('<nav class="nmenu"')
        j = texto.index("</nav>", i)
        bloque = texto[i:j]
        if MARCA in bloque:
            k = bloque.index(MARCA)
            fin = bloque.index("</a>", k) + 4
            nuevo = bloque[:fin] + NAV + bloque[fin:]
            texto = texto[:i] + nuevo + texto[j:]
    # Menú móvil: antes del enlace de contacto.
    if '<div class="drawer"' in texto:
        i = texto.index('<div class="drawer"')
        j = texto.index("</div>", i)
        bloque = texto[i:j]
        if 'href="contact.html"' in bloque and DESTINO not in bloque:
            k = bloque.index('href="contact.html"')
            inicio = bloque.rindex("<a", 0, k)
            texto = texto[:i] + bloque[:inicio] + f'<a href="{DESTINO}" data-noi18n>{ETIQUETA}</a>' + bloque[inicio:] + texto[j:]
    archivo.write_text(texto, encoding="utf-8")
    cambiados += 1
    print("actualizado:", archivo.name)

print(f"{cambiados} archivo(s)")
