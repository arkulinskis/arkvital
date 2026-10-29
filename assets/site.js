(() => {
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
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealItems = document.querySelectorAll('.hero-copy, .hero-photo, .about-text, .about-photo, .section-head, .card, .project, .post, .visual-tile, .step, .service-row, .split-callout');
  if (!reducedMotion && 'IntersectionObserver' in window) {
    document.documentElement.classList.add('motion-ready');
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

  const parallaxItems = document.querySelectorAll('.hero-photo, .hero-backdrop, .about-photo, .visual-tile, .project');
  if (!reducedMotion) {
    document.documentElement.classList.add('parallax-ready');
    let frameRequested = false;
    const updateParallax = () => {
      const viewportCenter = window.innerHeight / 2;
      parallaxItems.forEach((item) => {
        const bounds = item.getBoundingClientRect();
        const distance = (bounds.top + bounds.height / 2 - viewportCenter) * -0.035;
        const offset = Math.max(-22, Math.min(22, distance));
        item.style.setProperty('--parallax-y', `${offset.toFixed(1)}px`);
      });
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollable > 0 ? window.scrollY / scrollable : 0;
      document.documentElement.style.setProperty('--scroll-progress', progress.toFixed(4));
      const header = document.querySelector('.site-header');
      if (header) header.classList.toggle('scrolled', window.scrollY > 8);
      frameRequested = false;
    };
    const requestParallaxUpdate = () => {
      if (!frameRequested) {
        frameRequested = true;
        window.requestAnimationFrame(updateParallax);
      }
    };
    window.addEventListener('scroll', requestParallaxUpdate, { passive: true });
    window.addEventListener('resize', requestParallaxUpdate, { passive: true });
    requestParallaxUpdate();
  }
})();
