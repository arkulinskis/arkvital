(() => {
  const root = document.documentElement;
  const button = document.querySelector('.menu-toggle');
  const menu = document.querySelector('.nav-links');
  if (button && menu) {
    button.addEventListener('click', () => {
      const open = button.getAttribute('aria-expanded') !== 'true';
      button.setAttribute('aria-expanded', String(open));
      button.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      menu.classList.toggle('open', open);
    });
    menu.addEventListener('click', (event) => {
      if (event.target.closest('a')) {
        menu.classList.remove('open');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-label', 'Open menu');
      }
    });
  }
  // Videos: show a local thumbnail; load the YouTube player only when someone presses play.
  document.querySelectorAll('.video-frame[data-video]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const p = new URLSearchParams({ autoplay: '1', rel: '0', modestbranding: '1', playsinline: '1' });
      if (link.dataset.start) p.set('start', link.dataset.start);
      if (link.dataset.end) p.set('end', link.dataset.end);
      const frame = document.createElement('iframe');
      frame.src = `https://www.youtube-nocookie.com/embed/${link.dataset.video}?${p}`;
      frame.title = link.dataset.title || 'YouTube video';
      frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      const box = document.createElement('div');
      box.className = 'video-frame';
      box.appendChild(frame);
      link.replaceWith(box);
      frame.focus();
    });
  });
  document.querySelectorAll('#year, .footer-year').forEach((el) => { el.textContent = new Date().getFullYear(); });

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Fade and lift content in as it scrolls into view.
  const revealItems = document.querySelectorAll('.hero-copy, .hero-photo, .about-text, .about-photo, .section-head, .card, .project, .post, .video, .visual-tile, .step, .service-row, .split-callout, .band-copy, .cta-copy, .cta-photo');
  if (!reducedMotion && 'IntersectionObserver' in window) {
    root.classList.add('motion-ready');
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -36px 0px' });
    revealItems.forEach((item, index) => {
      item.classList.add('reveal-on-scroll');
      item.style.setProperty('--reveal-delay', `${Math.min(index % 4, 3) * 75}ms`);
      revealObserver.observe(item);
    });
  }

  // Rotating topic in the home hero.
  const heroTopic = document.querySelector('.hero-topic');
  if (heroTopic && !reducedMotion) {
    const topics = (heroTopic.dataset.topics || '').split('|').filter(Boolean);
    let topicIndex = 0;
    if (topics.length > 1) {
      window.setInterval(() => {
        if (document.visibilityState === 'hidden') return;
        heroTopic.classList.add('is-changing');
        window.setTimeout(() => {
          topicIndex = (topicIndex + 1) % topics.length;
          heroTopic.textContent = topics[topicIndex];
          heroTopic.classList.remove('is-changing');
        }, 240);
      }, 3200);
    }
  }

  // Count up the leading number in each fact ("12+ years") once it is on screen.
  const counters = [...document.querySelectorAll('.experience-band .fact b')]
    .map((el) => ({ el, match: el.textContent.match(/^(\d+)(.*)$/) }))
    .filter((c) => c.match);
  if (counters.length && !reducedMotion && 'IntersectionObserver' in window) {
    const run = ({ el, match }) => {
      const target = Number(match[1]);
      const start = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - start) / 1400);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased) + match[2];
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    const countObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        counters.filter((c) => c.el === entry.target).forEach(run);
      });
    }, { threshold: 0.6 });
    counters.forEach((c) => { c.el.textContent = '0' + c.match[2]; countObserver.observe(c.el); });
  }

  // Scroll effects.
  //   data-parallax="hero"   the home hero photo drifts down and slowly zooms; the copy lifts and fades.
  //   data-parallax="inner"  the photo drifts inside its frame (data-speed = share of its height, e.g. 0.07).
  //   data-parallax="band"   a full-bleed photo with extra height drifts behind its section.
  //   data-parallax="depth"  the element itself floats (data-speed = pixels each way; negative floats the other way).
  const header = document.querySelector('.site-header');
  const items = [...document.querySelectorAll('[data-parallax]')].map((el) => ({
    el, mode: el.dataset.parallax, speed: parseFloat(el.dataset.speed || '0'),
  }));
  const hero = document.querySelector('.hero-full');
  const heroInner = hero && hero.querySelector('.hero-inner');
  const heroScroll = hero && hero.querySelector('.hero-scroll');
  if (!reducedMotion && items.length) root.classList.add('parallax-ready');

  let frameRequested = false;
  const update = () => {
    frameRequested = false;
    const vh = window.innerHeight;
    const y = window.scrollY;
    const scrollable = root.scrollHeight - vh;
    root.style.setProperty('--scroll-progress', (scrollable > 0 ? y / scrollable : 0).toFixed(4));
    if (header) header.classList.toggle('scrolled', y > 8);
    if (reducedMotion) return;

    items.forEach((item) => {
      const { el, mode, speed } = item;
      if (mode === 'hero') {
        const h = el.offsetHeight || vh;
        const s = Math.min(y, h * 1.2);
        const k = window.innerWidth < 820 ? 0.16 : 0.3;
        el.style.setProperty('--px-y', `${(s * k).toFixed(1)}px`);
        el.style.setProperty('--px-s', (1 + (s * k) / h + 0.02).toFixed(4));
        return;
      }
      const r = el.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) return;
      // -1 when the element is just leaving the top of the screen, +1 when it is just entering at the bottom.
      const p = Math.max(-1, Math.min(1, (r.top + r.height / 2 - vh / 2) / ((vh + r.height) / 2)));
      if (mode === 'inner') {
        const sp = speed || 0.07;
        el.style.setProperty('--px-y', `${(-p * sp * r.height).toFixed(1)}px`);
        el.style.setProperty('--px-s', (1 + 2 * sp + 0.01).toFixed(3));
      } else if (mode === 'band') {
        // the photo is 30% taller than its frame: 15% spare above and below
        el.style.setProperty('--px-y', `${(-p * 0.15 * r.height).toFixed(1)}px`);
      } else if (mode === 'depth') {
        el.style.setProperty('--px-y', `${(p * (speed || 24)).toFixed(1)}px`);
      }
    });

    if (hero && heroInner) {
      const h = hero.offsetHeight || vh;
      const t = Math.min(1, Math.max(0, y / (h * 0.75)));
      heroInner.style.setProperty('--hero-lift', `${(-y * 0.12).toFixed(1)}px`);
      heroInner.style.setProperty('--hero-fade', (1 - t * 0.7).toFixed(3));
      if (heroScroll) heroScroll.style.opacity = String(Math.max(0, 1 - y / 160));
    }
  };
  const request = () => {
    if (!frameRequested) {
      frameRequested = true;
      window.requestAnimationFrame(update);
    }
  };
  window.addEventListener('scroll', request, { passive: true });
  window.addEventListener('resize', request, { passive: true });
  window.addEventListener('load', request);
  request();
})();

