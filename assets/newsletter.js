/* Legend Travel — banner de suscripción al newsletter (Doppler, lista "Suscriptores Web").
   Se carga en todas las páginas con un <script> antes de </body>. Todo vive acá: CSS, HTML y envío.
   Se monta arriba del pie (dentro del primer contenedor de cada <footer>) y, en la home, al final
   de cada artículo de "Guías y artículos" (el modal llama a window.ltNewsletter). NO va en el hero.
   No aparece si: NEWSLETTER_ACTIVO está en false, todavía no es INICIO (para no competir con el
   popup del sorteo) o el visitante ya se suscribió desde este navegador (lt_newsletter_ok).
   Para verlo antes de INICIO: agregar ?newsletter=preview a la URL.
   El envío va a newsletter/suscribir.php (honeypot + tiempo medido con performance.now()). */
(function () {
  'use strict';
  var NEWSLETTER_ACTIVO = true;                          /* ← apagar a mano: false */
  var INICIO = Date.UTC(2026, 9, 28, 3, 0, 0);           /* 28/10/2026 00:00 en Argentina (UTC-3) */
  var URL_POST = 'newsletter/suscribir.php';
  var URL_PRIVACIDAD = 'politica-de-privacidad/';
  var CLAVE = 'lt_newsletter_ok';
  var OK_MSG = '¡Listo! Te vamos a escribir con las mejores promos.';

  var preview = /[?&]newsletter=preview(&|$)/.test(location.search);
  function leer() { try { return localStorage.getItem(CLAVE); } catch (e) { return null; } }
  function marcar() { try { localStorage.setItem(CLAVE, '1'); } catch (e) {} }
  if (!preview && (!NEWSLETTER_ACTIVO || Date.now() < INICIO || leer())) return;

  var d = document, n = 0;
  function ahora() { return (window.performance && performance.now) ? performance.now() : Date.now(); }
  function gtm(ev) { try { (window.dataLayer = window.dataLayer || []).push({ event: ev }); } catch (e) {} }

  var css = '.nlb{position:relative;display:grid;gap:24px;margin:0 0 64px;padding:clamp(26px,3.2vw,44px);border-radius:24px;background:#0E232D;color:#F8F8F8;font-family:inherit;overflow:hidden}'
    + '.nlb::before{content:"";position:absolute;right:-90px;top:-90px;width:240px;height:240px;border-radius:50%;background:radial-gradient(circle,rgba(242,179,61,.18),rgba(242,179,61,0) 70%);pointer-events:none}'
    + '.nlb-h{position:relative;margin:0;font-size:clamp(22px,2.3vw,30px);font-weight:700;letter-spacing:-.025em;line-height:1.15;color:#F8F8F8;max-width:22ch}'
    + '.nlb-h em{font-style:italic;font-weight:400;color:#F2B33D}'
    + '.nlb-f{position:relative;margin:0}'
    + '.nlb-row{display:flex;flex-wrap:wrap;gap:10px}'
    + '.nlb-in{flex:1 1 220px;min-width:0;height:52px;padding:0 22px;border-radius:999px;border:1px solid rgba(248,248,248,.22);background:rgba(248,248,248,.08);color:#F8F8F8;font:inherit;font-size:16px;outline:0;transition:border-color .3s,background .3s}'
    + '.nlb-in::placeholder{color:rgba(248,248,248,.5)}'
    + '.nlb-in:focus{border-color:#F2B33D;background:rgba(248,248,248,.12)}'
    + '.nlb-in[aria-invalid="true"]{border-color:#F28B8F}'
    + '.nlb-bt{flex:none;height:52px;padding:0 28px;border:0;border-radius:999px;background:#AC0A10;color:#fff;font:inherit;font-size:15px;font-weight:700;cursor:pointer;transition:background .4s cubic-bezier(.16,1,.3,1),opacity .3s}'
    + '.nlb-bt:hover{background:#C8141B}.nlb-bt:focus-visible{outline:2px solid #F2B33D;outline-offset:3px}'
    + '.nlb-bt[disabled]{opacity:.6;cursor:wait}'
    + '.nlb-msg{margin:10px 0 0;min-height:1.4em;font-size:14px;line-height:1.4;color:#F28B8F}'
    + '.nlb-msg:empty{display:none}'
    + '.nlb-legal{margin:12px 0 0;font-size:12.5px;line-height:1.5;color:rgba(248,248,248,.55)}'
    + '.nlb-legal a{color:rgba(248,248,248,.8);text-decoration:underline;text-underline-offset:2px}'
    + '.nlb-legal a:hover{color:#F2B33D}'
    + '.nlb-ok{margin:0;font-size:clamp(17px,1.5vw,20px);font-weight:700;line-height:1.35;color:#F2B33D}'
    + '.nlb-hp{position:absolute!important;left:-9999px!important;width:1px;height:1px;opacity:0}'
    + '.nlb-sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}'
    + '.nlb.nlb-art{margin:36px 0 0}'
    + '@media(max-width:519px){.nlb-bt{flex:1 1 100%}}'
    + '@media(min-width:960px){.nlb{grid-template-columns:1fr minmax(380px,1fr);align-items:center;gap:56px}.nlb.nlb-art{grid-template-columns:1fr;gap:24px}}'
    + '@media(prefers-reduced-motion:reduce){.nlb-in,.nlb-bt{transition:none}}';
  var st = d.createElement('style'); st.textContent = css; d.head.appendChild(st);

  function banner(enArticulo) {
    var i = ++n, el = d.createElement('section');
    el.className = 'nlb' + (enArticulo ? ' nlb-art' : '');
    el.setAttribute('aria-labelledby', 'nlb-h' + i);
    el.innerHTML = '<h2 class="nlb-h" id="nlb-h' + i + '">Recibí antes que nadie las promociones de <em>Europa y Caribe.</em></h2>'
      + '<form class="nlb-f" novalidate action="' + URL_POST + '" method="post">'
      + '<div class="nlb-row">'
      + '<label class="nlb-sr" for="nlb-e' + i + '">Tu email</label>'
      + '<input class="nlb-in" id="nlb-e' + i + '" type="email" name="email" required maxlength="100" autocomplete="email" inputmode="email" placeholder="Tu email">'
      + '<input class="nlb-hp" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">'
      + '<button class="nlb-bt" type="submit">Quiero recibirlas</button>'
      + '</div>'
      + '<p class="nlb-msg" role="alert"></p>'
      + '<p class="nlb-legal">Podés darte de baja cuando quieras. <a href="' + URL_PRIVACIDAD + '">Ver Política de privacidad</a></p>'
      + '</form>';
    var t0 = ahora(), f = el.querySelector('form'), inp = f.querySelector('.nlb-in'),
        bt = f.querySelector('.nlb-bt'), msg = f.querySelector('.nlb-msg');
    function error(texto) { msg.textContent = texto; inp.setAttribute('aria-invalid', 'true'); inp.focus(); }
    inp.addEventListener('input', function () { inp.removeAttribute('aria-invalid'); msg.textContent = ''; });
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      if (bt.disabled) return;
      var email = inp.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return error('Revisá el email.');
      var datos = new FormData(f);
      datos.set('email', email);
      datos.set('elapsed', String(Math.round(ahora() - t0)));   /* tiempo desde que apareció el banner, nunca la hora del reloj */
      bt.disabled = true; msg.textContent = '';
      fetch(URL_POST, { method: 'POST', body: datos, credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j || !j.ok) { bt.disabled = false; return error((j && j.msg) || 'No pudimos suscribirte. Probá de nuevo en un rato.'); }
          marcar();
          gtm('suscripcion_newsletter');
          f.innerHTML = '<p class="nlb-ok" role="status">' + OK_MSG + '</p>';
        })
        .catch(function () { bt.disabled = false; error('No pudimos conectarnos. Revisá tu conexión y probá de nuevo.'); });
    });
    return el;
  }

  /* pie de cada página: arriba de todo, dentro del contenedor (.wrap / .mx) para heredar el ancho */
  Array.prototype.forEach.call(d.querySelectorAll('footer'), function (ft) {
    var cont = ft.firstElementChild || ft;
    cont.insertBefore(banner(false), cont.firstChild);
  });

  /* artículos de "Guías y artículos": el modal de la home lo llama al abrir cada uno */
  window.ltNewsletter = function (destino) {
    if (destino && !leer()) destino.appendChild(banner(true));
  };
})();
