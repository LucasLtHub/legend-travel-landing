/* Legend Travel — comportamiento compartido del sitio.
   Reemplaza al script que cada página llevaba inline: entrada del hero,
   cabecera, menú, aparición al scrollear, acordeón de preguntas. */
(function () {
  'use strict';
  var d = document;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var io = 'IntersectionObserver' in window;

  /* entrada escalonada del hero (.fade con data-delay) */
  d.querySelectorAll('.fade').forEach(function (el) {
    if (reduce) { el.classList.add('in'); return; }
    setTimeout(function () { el.classList.add('in'); }, parseInt(el.dataset.delay || '0', 10));
  });

  /* cabecera: transparente arriba de todo, sólida apenas se scrollea.
     (Un testigo invisible de 140px al tope de la página; sin scroll listeners.) */
  var nav = d.querySelector('.navwrap');
  var hero = d.querySelector('.hero, .dhero, .blog-hero');
  if (nav) {
    if (hero && io) {
      var testigo = d.createElement('div');
      testigo.setAttribute('aria-hidden', 'true');
      testigo.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:140px;pointer-events:none;visibility:hidden';
      d.body.appendChild(testigo);
      new IntersectionObserver(function (es) {
        nav.classList.toggle('solid', !es[0].isIntersecting);
      }, { threshold: 0 }).observe(testigo);
    } else {
      nav.classList.add('solid');
    }
  }

  /* menú móvil */
  var menu = d.getElementById('navMobile');
  var openBtn = d.getElementById('navToggleBtn');
  var closeBtn = d.getElementById('navCloseBtn');
  function setMenu(open) {
    if (!menu) return;
    menu.classList.toggle('open', open);
    d.body.style.overflow = open ? 'hidden' : '';
    if (openBtn) openBtn.setAttribute('aria-expanded', open);
  }
  if (menu && openBtn) {
    openBtn.setAttribute('aria-expanded', 'false');
    openBtn.addEventListener('click', function () { setMenu(true); });
    if (closeBtn) closeBtn.addEventListener('click', function () { setMenu(false); });
    menu.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { setMenu(false); });
    });
    d.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('open')) setMenu(false);
    });
  }

  /* aparición al entrar en pantalla */
  var rvs = d.querySelectorAll('.rv');
  if (io && !reduce) {
    var obs = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target); }
      });
    }, { threshold: 0, rootMargin: '0px 0px -8% 0px' }); /* threshold 0: un bloque más alto que la pantalla nunca llega a un % visible */
    rvs.forEach(function (el) { obs.observe(el); });
  } else {
    rvs.forEach(function (el) { el.classList.add('in'); });
  }

  /* preguntas frecuentes */
  d.querySelectorAll('.faq').forEach(function (f) {
    var btn = f.querySelector('button');
    var ans = f.querySelector('.ans');
    if (!btn || !ans) return;
    btn.addEventListener('click', function () {
      var open = f.classList.toggle('open');
      btn.setAttribute('aria-expanded', open);
      ans.style.maxHeight = open ? ans.scrollHeight + 'px' : 0;
    });
  });

  /* hilo dorado de progreso (decorativo, solo escritorio) */
  if (!reduce && !d.querySelector('.thread')) {
    var t = d.createElement('div');
    t.className = 'thread';
    t.setAttribute('aria-hidden', 'true');
    t.innerHTML = '<i></i><b></b>';
    d.body.appendChild(t);
  }

  /* botones principales: leve atracción al cursor */
  if (fine && !reduce) {
    d.querySelectorAll('.btn-hero-main, .bigbtn, .btn-white').forEach(function (b) {
      if (b.classList.contains('rv')) return; /* ya anima su transform al aparecer */
      var raf = null, tx = 0, ty = 0;
      function paint() { b.style.transform = 'translate(' + tx + 'px,' + ty + 'px)'; raf = null; }
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        tx = (e.clientX - (r.left + r.width / 2)) * 0.2;
        ty = (e.clientY - (r.top + r.height / 2)) * 0.28;
        if (!raf) raf = requestAnimationFrame(paint);
      });
      b.addEventListener('pointerleave', function () {
        tx = 0; ty = 0;
        if (!raf) raf = requestAnimationFrame(paint);
      });
    });
  }
})();
