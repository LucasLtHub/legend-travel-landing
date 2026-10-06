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
  var css = '.srp{position:fixed;inset:0;z-index:80;display:flex;align-items:flex-end;justify-content:center;background:rgba(14,35,45,.6);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);opacity:0;pointer-events:none;transition:opacity .45s cubic-bezier(.16,1,.3,1)}'
    + '.srp.on{opacity:1;pointer-events:auto}'
    + '.srp-box{position:relative;width:100%;max-height:80vh;max-height:80svh;overflow:auto;background:#0E232D;color:#F8F8F8;border-radius:24px 24px 0 0;transform:translateY(40px);transition:transform .6s cubic-bezier(.16,1,.3,1);font-family:Satoshi,system-ui,sans-serif;-webkit-font-smoothing:antialiased;box-shadow:0 -20px 60px -20px rgba(0,0,0,.5)}'
    + '.srp.on .srp-box{transform:none}'
    + '.srp-img{position:relative;height:min(38vh,220px);background:#0E232D url(' + FOTO + ') center/cover no-repeat}'
    + '.srp-img::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,35,45,0) 35%,#0E232D 100%)}'
    + '.srp-tag{position:absolute;left:20px;top:18px;z-index:1;display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;background:#F2B33D;color:#0E232D;font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}'
    + '.srp-x{position:absolute;right:14px;top:14px;z-index:2;width:44px;height:44px;border-radius:50%;background:rgba(14,35,45,.6);color:#fff;border:0;display:grid;place-items:center;cursor:pointer;transition:background .3s,transform .5s cubic-bezier(.16,1,.3,1)}'
    + '.srp-x:hover,.srp-x:focus-visible{background:#F2B33D;color:#0E232D;transform:rotate(90deg);outline:0}'
    + '.srp-x svg{width:18px;height:18px}'
    + '.srp-body{position:relative;padding:4px 24px 26px;margin-top:-24px}'
    + '.srp-k{margin:0 0 8px;font-size:11px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#F2B33D}'
    + '.srp-h{font-size:clamp(24px,6vw,34px);font-weight:700;letter-spacing:-.035em;line-height:1.04;margin:0;color:#F8F8F8}'
    + '.srp-h em{font-style:italic;font-weight:400;color:#F2B33D}'
    + '.srp-p{margin:10px 0 0;font-size:15px;line-height:1.5;color:rgba(248,248,248,.74)}'
    + '.srp-a{display:inline-flex;align-items:center;gap:14px;margin-top:18px;padding:7px 7px 7px 24px;border-radius:999px;background:#F2B33D;color:#0E232D;font-weight:700;font-size:15px;line-height:1;text-decoration:none;transition:background .45s cubic-bezier(.16,1,.3,1),color .3s}'
    + '.srp-a:hover{background:#F8F8F8;color:#0E232D}'
    + '.srp-a:focus-visible{outline:2px solid #F8F8F8;outline-offset:3px}'
    + '.srp-a i{width:38px;height:38px;border-radius:50%;background:rgba(14,35,45,.14);display:grid;place-items:center;font-style:normal}'
    + '.srp-a svg{width:16px;height:16px}'
    + '@media(min-width:720px){.srp{align-items:center;padding:24px}.srp-box{width:min(92vw,760px);display:grid;grid-template-columns:1fr 1.05fr;border-radius:24px;transform:translateY(24px) scale(.97)}.srp-img{height:auto;min-height:100%}.srp-img::after{background:linear-gradient(90deg,rgba(14,35,45,0) 50%,#0E232D 100%)}.srp-body{padding:40px 40px 36px 4px;margin:0;display:flex;flex-direction:column;justify-content:center}.srp-h{font-size:clamp(28px,3.2vw,40px)}}'
    + '@media(prefers-reduced-motion:reduce){.srp,.srp-box,.srp-x{transition:none}}';

  function abrir() {
    if (abrir.hecho) return; abrir.hecho = true;
    marcar();
    var st = d.createElement('style'); st.textContent = css; d.head.appendChild(st);
    var root = d.createElement('div'); root.className = 'srp'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-labelledby', 'srp-h');
    root.innerHTML = '<div class="srp-box">'
      + '<div class="srp-img" aria-hidden="true"><span class="srp-tag">Sorteo · hasta el 27/10</span></div>'
      + '<button type="button" class="srp-x" aria-label="Cerrar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>'
      + '<div class="srp-body"><p class="srp-k">Legend Travel × Río de Janeiro</p><h2 class="srp-h" id="srp-h">Ganate 3 noches <em>en Copacabana</em></h2>'
      + '<p class="srp-p">Para 2 personas, con desayuno. Participás en 1 minuto.</p>'
      + '<a class="srp-a" href="' + URL_SORTEO + '">Quiero participar <i><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></i></a></div></div>';
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
    requestAnimationFrame(function () { requestAnimationFrame(function () { root.classList.add('on'); root.querySelector('.srp-a').focus({ preventScroll: true }); }); });
    gtm('sorteo_popup_visto');
  }
  var timer = setTimeout(abrir, 8000);
  function alScroll() {
    var h = d.documentElement.scrollHeight - innerHeight;
    if (h > 0 && scrollY / h >= 0.4) { clearTimeout(timer); removeEventListener('scroll', alScroll); abrir(); }
  }
  addEventListener('scroll', alScroll, { passive: true });
})();