// Home page: three apps picked at random from all of them (data from tools/seo.py), plus Shuffle.
(() => {
  const box = document.querySelector('[data-app-picks]');
  const data = document.getElementById('app-picks-data');
  if (!box || !data) return;
  let apps;
  try { apps = JSON.parse(data.textContent); } catch (e) { return; }
  if (!Array.isArray(apps) || apps.length < 4) return;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const card = (a) => `<a class="project app-pick" href="${esc(a.url)}" target="_blank" rel="noopener">`
    + `<img src="assets/img/apps/${esc(a.key)}.webp" alt="" width="720" height="450" loading="lazy">`
    + `<div><span class="project-type">${esc(a.group)}</span><h3>${esc(a.name)}</h3><p>${esc(a.description)}</p>`
    + `<span class="project-link">${esc(a.host)} ↗</span></div></a>`;
  let shown = [...box.querySelectorAll('[data-key]')].map((el) => el.dataset.key);
  const pick = () => {
    const pool = apps.filter((a) => !shown.includes(a.key));
    const out = [];
    while (out.length < 3 && pool.length) out.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
    shown = out.map((a) => a.key);
    box.innerHTML = out.map(card).join('');
    box.querySelectorAll('.app-pick').forEach((el, i) => { el.dataset.key = shown[i]; });
  };
  pick();
  const btn = document.querySelector('[data-app-shuffle]');
  if (btn) {
    btn.hidden = false;
    btn.addEventListener('click', () => {
      pick();
      const live = document.getElementById('app-picks-status');
      if (live) live.textContent = 'Now showing ' + shown.map((k) => apps.find((a) => a.key === k).name).join(', ') + '.';
    });
  }
})();
