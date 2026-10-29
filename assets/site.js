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
  document.querySelectorAll('#year, .footer-year').forEach((el) => { el.textContent = new Date().getFullYear(); });

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Fade and lift content in as it scrolls into view.
  const revealItems = document.querySelectorAll('.hero-copy, .hero-photo, .about-text, .about-photo, .section-head, .card, .project, .post, .visual-tile, .step, .service-row, .split-callout, .band-copy, .cta-copy, .cta-photo');
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
