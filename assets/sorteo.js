/* Legend Travel — popup del sorteo "Legend Travel × Río de Janeiro" (campaña temporal).
   Se carga SOLO desde la home (index.html). Todo vive acá: CSS, HTML y disparadores.
   Aparece a los 8 s de navegación o al 40 % de scroll (lo que ocurra primero), una
   sola vez por visitante. No aparece si: ya se vio (lt_sorteo_visto), el visitante
   viene de /sorteo/, ya pasó el cierre del sorteo (27/10/2026 20:00, hora Argentina)
   o SORTEO_ACTIVO está en false. Se cierra con la X, Escape o clic afuera. */
(function () {
  'use strict';
  var SORTEO_ACTIVO = true;                              /* ← apagar a mano: false */
  var CIERRE = Date.UTC(2026, 9, 27, 23, 0, 0);          /* 27/10/2026 20:00 en Argentina (UTC-3) */
  var URL_SORTEO = 'sorteo/';
  var FOTO = 'assets/img/sorteo-rio-sm.jpg';
  var CLAVE = 'lt_sorteo_visto';

  if (!SORTEO_ACTIVO) return;
  if (Date.now() > CIERRE) return;                       /* después del cierre el popup muere solo */
  if (/\/sorteo(\/|$)/i.test(document.referrer || '')) return;
  function leer() { try { return localStorage.getItem(CLAVE); } catch (e) { return null; } }
  function marcar() { try { localStorage.setItem(CLAVE, '1'); } catch (e) {} }
  if (leer()) return;

  var d = document, reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function gtm(ev) { try { (window.dataLayer = window.dataLayer || []).push({ event: ev }); } catch (e) {} }

  /* la capa es fija: no mueve nada del documento (sin layout shift) */
  var css = '.srp{position:fixed;inset:0;z-index:80;display:flex;align-items:flex-end;justify-content:center;background:rgba(14,35,45,.55);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);opacity:0;pointer-events:none;transition:opacity .5s cubic-bezier(.16,1,.3,1)}'
    + '.srp.on{opacity:1;pointer-events:auto}'
    + '.srp-box{position:relative;outline:0;width:100%;max-height:80vh;max-height:80svh;overflow:auto;background:#F8F8F8;color:#0E232D;border-radius:24px 24px 0 0;transform:translateY(40px);transition:transform .7s cubic-bezier(.16,1,.3,1);font-family:Satoshi,system-ui,sans-serif;-webkit-font-smoothing:antialiased;box-shadow:0 40px 80px -30px rgba(14,35,45,.6)}'
    + '.srp.on .srp-box{transform:none}'
    + '.srp-img{position:relative;height:min(34vh,200px);background:#491417 url(' + FOTO + ') center/cover no-repeat}'
    + '.srp-img::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,35,45,.1) 0%,rgba(14,35,45,0) 40%,rgba(73,20,23,.55) 100%)}'
    + '.srp-tag{position:absolute;left:22px;bottom:16px;z-index:1;display:flex;align-items:center;gap:10px;font-size:11px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#F8F8F8}'
    + '.srp-tag i{width:7px;height:7px;border-radius:50%;background:#F2B33D;box-shadow:0 0 0 4px rgba(242,179,61,.25)}'
    + '.srp-x{position:absolute;right:14px;top:14px;z-index:2;width:42px;height:42px;border-radius:50%;background:rgba(248,248,248,.92);color:#0E232D;border:0;display:grid;place-items:center;cursor:pointer;box-shadow:0 6px 20px -8px rgba(14,35,45,.4);transition:background .3s,color .3s,transform .5s cubic-bezier(.16,1,.3,1)}'
    + '.srp-x:hover{background:#AC0A10;color:#fff;transform:rotate(90deg)}.srp-x:focus-visible{outline:2px solid #F2B33D;outline-offset:2px}'
    + '.srp-x svg{width:16px;height:16px}'
    + '.srp-body{position:relative;padding:22px 24px 28px}'
    + '.srp-k{margin:0 0 12px;font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#AC0A10}'
    + '.srp-h{font-size:clamp(28px,7vw,38px);font-weight:700;letter-spacing:-.035em;line-height:1.02;margin:0;color:#0E232D;padding-bottom:.06em}'
    + '.srp-h em{font-style:italic;font-weight:400;color:#AC0A10}'
    + '.srp-p{margin:12px 0 0;font-size:15px;line-height:1.55;color:rgba(14,35,45,.64);max-width:34ch}'
    + '.srp-a{display:inline-flex;align-items:center;gap:14px;margin-top:22px;padding:7px 7px 7px 26px;border-radius:999px;background:#AC0A10;color:#fff;font-weight:700;font-size:15px;line-height:1;white-space:nowrap;text-decoration:none;transition:background .45s cubic-bezier(.16,1,.3,1)}'
    + '.srp-a:hover{background:#491417}.srp-a:focus-visible{outline:2px solid #F2B33D;outline-offset:3px}'
    + '.srp-a i{width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,.16);display:grid;place-items:center;font-style:normal;transition:transform .5s cubic-bezier(.16,1,.3,1)}'
    + '.srp-a:hover i{transform:translate(2px,-2px)}'
    + '.srp-a svg{width:16px;height:16px}'
    + '.srp-f{margin:18px 0 0;font-size:12px;color:rgba(14,35,45,.44)}'
    + '@media(min-width:720px){.srp{align-items:center;padding:24px}.srp-box{width:min(90vw,820px);display:grid;grid-template-columns:5fr 6fr;border-radius:24px;transform:translateY(24px) scale(.97)}.srp-img{height:auto;min-height:360px}.srp-img::after{background:linear-gradient(180deg,rgba(14,35,45,.08) 0%,rgba(14,35,45,0) 40%,rgba(73,20,23,.6) 100%)}.srp-body{padding:48px 48px 44px 44px;display:flex;flex-direction:column;justify-content:center}.srp-h{font-size:clamp(34px,3.6vw,48px)}.srp-x{right:18px;top:18px}}'
    + '@media(prefers-reduced-motion:reduce){.srp,.srp-box,.srp-x,.srp-a i{transition:none}}';

  function abrir() {
    if (abrir.hecho) return; abrir.hecho = true;
    marcar();
    var st = d.createElement('style'); st.textContent = css; d.head.appendChild(st);
    var root = d.createElement('div'); root.className = 'srp'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-labelledby', 'srp-h');
    root.innerHTML = '<div class="srp-box">'
      + '<div class="srp-img" aria-hidden="true"><span class="srp-tag"><i></i>Sorteo · hasta el 27/10</span></div>'
      + '<button type="button" class="srp-x" aria-label="Cerrar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>'
      + '<div class="srp-body"><p class="srp-k">Legend Travel × Río de Janeiro</p><h2 class="srp-h" id="srp-h">Ganate 3 noches <em>en Copacabana.</em></h2>'
      + '<p class="srp-p">Para 2 personas, con desayuno. Participás en un minuto.</p>'
      + '<a class="srp-a" href="' + URL_SORTEO + '">Quiero participar <i><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></i></a>'
      + '<p class="srp-f">Participación gratuita, sin obligación de compra.</p></div></div>';
    d.body.appendChild(root);
    var ultimo = d.activeElement, foco = root.querySelectorAll('button, a');
    function cerrar() { marcar(); root.classList.remove('on'); d.removeEventListener('keydown', tecla); setTimeout(function () { root.remove(); }, reduce ? 0 : 450); if (ultimo && ultimo.focus) ultimo.focus(); }
    function tecla(e) {
      if (e.key === 'Escape') return cerrar();
      if (e.key !== 'Tab') return;                       /* el foco queda dentro del popup */
      var a = foco[0], z = foco[foco.length - 1];
      if (e.shiftKey && d.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && d.activeElement === z) { e.preventDefault(); a.focus(); }
    }
    root.querySelector('.srp-x').addEventListener('click', cerrar);
    root.addEventListener('click', function (e) { if (e.target === root) cerrar(); });
    root.querySelector('.srp-a').addEventListener('click', function () { marcar(); gtm('sorteo_popup_click'); });
    d.addEventListener('keydown', tecla);
    requestAnimationFrame(function () { requestAnimationFrame(function () { root.classList.add('on'); root.querySelector('.srp-box').setAttribute('tabindex', '-1'); root.querySelector('.srp-box').focus({ preventScroll: true }); }); });
    gtm('sorteo_popup_visto');
  }
  var timer = setTimeout(abrir, 8000);
  function alScroll() {
    var h = d.documentElement.scrollHeight - innerHeight;
    if (h > 0 && scrollY / h >= 0.4) { clearTimeout(timer); removeEventListener('scroll', alScroll); abrir(); }
  }
  addEventListener('scroll', alScroll, { passive: true });
})();
