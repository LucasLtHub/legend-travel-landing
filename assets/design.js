/* Legend Travel — comportamiento compartido del sitio · v2 (sincronizado con la home final).
   Entrada del hero, cabecera, menú, aparición al scrollear, botones imantados,
   tarjeta de medios de pago, conversación de preguntas, íconos del cierre,
   línea de la historia. Cada bloque se activa solo si la página tiene el componente. */
(function () {
  'use strict';
  var d = document;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var io = 'IntersectionObserver' in window;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }

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

  /* aparición al entrar en pantalla; los hermanos .rv de un mismo bloque entran escalonados (--d) */
  var rvs = d.querySelectorAll('.rv');
  rvs.forEach(function (el) {
    if (el.style.getPropertyValue('--d')) return;
    var p = el.parentElement, i = 0, n = p ? p.children : [];
    for (var k = 0; k < n.length && n[k] !== el; k++) if (n[k].classList.contains('rv')) i++;
    if (i) el.style.setProperty('--d', Math.min(i, 6) * 90 + 'ms');
  });
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

  /* hilo dorado de progreso (decorativo, solo escritorio) */
  if (!reduce && !d.querySelector('.thread')) {
    var t = d.createElement('div');
    t.className = 'thread';
    t.setAttribute('aria-hidden', 'true');
    t.innerHTML = '<i></i><b></b>';
    d.body.appendChild(t);
  }

  /* botones principales: leve atracción al cursor (como los de la home) */
  if (fine && !reduce) {
    d.querySelectorAll('.btn-hero-main, .bigbtn, .btn-white, .btn[data-magnet], .dbtn, .btn-amedida').forEach(function (b) {
      if (b.classList.contains('rv')) return; /* ya anima su transform al aparecer */
      var raf = null, tx = 0, ty = 0;
      function paint() { b.style.transform = 'translate(' + tx + 'px,' + ty + 'px)'; raf = null; }
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        tx = (e.clientX - (r.left + r.width / 2)) * 0.22;
        ty = (e.clientY - (r.top + r.height / 2)) * 0.3;
        if (!raf) raf = requestAnimationFrame(paint);
      });
      b.addEventListener('pointerleave', function () {
        tx = 0; ty = 0;
        if (!raf) raf = requestAnimationFrame(paint);
      });
    });
  }

  /* medios de pago: la tarjeta se inclina hacia el mouse (al scrollear, en el celular)
     y los medios se encienden uno a uno mientras está a la vista */
  d.querySelectorAll('.fin .chips').forEach(function (card) {
    var chips = [].slice.call(card.querySelectorAll('.chip')), idx = -1, timer = null, raf = null, rx = 0, ry = 0, mx = 30, my = 20;
    if (!chips.length) return;
    function pick(i) { idx = i; chips.forEach(function (c, k) { c.classList.toggle('on', k === i); }); }
    function start() { if (timer || reduce) return; if (idx < 0) pick(0); timer = setInterval(function () { pick((idx + 1) % chips.length); }, 1700); }
    function stop() { clearInterval(timer); timer = null; }
    if (reduce) { chips.forEach(function (c) { c.classList.add('on'); }); return; }
    if (io) new IntersectionObserver(function (es) { es[0].isIntersecting ? start() : stop(); }, { threshold: .4 }).observe(card); else start();
    chips.forEach(function (c, i) { c.addEventListener('pointerenter', function () { stop(); pick(i); }); c.addEventListener('click', function () { stop(); pick(i); }); });
    card.addEventListener('pointerleave', start);
    function paint() { raf = null; card.style.setProperty('--rx', rx.toFixed(2) + 'deg'); card.style.setProperty('--ry', ry.toFixed(2) + 'deg'); card.style.setProperty('--mx', mx.toFixed(1) + '%'); card.style.setProperty('--my', my.toFixed(1) + '%'); }
    if (fine) {
      card.addEventListener('pointermove', function (e) { var r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height; ry = (x - .5) * 22; rx = -(y - .5) * 16; mx = x * 100; my = y * 100; if (!raf) raf = requestAnimationFrame(paint); });
      card.addEventListener('pointerleave', function () { rx = 0; ry = 0; mx = 30; my = 20; if (!raf) raf = requestAnimationFrame(paint); });
    } else {
      var sraf = null;
      var onScroll = function () { sraf = null; var r = card.getBoundingClientRect(), c = (r.top + r.height / 2) / innerHeight; rx = clamp((c - .5) * -26, -14, 14); ry = clamp((c - .5) * 10, -6, 6); mx = 50 + (c - .5) * 60; my = 20 + (c - .5) * 80; paint(); };
      addEventListener('scroll', function () { if (!sraf) sraf = requestAnimationFrame(onScroll); }, { passive: true }); onScroll();
    }
  });

  /* preguntas frecuentes: aparecen como una conversación (llega la pregunta, Legend escribe, llega la respuesta) */
  d.querySelectorAll('.faqwrap').forEach(function (wrap) {
    var bs = [], typ = d.createElement('div'), i = 0, started = false;
    wrap.querySelectorAll('.faq').forEach(function (f) {
      var b = f.querySelector('button'), a = f.querySelector('.ans');
      if (b) { b.setAttribute('aria-expanded', 'true'); b.tabIndex = -1; bs.push(b); }
      if (a) { a.style.maxHeight = ''; bs.push(a); }
    });
    if (!bs.length) return;
    typ.className = 'faq-typing'; typ.setAttribute('aria-hidden', 'true'); typ.innerHTML = '<i></i><i></i><i></i>';
    if (reduce || !io) { bs.forEach(function (b) { b.classList.add('in'); }); return; }
    var lista = wrap.querySelector('.faq').parentElement; /* en madres e hijas los .faq van dentro de un .rv */
    lista.appendChild(typ);
    function next() {
      if (i >= bs.length) { typ.classList.remove('on'); return; }
      var b = bs[i];
      if (b.classList.contains('ans')) {
        typ.classList.add('on'); lista.appendChild(typ);
        setTimeout(function () { typ.classList.remove('on'); b.classList.add('in'); i++; setTimeout(next, 500); }, 900);
      } else { b.classList.add('in'); i++; setTimeout(next, 700); }
    }
    new IntersectionObserver(function (es, o) { if (es[0].isIntersecting && !started) { started = true; o.disconnect(); setTimeout(next, 300); } }, { threshold: .2 }).observe(wrap);
  });

  /* cierre de contacto: los íconos cobran vida al aparecer (pin que cae y late, WhatsApp que vibra, reloj que gira) */
  d.querySelectorAll('.contact, .cierre').forEach(function (sec) {
    var cards = sec.querySelectorAll('.ccard');
    if (!cards.length) return;
    cards.forEach(function (c) {
      var txt = (c.textContent || '').toLowerCase();
      if (txt.indexOf('whatsapp') >= 0 || txt.indexOf('+54') >= 0) c.classList.add('ic-wa');
      else if (txt.indexOf('horario') >= 0 || /\d+\s*a\s*\d+\s*h/.test(txt)) c.classList.add('ic-clock');
      else { c.classList.add('ic-pin'); var r = d.createElement('i'); r.className = 'radar'; r.setAttribute('aria-hidden', 'true'); c.appendChild(r); }
    });
    if (reduce || !io) { sec.classList.add('in'); return; }
    new IntersectionObserver(function (es, o) { if (es[0].isIntersecting) { sec.classList.add('in'); o.disconnect(); } }, { threshold: .3 }).observe(sec.querySelector('.cgrid') || sec);
  });

  /* historia: el hito que pasa por el centro se enciende y la línea se va llenando */
  d.querySelectorAll('.hist-timeline').forEach(function (tl) {
    var eras = [].slice.call(tl.querySelectorAll('.hist-block'));
    if (!eras.length) return;
    if (reduce || !io) { eras.forEach(function (e) { e.classList.add('on'); }); tl.style.setProperty('--k', 1); return; }
    var obsH = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        var i = eras.indexOf(e.target);
        eras.forEach(function (x, k) { x.classList.toggle('on', k <= i); });
        var r = e.target.getBoundingClientRect(), t = tl.getBoundingClientRect();
        tl.style.setProperty('--k', clamp((r.top + 14 - t.top) / t.height, 0, 1).toFixed(3));
      });
    }, { rootMargin: '-45% 0px -45% 0px', threshold: 0 });
    eras.forEach(function (e) { obsH.observe(e); });
  });
})();
