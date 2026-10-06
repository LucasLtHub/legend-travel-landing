#!/usr/bin/env python3
"""
tools/css_v2.py — lleva assets/design.css al lenguaje de la home final (v2).

Parte del design.css v1 que está en git (HEAD) y aplica reemplazos puntuales
(tokens, tipografía, cabecera, hero, reveals) y agrega al final los bloques
nuevos: botones de la home, medios de pago como tarjeta, FAQ como
conversación, cierre de contacto con íconos vivos, historia con línea que se
enciende y pie con logo + claim. Los bloques de las secciones se EXTRAEN de
index.html (la referencia) y se adaptan a las clases de las subpáginas, así
una corrección en la home se propaga corriendo esto de nuevo.

    python tools/css_v2.py        # reescribe assets/design.css
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def git(ref_path):
    return subprocess.run(['git', 'show', ref_path], cwd=ROOT, capture_output=True, text=True, encoding='utf-8').stdout

def home_block(css, inicio, fin):
    """Bloque del <style> de la home entre dos comentarios/marcadores."""
    i = css.index(inicio); j = css.index(fin, i + len(inicio))
    return css[i:j].rstrip() + '\n'

def sustituir(css, viejo, nuevo, nombre):
    if viejo not in css:
        raise SystemExit(f'no encontré en design.css v1 el bloque: {nombre}')
    return css.replace(viejo, nuevo, 1)

def main():
    v1 = git('d3f37ba:assets/design.css')  # última v1 commiteada (antes del lote 1 del v2)
    home = (ROOT / 'index.html').read_text(encoding='utf-8')
    hcss = home[home.index('<style>') + 7:home.index('</style>')]
    css = v1

    # ---- cabecera del archivo
    css = sustituir(css, '   Legend Travel — sistema de diseño compartido\n',
        '   Legend Travel — sistema de diseño compartido · v2 (sincronizado con la home final)\n'
        '   Generado por tools/css_v2.py a partir del v1 y del <style> de index.html.\n', 'cabecera')

    # ---- tokens: mismos grises y cabecera de 96px también en móvil (como la home)
    css = sustituir(css, '--ink:#0E232D;--ink-2:rgba(14,35,45,.66);--ink-3:rgba(14,35,45,.46);', '--ink:#0E232D;--ink-2:rgba(14,35,45,.64);--ink-3:rgba(14,35,45,.44);', 'tokens ink')
    css = sustituir(css, '--gutter:20px;--nav-h:76px;', '--gutter:20px;--nav-h:96px;', 'nav-h')
    css = sustituir(css, '@media(min-width:1024px){:root{--nav-h:96px}}\n', '', 'nav-h media')
    css = sustituir(css, 'html{-webkit-text-size-adjust:100%}', 'html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}', 'html')

    # ---- tipografía: escala de la home, kicker sin "//"
    css = sustituir(css, '.h2{font-size:clamp(34px,4.8vw,68px);font-weight:700;letter-spacing:-.035em;line-height:1.03;',
                         '.h2{font-size:clamp(40px,6vw,88px);font-weight:700;letter-spacing:-.035em;line-height:1.02;', 'h2')
    css = sustituir(css, '.h2[style*="font-size"]{font-size:clamp(30px,3.8vw,54px)!important}',
                         '.h2[style*="font-size"],.h2.md{font-size:clamp(36px,4.6vw,68px)!important}', 'h2 chico')
    css = sustituir(css, ".kicker{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.2em;color:var(--red);margin-bottom:18px}\n.kicker::before{content:'// '}\n",
                         ".kicker{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.18em;color:var(--red);margin-bottom:24px}\n", 'kicker')
    css = sustituir(css, ".hero-kicker::before{content:'// '}\n", '', 'hero-kicker')
    css = sustituir(css, '.lead{font-size:clamp(17px,1.3vw,20px);line-height:1.6;color:var(--ink-2)}',
                         '.lead{font-size:clamp(17px,1.3vw,20px);line-height:1.6;color:var(--ink-2);max-width:52ch}', 'lead')

    # ---- secciones: el aire de la home
    css = sustituir(css, '.sec{padding-top:clamp(88px,12vh,152px);padding-bottom:clamp(88px,12vh,152px)}',
                         '.sec{padding-top:112px;padding-bottom:112px}\n@media(min-width:1024px){.sec{padding-top:168px;padding-bottom:168px}}', 'sec')

    # ---- reveals con retardo escalonado (--d)
    css = sustituir(css, '.rv{opacity:0;transform:translateY(28px);transition:opacity 1s var(--ease),transform 1.1s var(--ease)}',
                         '.rv{opacity:0;transform:translateY(28px);transition:opacity 1s var(--ease),transform 1.1s var(--ease);transition-delay:var(--d,0ms)}', 'rv')

    # ---- cabecera: links a la derecha + pastilla, como la home
    css = sustituir(css,
        '  .navlinks{display:flex;position:absolute;inset:0;align-items:center;justify-content:center;gap:clamp(18px,2.2vw,34px);pointer-events:none}\n'
        '  .navlinks a{pointer-events:auto;position:relative;font-size:clamp(15px,1.25vw,17px);font-weight:500;color:inherit;white-space:nowrap;opacity:.9;transition:opacity .3s}\n',
        '  .navlinks{display:flex;align-items:center;gap:clamp(20px,2.4vw,34px);margin-left:auto;font-size:15px;font-weight:500}\n'
        '  .navlinks a{position:relative;font-size:15px;font-weight:500;color:inherit;white-space:nowrap;opacity:.86;transition:opacity .3s}\n', 'navlinks')
    css = sustituir(css,
        '  .navlinks .btn-red{position:absolute;right:0;top:50%;transform:translateY(-50%);padding:13px 22px;font-size:14px;font-weight:700;opacity:1;color:#fff}\n'
        '  .navlinks .btn-red:hover{color:#fff}\n'
        '  .navlinks .btn-red:active{transform:translateY(-50%) scale(.97)!important}\n',
        '  .navlinks .btn-red{margin-left:8px;padding:13px 22px;border-radius:999px;background:var(--red);font-size:14px;font-weight:700;opacity:1;color:#fff;transition:background .45s var(--ease),transform .6s var(--ease)}\n'
        '  .navlinks .btn-red:hover{color:#fff;background:var(--bur)}\n'
        '  .navlinks .btn-red:active{transform:scale(.97)!important}\n', 'nav btn')
    css = sustituir(css, '.navtoggle{display:flex;align-items:center;justify-content:center;width:44px;height:44px;margin:0 -10px 0 auto;color:inherit}',
                         '.navtoggle{display:flex;align-items:center;justify-content:center;width:44px;height:44px;margin:0 -10px 0 auto;color:inherit}\n@media(min-width:1024px){.navlinks{margin-left:auto}}', 'navtoggle')

    # ---- hero: composición de la home (título grande abajo a la izquierda, dos líneas que suben)
    css = sustituir(css,
        '.hero-inner{position:relative;z-index:10;width:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;min-height:0;padding-top:calc(var(--nav-h) + 44px);padding-bottom:clamp(40px,7vh,72px)}\n'
        '@media(max-width:767px){.hero-inner{padding-top:calc(var(--nav-h) + 66px)}}\n',
        '.hero-inner{position:relative;z-index:10;width:100%;max-width:1360px;margin:0 auto;display:grid;grid-template-columns:minmax(0,1fr);align-content:end;gap:26px;text-align:left;min-height:100vh;min-height:100svh;padding-top:calc(var(--nav-h) + 56px);padding-bottom:clamp(36px,6vh,56px)}\n'
        '.hero h1.fade{opacity:1;transform:none;transition:none}\n'
        '.hero h1 .ln{display:block;overflow:hidden;padding:0 .08em .1em 0;margin-bottom:-.1em}\n'
        '.hero h1 .ln>span{display:block;transform:translateY(112%);animation:rise 1.3s var(--ease) forwards}\n'
        '.hero h1 .ln:nth-child(1)>span{animation-delay:.2s}.hero h1 .ln:nth-child(2)>span{animation-delay:.34s}.hero h1 .ln:nth-child(3)>span{animation-delay:.48s}.hero h1 .ln:nth-child(4)>span{animation-delay:.62s}\n'
        '@keyframes rise{to{transform:translateY(0)}}\n'
        '@media(min-width:1024px){\n'
        '  .hero-inner{grid-template-columns:1.25fr .75fr;grid-template-areas:"h1 sub" "h1 btns" "stats stats";column-gap:64px;row-gap:22px;align-items:end}\n'
        '  .hero h1{grid-area:h1;align-self:end}.hero-sub{grid-area:sub;align-self:end}.hero-btns{grid-area:btns}.hero-stats,.hero-cred-row,.hero-chips{grid-area:stats}\n'
        '}\n', 'hero-inner')
    css = sustituir(css,
        '.hero h1{font-size:clamp(36px,6vw,92px);font-weight:700;letter-spacing:-.04em;line-height:1;color:#fff;text-shadow:0 2px 40px rgba(14,35,45,.35);margin:0;padding-bottom:.08em;max-width:18ch;text-wrap:balance}\n'
        '.hero-sub{margin:clamp(18px,3vh,28px) auto 0;max-width:60ch;font-size:clamp(16px,1.25vw,19px);line-height:1.55;font-weight:400;color:rgba(255,255,255,.88);text-shadow:0 1px 18px rgba(14,35,45,.5)}\n'
        '.hero-btns{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;margin-top:clamp(24px,4.4vh,40px)}\n'
        '.hero-stats,.hero-cred-row,.hero-chips{display:flex;flex-wrap:wrap;justify-content:center;gap:0;margin-top:clamp(28px,5vh,52px);padding-top:0;border-top:1px solid rgba(255,255,255,.2)}\n'
        '.hero-stat{padding:20px clamp(16px,3vw,44px) 0;text-align:center}\n',
        '.hero h1{font-size:clamp(46px,8.2vw,128px);font-weight:700;letter-spacing:-.045em;line-height:.94;color:#fff;margin:0 0 0 -.04em;padding-bottom:.06em;max-width:none;text-wrap:balance}\n'
        '.hero-sub{margin:0;max-width:40ch;font-size:clamp(17px,1.35vw,21px);line-height:1.5;font-weight:400;color:rgba(255,255,255,.84)}\n'
        '.hero-btns{display:flex;flex-wrap:wrap;gap:12px;justify-content:flex-start;margin:0}\n'
        '.hero-stats,.hero-cred-row,.hero-chips{display:flex;flex-wrap:wrap;justify-content:flex-start;gap:0;margin-top:clamp(16px,3vh,32px);padding-top:0;border-top:1px solid rgba(255,255,255,.2)}\n'
        '.hero-stat{padding:20px clamp(16px,3vw,44px) 20px 0;text-align:left}\n', 'hero h1')
    css = sustituir(css, '.hero-stat+.hero-stat{border-left:1px solid rgba(255,255,255,.2)}',
                         '.hero-stat+.hero-stat{border-left:1px solid rgba(255,255,255,.2);padding-left:clamp(16px,3vw,44px)}', 'hero-stat')
    css = sustituir(css, '.hero-cred-row,.hero-chips{gap:8px;padding-top:24px}', '.hero-cred-row,.hero-chips{gap:8px;padding-top:24px;justify-content:flex-start}', 'cred-row')
    css = sustituir(css, '.hero-media .ground{position:absolute;inset:0;height:auto;background:linear-gradient(180deg,rgba(14,35,45,.58) 0%,rgba(14,35,45,.4) 30%,rgba(14,35,45,.5) 62%,rgba(14,35,45,.84) 100%);pointer-events:none}',
                         '.hero-media .ground{position:absolute;inset:0;height:auto;background:linear-gradient(180deg,rgba(14,35,45,.42) 0%,rgba(14,35,45,.08) 28%,rgba(14,35,45,.3) 52%,rgba(14,35,45,.92) 100%);pointer-events:none}', 'ground')
    css = sustituir(css, '#navcrumb{top:calc(var(--nav-h) + 16px)!important;left:0!important;right:0!important;padding:0 var(--gutter)!important;font-size:11.5px!important;font-weight:700;letter-spacing:.16em!important;text-transform:uppercase;text-align:center;line-height:1.5}',
                         '#navcrumb{top:calc(var(--nav-h) + 16px)!important;left:0!important;right:0!important;padding:0 var(--gutter)!important;font-size:11.5px!important;font-weight:700;letter-spacing:.16em!important;text-transform:uppercase;text-align:left;line-height:1.5;max-width:1360px;margin:0 auto}', 'navcrumb')
    # las páginas legales y la 404 conservan su hero compacto y centrado
    css = sustituir(css, '.hero-kicker+h1{font-size:clamp(32px,4.2vw,58px);max-width:20ch}',
                         '.hero:has(.hero-kicker) .hero-inner,.hero:has(.code) .hero-inner{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;min-height:0}\n'
                         '.hero:has(.hero-kicker){min-height:min(60vh,560px);align-items:center}\n'
                         '.hero:has(.hero-kicker) h1{font-size:clamp(32px,4.2vw,58px);max-width:20ch;margin:0;letter-spacing:-.035em;line-height:1.04}\n'
                         '.hero:has(.hero-kicker) .hero-inner{padding-top:calc(var(--nav-h) + 48px);padding-bottom:clamp(40px,7vh,72px)}', 'hero legal')
    css = sustituir(css, '.hero:has(.code) h1{font-size:clamp(30px,3.8vw,52px);line-height:1.04;max-width:20ch;margin:0 auto}',
                         '.hero:has(.code) h1{font-size:clamp(30px,3.8vw,52px);line-height:1.04;max-width:20ch;margin:0 auto;letter-spacing:-.035em}', '404 h1')

    # ---- FAQ: el acordeón v1 se reemplaza por la conversación (bloque nuevo al final)
    css = sustituir(css, css[css.index('/* preguntas frecuentes */'):css.index('/* cierre de contacto */')], '', 'faq v1')
    # ---- cierre de contacto v1: se reemplaza
    css = sustituir(css, css[css.index('/* cierre de contacto */'):css.index('/* ---------- pie ---------- */')], '', 'contacto v1')
    # ---- historia v1: se reemplaza
    css = sustituir(css, css[css.index('/* historia (bloque bordó con línea de tiempo dorada) */'):css.index('/* equipo */')], '', 'historia v1')
    # ---- medios de pago v1: se reemplaza
    css = sustituir(css, css[css.index('/* medios de pago */'):css.index('/* guía de viaje */')], '', 'fin v1')
    # ---- pie v1: el bloque de marca dentro de la grilla ya no existe
    css = sustituir(css, '.fgrid>div:first-child{grid-column:1/-1;padding-bottom:36px;border-bottom:1px solid var(--line)}\n', '', 'pie brand')
    css = sustituir(css, '.fbot .claim{font-style:italic;color:var(--red)}\n', '', 'pie claim')

    # ================= bloques nuevos (extraídos de la home y adaptados) =================
    btn = home_block(hcss, '/* Buttons */', '/* Reveal */')
    footer = home_block(hcss, '/* Footer */', '/* WhatsApp float */')
    footer = footer.replace('footer{', 'footer.px{').replace('\n.fgrid h4', '\n.fgrid h4')  # mismas reglas que la home
    # (las secciones elegidas de la home —tarjeta de pago, conversación, contacto, historia—
    #  se adaptan abajo a las clases de las subpáginas, con los mismos valores que index.html)

    nuevo = '''
/* ============================================================================
   v2 · bloques sincronizados con la home final (tools/css_v2.py)
   ========================================================================== */

/* botones de la home (disponibles para toda página) */
''' + btn + '''
/* ---------- medios de pago: tarjeta que se inclina (Financiación A de la home) ---------- */
.fin{background:var(--bur);color:#fff;overflow:hidden;padding-top:clamp(80px,11vh,128px);padding-bottom:clamp(80px,11vh,128px)}
.fin .mx{position:relative;display:grid;grid-template-columns:minmax(0,1fr);gap:0;align-items:start;perspective:1400px}
.fin .h2{color:#fff}
.fin .kicker{color:var(--gold)}
.fin p.lead{margin-top:28px;max-width:54ch;color:rgba(255,255,255,.72)}
.fin .mx>a{justify-self:start;margin-top:32px}
@media(max-width:640px){.fin .mx>a{max-width:100%;white-space:normal;text-align:left;line-height:1.25}}
.chips{position:relative;display:grid;gap:clamp(6px,1vw,12px);align-content:end;margin:36px 0 0;aspect-ratio:1.586;max-width:520px;border-radius:clamp(18px,2.4vw,28px);padding:calc(clamp(22px,3vw,40px) + clamp(30px,3.3vw,42px) + 22px) clamp(22px,3vw,40px) clamp(22px,3vw,40px);background:linear-gradient(135deg,#5e1b1f 0%,#3a0f12 55%,#2b0a0c 100%);box-shadow:0 60px 90px -50px rgba(0,0,0,.8),inset 0 1px 0 rgba(255,255,255,.14);transform:rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg));transition:transform .9s var(--ease);will-change:transform;overflow:hidden;touch-action:pan-y}
.chips::before{content:'';position:absolute;inset:-40%;background:radial-gradient(circle at var(--mx,30%) var(--my,20%),rgba(255,255,255,.16),rgba(255,255,255,0) 32%);pointer-events:none}
.chips::after{content:'';position:absolute;top:clamp(22px,3vw,40px);left:clamp(22px,3vw,40px);width:clamp(40px,4.4vw,56px);height:clamp(30px,3.3vw,42px);border-radius:8px;background:linear-gradient(135deg,#f7cf7a,#c98a1c);box-shadow:inset 0 0 0 1px rgba(0,0,0,.25),inset 0 6px 0 -3px rgba(255,255,255,.35)}
.chip{position:relative;z-index:1;display:flex;align-items:center;gap:14px;border:0;border-radius:0;padding:0;font-size:clamp(17px,1.9vw,26px);font-weight:500;letter-spacing:-.02em;line-height:1.15;text-transform:none;color:rgba(255,255,255,.42);transition:color .5s var(--ease),transform .7s var(--ease);cursor:default}
.chip::before{content:'';width:10px;height:10px;border-radius:50%;flex:none;border:1.5px solid rgba(255,255,255,.35);transition:background .4s,border-color .4s,transform .6s var(--ease)}
.chip.on{color:#fff;font-weight:700;transform:translateX(6px)}
.chip.on::before{background:var(--gold);border-color:var(--gold);transform:scale(1.25);box-shadow:0 0 0 5px rgba(242,179,61,.22)}
@media(min-width:1024px){
  /* texto a la izquierda y la tarjeta flotando a la derecha, centrada en el alto del bloque */
  .fin .mx{min-height:440px;align-content:center}
  .fin .mx>.rv{width:calc(50% - clamp(24px,3vw,55px))}
  .fin .mx>a{max-width:calc(50% - clamp(24px,3vw,55px))}
  .fin .mx>.rv>.chips{position:absolute;right:0;top:50%;width:calc(50% - clamp(24px,3vw,55px));max-width:none;margin:0;transform:translateY(-50%) rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg))}
}
@media(prefers-reduced-motion:reduce){.chips{transform:none!important}.chip{color:#fff}.chip::before{background:var(--gold);border-color:var(--gold)}}

/* ---------- preguntas frecuentes: conversación (FAQ H de la home) ---------- */
/* dos estructuras: servicios (.mx > título.rv + .faqwrap) y madres/hijas (.faqwrap > título.rv + .rv > .faq) */
.mx:has(>.faqwrap),.faqwrap:has(>.rv>.faq){display:grid;gap:40px;max-width:none;margin:0}
.mx:has(>.faqwrap)>.rv,.faqwrap:has(>.rv>.faq)>.rv:first-child{margin:0!important;max-width:none!important;text-align:left!important}
.faqwrap:has(>.rv>.faq)>.rv:first-child .h2,.faqwrap:has(>.rv>.faq)>.rv:first-child .kicker{text-align:left!important}
.faqwrap:not(:has(>.rv>.faq)),.faqwrap>.rv:has(>.faq){max-width:640px;margin:0;display:grid;gap:clamp(10px,1.4vh,14px)}
.faq{display:grid;gap:clamp(10px,1.4vh,14px);border:0!important}
.faq.rv{opacity:1;transform:none}
.faq button,.faq .ans{position:relative;max-width:88%;padding:14px 18px;border-radius:18px;opacity:0;transform:translateY(14px) scale(.96);transition:opacity .45s var(--ease),transform .6s var(--ease)}
.faq button{width:auto;justify-self:end;justify-content:flex-start;gap:0;background:var(--red);color:#fff;border-bottom-right-radius:4px;transform-origin:100% 100%;text-align:left;font-size:clamp(16px,1.2vw,18px);font-weight:700;letter-spacing:-.01em;line-height:1.3;cursor:default}
.faq button:hover{color:#fff}
.faq button .pm{display:none}
.faq .ans{justify-self:start;max-height:none!important;overflow:visible;background:#fff;color:var(--ink);border-bottom-left-radius:4px;transform-origin:0 100%;box-shadow:0 0 0 1px var(--line),0 14px 30px -22px rgba(14,35,45,.35)}
.faq .ans p{padding:0;font-size:15.5px;line-height:1.6;color:var(--ink-2);max-width:none}
.faq .ans p strong{color:var(--ink);font-weight:700}
.faq .ans p a{color:var(--red);font-weight:700}
.faq button.in,.faq .ans.in{opacity:1;transform:none}
.faq-typing{justify-self:start;display:flex;gap:5px;padding:0 16px;height:0;overflow:hidden;border-radius:18px 18px 18px 4px;background:rgba(14,35,45,.06);opacity:0;transition:opacity .3s}
.faq-typing.on{opacity:1;height:auto;padding:14px 16px}
.faq-typing i{width:7px;height:7px;border-radius:50%;background:rgba(14,35,45,.45);animation:faqDots 1.2s infinite}
.faq-typing i:nth-child(2){animation-delay:.2s}.faq-typing i:nth-child(3){animation-delay:.4s}
@keyframes faqDots{0%,60%,100%{transform:translateY(0);opacity:.5}30%{transform:translateY(-4px);opacity:1}}
@media(min-width:1024px){
  .mx:has(>.faqwrap),.faqwrap:has(>.rv>.faq){grid-template-columns:5fr 7fr;gap:96px;align-items:start}
  .mx:has(>.faqwrap)>.rv,.faqwrap:has(>.rv>.faq)>.rv:first-child{position:sticky;top:calc(var(--nav-h) + 32px)}
  .faqwrap:not(:has(>.rv>.faq)),.faqwrap>.rv:has(>.faq){max-width:none}
}
@media(prefers-reduced-motion:reduce){.faq button,.faq .ans{opacity:1;transform:none;transition:none}.faq-typing{display:none}}

/* ---------- cierre de contacto: tarjetas con íconos vivos (Contacto H de la home) ---------- */
.contact,.cierre{position:relative;overflow:hidden;background:var(--bur);color:#fff;text-align:left;padding-top:clamp(104px,15vh,184px)}
.cierre::before{content:'';position:absolute;inset:0;background-size:cover;background-repeat:no-repeat;opacity:.16;pointer-events:none}
.contact>.mx,.cierre>.mx{position:relative;z-index:1;max-width:1360px!important;display:grid;gap:40px}
.contact .kicker,.cierre .kicker{color:var(--gold);text-align:left!important}
.contact .h2,.cierre .h2{color:#fff;font-size:clamp(44px,7vw,96px)!important;max-width:none;margin:0;text-align:left!important}
.contact .lead,.cierre .lead{color:rgba(255,255,255,.72)!important;margin:28px 0 0!important;max-width:52ch!important;text-align:left!important;font-size:clamp(17px,1.3vw,20px)}
.contact .mx>.rv[style*="text-align:center"],.cierre .mx>.rv[style*="text-align:center"]{text-align:left!important;margin-top:0!important}
.contact .bigbtn,.cierre .bigbtn{margin-top:0}
.cgrid{display:grid;gap:12px;margin-top:0;border:0;text-align:left}
.ccard{position:relative;padding:clamp(22px,2.4vw,32px);border:0;border-radius:var(--r-lg);background:rgba(255,255,255,.05);box-shadow:inset 0 0 0 1px rgba(255,255,255,.1);overflow:hidden}
.ccard+.ccard{border:0}
.ccard svg{position:relative;z-index:1;display:block;width:42px;height:42px;padding:12px;border-radius:50%;color:var(--gold);box-shadow:inset 0 0 0 1px rgba(242,179,61,.5);margin:0 0 18px;overflow:visible}
.ccard b{display:block;font-size:12px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--gold)}
.ccard p{margin-top:14px;font-size:clamp(22px,1.9vw,30px);font-weight:500;letter-spacing:-.03em;line-height:1.12;color:#fff}
.ccard p small,.ccard p span{display:block;margin-top:10px;font-size:15px;font-weight:400;letter-spacing:0;line-height:1.5;color:rgba(255,255,255,.6)}
/* el local: el pin cae y rebota, y un radar late */
.ccard.ic-pin{--w:1}
.contact.in .ccard.ic-pin svg,.cierre.in .ccard.ic-pin svg{animation:ctHdrop 1.1s cubic-bezier(.2,1.4,.3,1) .2s both}
.contact.in .ccard.ic-pin svg::after{content:none}
.ccard.ic-pin i.radar{position:absolute;left:clamp(22px,2.4vw,32px);top:clamp(22px,2.4vw,32px);width:42px;height:42px;border-radius:50%;border:1.5px solid rgba(242,179,61,.7);opacity:0;pointer-events:none}
.contact.in .ccard.ic-pin i.radar,.cierre.in .ccard.ic-pin i.radar{animation:ctHradar 2.4s ease-out 1s infinite}
@keyframes ctHdrop{0%{transform:translateY(-40px);opacity:0}60%{transform:translateY(4px);opacity:1}80%{transform:translateY(-2px)}100%{transform:none}}
@keyframes ctHradar{0%{transform:scale(1);opacity:.9}100%{transform:scale(2.6);opacity:0}}
/* WhatsApp: el ícono vibra como una llamada entrante */
.contact.in .ccard.ic-wa svg,.cierre.in .ccard.ic-wa svg{animation:ctHring 3s ease-in-out 1.2s infinite}
@keyframes ctHring{0%,70%,100%{transform:rotate(0)}74%{transform:rotate(-12deg)}78%{transform:rotate(10deg)}82%{transform:rotate(-8deg)}86%{transform:rotate(6deg)}90%{transform:rotate(0)}}
/* horarios: la aguja del reloj gira */
.ccard.ic-clock svg path{transform-origin:12px 12px}
.contact.in .ccard.ic-clock svg path,.cierre.in .ccard.ic-clock svg path{animation:ctHclock 8s linear infinite}
@keyframes ctHclock{to{transform:rotate(360deg)}}
.soc-row{grid-column:1/-1;margin-top:0;padding-top:0;border-top:0}
.soc-label{display:none}
.soc-icons{display:grid;grid-template-columns:1fr;gap:0;border-top:1px solid rgba(255,255,255,.12);border-bottom:1px solid rgba(255,255,255,.12)}
.soc-link{display:flex;align-items:center;gap:14px;padding:20px 0;border-radius:0;box-shadow:none;background:none;color:#fff;transition:color .3s}
.soc-link+.soc-link{border-top:1px solid rgba(255,255,255,.12)}
.soc-link svg{width:42px;height:42px;padding:12px;border-radius:50%;box-shadow:inset 0 0 0 1px rgba(255,255,255,.22);transition:color .3s,box-shadow .3s}
.soc-link span{font-size:19px;font-weight:500;letter-spacing:-.02em}
.soc-link:hover{background:none;transform:none;color:#fff}
.soc-link:hover svg{color:var(--gold);box-shadow:inset 0 0 0 1px rgba(242,179,61,.6)}
.contact .contact-btns{justify-content:flex-start;margin-top:0}
@media(min-width:900px){
  .soc-icons{grid-template-columns:repeat(3,1fr)}
  .soc-link{padding:26px 40px}
  .soc-link:first-child{padding-left:0}.soc-link:last-child{padding-right:0}
  .soc-link+.soc-link{border-top:0;border-left:1px solid rgba(255,255,255,.12)}
}
@media(min-width:1024px){
  .contact,.cierre{min-height:100vh;min-height:100svh;display:flex;align-items:center;padding-top:calc(var(--nav-h) + clamp(12px,2.6vh,44px));padding-bottom:clamp(16px,3.4vh,56px)}
  .contact>.mx,.cierre>.mx{width:100%;grid-template-columns:1.15fr .85fr;column-gap:clamp(48px,6vw,110px);row-gap:40px;align-items:center}
  .contact>.mx>.rv:first-child,.cierre>.mx>.rv:first-child{grid-column:1;grid-row:1;align-self:end}
  .contact>.mx>.rv:nth-child(2),.cierre>.mx>.rv:nth-child(2){grid-column:1;grid-row:2;align-self:start}
  .contact>.mx>.cgrid,.cierre>.mx>.cgrid{grid-column:2;grid-row:1/span 2}
  .contact .h2,.cierre .h2{font-size:clamp(44px,min(5.2vw,10vh),96px)}
  .ccard{padding:clamp(18px,2.6vh,32px)}
  .ccard p{font-size:clamp(20px,2.8vh,30px)}
}
@media(prefers-reduced-motion:reduce){.contact.in .ccard svg,.cierre.in .ccard svg,.ccard svg path{animation:none!important}.ccard i.radar{display:none}}

/* ---------- historia: la línea dorada se enciende al pasar (Historia A de la home) ---------- */
.hist-section{background:var(--bur);color:#fff;padding-top:clamp(88px,12vh,152px);padding-bottom:clamp(88px,12vh,152px)}
.hist-section .h2{color:#fff}
.hist-section .kicker{color:var(--gold)}
.hist-section>.mx{display:grid;gap:64px}
.hist-timeline{position:relative;max-width:none;margin:0;padding-left:40px}
.hist-timeline::before{content:'';position:absolute;left:0;top:8px;bottom:0;width:1px;background:rgba(242,179,61,.18)}
.hist-timeline::after{content:'';position:absolute;left:0;top:8px;bottom:0;width:1px;background:var(--gold);transform-origin:top;transform:scaleY(var(--k,0));transition:transform 1.4s var(--ease)}
.hist-block{position:relative;display:grid;gap:14px;padding:0 0 clamp(56px,9vh,96px);border:0;opacity:.34;transition:opacity .9s var(--ease)}
.hist-block:last-child{padding-bottom:0}
.hist-block::before{content:'';position:absolute;left:-44px;top:14px;width:9px;height:9px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 6px rgba(242,179,61,.14);transform:scale(.6);transition:transform .8s var(--ease),box-shadow .8s var(--ease)}
.hist-block.on{opacity:1}
.hist-block.on::before{transform:scale(1);box-shadow:0 0 0 10px rgba(242,179,61,.18)}
.hist-year{width:auto;text-align:left;padding:0}
.hist-year b{display:block;font-size:clamp(36px,4.6vw,72px);font-weight:300;letter-spacing:-.04em;line-height:1;color:var(--gold);transform-origin:left bottom;transform:scale(.72);transition:transform 1s var(--ease)}
.hist-block.on .hist-year b{transform:none}
.hist-year span{display:block;margin-top:12px;font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.6)}
.hist-sep{display:none}
.hist-text{padding:0}
.hist-text h3{font-size:clamp(21px,2vw,28px);font-weight:700;letter-spacing:-.025em;line-height:1.15;color:#fff;margin-bottom:14px}
.hist-text p{font-size:17px;line-height:1.75;color:rgba(255,255,255,.72);margin-bottom:14px;max-width:58ch}
.hist-text p strong{color:#fff;font-weight:700}
.hist-text p[style*="italic"]{font-size:clamp(19px,1.5vw,23px);line-height:1.45;margin-top:22px!important;color:var(--gold)}
@media(min-width:1024px){
  .hist-section>.mx{grid-template-columns:5fr 7fr;gap:96px;align-items:start}
  .hist-section>.mx>.rv:first-child{position:sticky;top:calc(var(--nav-h) + 32px)}
}
@media(prefers-reduced-motion:reduce){.hist-block{opacity:1}.hist-year b{transform:none}.hist-timeline::after{transform:scaleY(1)}}

/* ---------- pie: logo + claim arriba, como la home ---------- */
''' + footer + '''
.fgrid .fdest .cols,.fgrid .fdest>div[style*="grid"]{display:grid;grid-template-columns:1fr 1fr;gap:0 24px}
.fbot a{color:var(--ink-2)!important;opacity:1!important}
'''
    # el bloque nuevo va antes del apagado de animaciones, que sigue siendo lo último
    marca = '/* ---------- sin animaciones si el usuario lo pide ---------- */'
    css = css.replace(marca, nuevo + '\n' + marca, 1)
    css = sustituir(css, '  .rv,.fade,.navlinks-mobile a,.dest-card .cta{opacity:1!important;transform:none!important}',
                         '  .rv,.fade,.navlinks-mobile a,.dest-card .cta,.hero h1 .ln>span,.fin .mx>.rv>*{opacity:1!important;transform:none!important}', 'reduced')
    (ROOT / 'assets/design.css').write_text(css, encoding='utf-8', newline='\n')
    print('assets/design.css v2 escrito:', len(css) // 1024, 'KB')

if __name__ == '__main__':
    main()
