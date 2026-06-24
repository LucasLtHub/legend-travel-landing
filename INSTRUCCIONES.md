# Legend Travel — Cómo aplicar el SEO/GEO al HTML

Tenés 4 archivos en este zip:
- `head-block.html`   → pegar en el <head>
- `schema-block.html` → pegar antes de </body>
- `robots.txt` `llms.txt` `sitemap.xml` → subir a la raíz del sitio

Más 3 ediciones puntuales dentro del HTML (abajo).

---

## PASO 1 — Pegá el bloque del <head>
Abrí tu HTML. Buscá la línea `<title>Legend Travel — Tu viaje, tu historia</title>`.
Justo DEBAJO, pegá todo el contenido de `head-block.html`.

## PASO 2 — GTM noscript (apenas abre el body)
Buscá `<body>` y pegá JUSTO DEBAJO:

<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXXX"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>

## PASO 3 — Pegá el schema
Buscá `</body>` (al final). Justo ANTES, pegá todo el contenido de `schema-block.html`.

## PASO 4 — Arreglá el H1 (importante para SEO)
PROBLEMA: tu H1 está oculto y el título es el logo en imagen. Google necesita un H1 textual.

4a) En el CSS, BORRÁ esta línea (está sola, después de la animación del heading):
    .hero h1{display:none}

4b) Reemplazá el H1 oculto por uno accesible. Buscá:
    <h1 id="heading" aria-label="Tu viaje, tu historia."></h1>

    Y dejá el bloque del hero así (el H1 envuelve al logo, sigue viéndose igual):

    <h1 class="hero-h1-visually">
      <img src="logo-wordmark.png" alt="Legend Travel — agencia de viajes en Martínez, Buenos Aires">
      <span class="sr-only">Legend Travel — Tu viaje, tu historia. Agencia de viajes con más de 35 años de trayectoria.</span>
    </h1>

    (Quitá el <div class="hero-logo-main"> que tenía el logo, ya no hace falta;
     o más simple: dejá el logo donde está y solo agregá el <span class="sr-only">
     con el texto dentro de un <h1>.)

4c) Agregá esta clase al CSS (oculta visualmente pero Google y lectores la leen):
    .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
    overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}

## PASO 5 — Subí los 3 archivos a la raíz
robots.txt, llms.txt y sitemap.xml van en la carpeta raíz del sitio,
accesibles como www.legendtravel.com.ar/robots.txt etc.

## PASO 6 — Crear las cuentas (gratis) y pegar verificaciones
- Google Search Console → verificar dominio → enviar sitemap.xml
- Bing Webmaster Tools → verificar (importante: Copilot usa Bing)
- Google Tag Manager → crear contenedor, copiar el ID GTM-XXXXXXX y
  reemplazarlo en head-block (2 lugares) y en el noscript
- Dentro de GTM: agregar GA4 + un evento "clic_whatsapp" que dispare
  en todos los <a href="wa.me...">. Ese evento es tu conversión.

## DATOS QUE FALTAN (los dejé como COMPLETAR)
- og-image.jpg → subir una imagen 1200x630 (puede ser el hero con el logo)
- CUIT / razón social → si querés sumarlo al schema, avisame
- IDs de verificación y de GTM → salen al crear cada cuenta
