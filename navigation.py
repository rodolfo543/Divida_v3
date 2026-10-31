"""Uma navegação estática comum às áreas do dashboard."""
import re

PAGES = [('index.html', 'Cálculos'), ('vortx.html', 'Conciliação Vórtx'), ('calendario.html', 'Calendário'),
         ('recomposicao.html', 'Recomposição'), ('documentos.html', 'Documentação')]


def with_navigation(html, active):
    links = ''.join(f'<a href="./{file}"' + (' aria-current="page"' if file == active else '') + f'>{label}</a>' for file, label in PAGES)
    nav = '<nav class="workspace-nav" aria-label="Áreas do dashboard"><a class="workspace-brand" href="./index.html" aria-label="AXS Energia · página inicial"><img src="./axs-logo-header.png" alt="AXS Energia" width="126" height="62"></a><div>' + links + '</div></nav>'
    return re.sub(r'<nav class="workspace-nav".*?</nav>', lambda _: nav, html, count=1, flags=re.S)
