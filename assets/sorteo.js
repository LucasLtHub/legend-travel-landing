/* Legend Travel — popup del sorteo de Río de Janeiro (campaña temporal).
   TODO el popup vive acá: CSS, HTML y disparadores. Para apagarlo en todo el
   sitio basta poner SORTEO_ACTIVO = false (o sacar la línea que carga este
   archivo). Reglas: aparece a los 8 s o al 40 % de scroll (lo que pase
   primero), una sola vez por visitante, nunca en /sorteo/ ni en las legales,
   nunca si ya participó. Se cierra con la X, Escape o clic afuera. */
(function () {
  'use strict';
  var SORTEO_ACTIVO = true;                       /* ← el 27/10 a las 20 h: false */
  var URL_SORTEO = 'sorteo/';
  var FOTO = 'assets/img/sorteo-rio-sm.jpg';
  var CLAVE_VISTO = 'lt_sorteo_visto', CLAVE_PARTICIPO = 'lt_sorteo_participo';

  if (!SORTEO_ACTIVO) return;
  var path = (location.pathname || '').toLowerCase();
  if (/\/sorteo(\/|$)|politica-de-privacidad|terminos-y-condiciones/.test(path)) return;
  function ls(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  if (ls(CLAVE_VISTO) || ls(CLAVE_PARTICIPO)) return;
  var d = document, reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function gtm(ev) { try { (window.dataLayer = window.dataLayer || []).push({ event: ev }); } catch (e) {} }

  var css = '.srp{position:fixed;inset:0;z-index:80;display:flex;align-items:flex-end;justify-content:center;background:rgba(14,35,45,.62);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);opacity:0;pointer-events:none;transition:opacity .45s cubic-bezier(.16,1,.3,1)}'
    + '.srp.on{opacity:1;pointer-events:auto}'
    + '.srp-box{position:relative;width:100%;max-height:88vh;overflow:auto;background:#491417;color:#fff;border-radius:24px 24px 0 0;transform:translateY(40px);transition:transform .6s cubic-bezier(.16,1,.3,1);font-family:Satoshi,system-ui,sans-serif;-webkit-font-smoothing:antialiased}'
    + '.srp.on .srp-box{transform:none}'
    + '.srp-img{position:relative;aspect-ratio:16/9;background:#2b0a0c url(' + FOTO + ') center/cover no-repeat}'
    + '.srp-img::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(73,20,23,0) 40%,#491417 100%)}'
    + '.srp-tag{position:absolute;left:20px;top:18px;z-index:1;display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;background:#F2B33D;color:#491417;font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}'
    + '.srp-x{position:absolute;right:14px;top:14px;z-index:2;width:42px;height:42px;border-radius:50%;background:rgba(14,35,45,.55);color:#fff;border:0;display:grid;place-items:center;cursor:pointer;transition:background .3s,transform .5s cubic-bezier(.16,1,.3,1)}'
    + '.srp-x:hover{background:#AC0A10;transform:rotate(90deg)}'
    + '.srp-x svg{width:18px;height:18px}'
    + '.srp-body{position:relative;padding:4px 24px 28px;margin-top:-28px}'
    + '.srp-h{font-size:clamp(26px,6.4vw,36px);font-weight:700;letter-spacing:-.035em;line-height:1.04;margin:0}'
    + '.srp-h em{font-style:italic;font-weight:400}'
    + '.srp-p{margin:12px 0 0;font-size:15px;line-height:1.5;color:rgba(255,255,255,.76)}'
    + '.srp-a{display:inline-flex;align-items:center;gap:14px;margin-top:20px;padding:7px 7px 7px 24px;border-radius:999px;background:#AC0A10;color:#fff;font-weight:700;font-size:15px;line-height:1;text-decoration:none;transition:background .45s cubic-bezier(.16,1,.3,1)}'
    + '.srp-a:hover{background:#F2B33D;color:#491417}'
    + '.srp-a i{width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,.16);display:grid;place-items:center;font-style:normal}'
    + '.srp-a svg{width:16px;height:16px}'
    + '.srp-no{display:block;margin-top:14px;background:none;border:0;color:rgba(255,255,255,.55);font:inherit;font-size:13px;cursor:pointer;text-decoration:underline;text-underline-offset:3px;padding:0}'
    + '.srp-no:hover{color:#fff}'
    + '@media(min-width:720px){.srp{align-items:center;padding:24px}.srp-box{width:min(92vw,840px);display:grid;grid-template-columns:1.05fr 1fr;border-radius:24px;transform:translateY(24px) scale(.97)}.srp-img{aspect-ratio:auto;min-height:100%}.srp-img::after{background:linear-gradient(90deg,rgba(73,20,23,0) 55%,#491417 100%)}.srp-body{padding:44px 40px 40px 8px;margin:0;display:flex;flex-direction:column;justify-content:center}.srp-h{font-size:clamp(30px,3.4vw,44px)}}'
    + '@media(prefers-reduced-motion:reduce){.srp,.srp-box,.srp-x{transition:none}}';

  function abrir() {
    if (abrir.hecho) return; abrir.hecho = true;
    ls(CLAVE_VISTO, '1');
    var st = d.createElement('style'); st.textContent = css; d.head.appendChild(st);
    var root = d.createElement('div'); root.className = 'srp'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-labelledby', 'srp-h');
    root.innerHTML = '<div class="srp-box">'
      + '<div class="srp-img" aria-hidden="true"><span class="srp-tag">Sorteo · hasta el 27/10</span></div>'
      + '<button type="button" class="srp-x" aria-label="Cerrar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>'
      + '<div class="srp-body"><h2 class="srp-h" id="srp-h">¿Querés ganarte <em>3 noches en Río?</em></h2>'
      + '<p class="srp-p">Para 2 personas, con desayuno, en zona Copacabana. Participás en 1 minuto.</p>'
      + '<a class="srp-a" href="' + URL_SORTEO + '">Quiero participar <i><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></i></a>'
      + '<button type="button" class="srp-no">Ahora no, gracias</button></div></div>';
    d.body.appendChild(root);
    var ultimo = d.activeElement, foco = root.querySelectorAll('button, a');
    function cerrar() { root.classList.remove('on'); d.removeEventListener('keydown', tecla); setTimeout(function () { root.remove(); }, reduce ? 0 : 450); if (ultimo && ultimo.focus) ultimo.focus(); }
    function tecla(e) {
      if (e.key === 'Escape') return cerrar();
      if (e.key !== 'Tab') return;                       /* el foco queda dentro del popup */
      var a = foco[0], z = foco[foco.length - 1];
      if (e.shiftKey && d.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && d.activeElement === z) { e.preventDefault(); a.focus(); }
    }
    root.querySelector('.srp-x').addEventListener('click', cerrar);
    root.querySelector('.srp-no').addEventListener('click', cerrar);
    root.addEventListener('click', function (e) { if (e.target === root) cerrar(); });
    root.querySelector('.srp-a').addEventListener('click', function () { gtm('sorteo_popup_click'); });
    d.addEventListener('keydown', tecla);
    requestAnimationFrame(function () { requestAnimationFrame(function () { root.classList.add('on'); root.querySelector('.srp-a').focus(); }); });
    gtm('sorteo_popup_visto');
  }
  var timer = setTimeout(abrir, 8000);
  function alScroll() {
    var h = d.documentElement.scrollHeight - innerHeight;
    if (h > 0 && scrollY / h >= 0.4) { clearTimeout(timer); removeEventListener('scroll', alScroll); abrir(); }
  }
  addEventListener('scroll', alScroll, { passive: true });
})();
