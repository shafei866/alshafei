/* main.js — الصفحة الرئيسية: سلايدر سريع تقليب كل 2.8 ثانية + كروت الأقسام من JSON */

const HERO_SLIDES = [
  { image: 'assets/images/hero-cover-1.jpg', fallback: 'https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=1800&q=85', alt: 'مائدة ضيافة رمضانية دافئة' },
  { image: 'assets/images/hero-cover-2.jpg', fallback: 'https://images.unsplash.com/photo-1517816743773-6e0fd518b4a6?auto=format&fit=crop&w=1800&q=85', alt: 'فوانيس وإضاءة رمضانية هادئة' },
  { image: 'assets/images/hero-cover-3.jpg', fallback: 'https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?auto=format&fit=crop&w=1800&q=85', alt: 'تفاصيل مائدة وديكور رمضان' }
];

function initHeroSlider() {
  const hero = document.getElementById('hero');
  const dotsWrap = document.getElementById('heroDots');
  if (!hero || !dotsWrap) return;

  HERO_SLIDES.forEach((slide, i) => {
    const div = document.createElement('div');
    div.className = 'hero-slide' + (i === 0 ? ' is-active' : '');
    div.innerHTML = `<img src="${slide.image}" alt="${slide.alt}" loading="${i === 0 ? 'eager' : 'lazy'}" onerror="this.src='${slide.fallback}'">`;
    hero.prepend(div);

    const dot = document.createElement('button');
    dot.className = 'hero-dot' + (i === 0 ? ' is-active' : '');
    dot.setAttribute('aria-label', `الشريحة ${i + 1}`);
    dot.addEventListener('click', () => goToSlide(i));
    dotsWrap.appendChild(dot);
  });

  const slides = hero.querySelectorAll('.hero-slide');
  const dots = dotsWrap.querySelectorAll('.hero-dot');
  let current = 0;
  let timer;

  function goToSlide(index) {
    slides[current].classList.remove('is-active');
    dots[current].classList.remove('is-active');
    current = index;
    slides[current].classList.add('is-active');
    dots[current].classList.add('is-active');
    resetTimer();
  }

  function nextSlide() {
    goToSlide((current + 1) % slides.length);
  }

  function resetTimer() {
    clearInterval(timer);
    /* مدة تقليب سريعة: 2.8 ثانية بدلاً من 5 ثوانٍ */
    timer = setInterval(nextSlide, 2800);
  }

  resetTimer();
}

async function renderCategoryCards() {
  const grid = document.getElementById('catGrid');
  if (!grid) return;
  try {
    const categories = await getCategories();
    grid.innerHTML = categories.map(cat => `
      <a class="cat-card" href="category.html?cat=${encodeURIComponent(cat.slug)}">
        <img src="${cat.cover}" alt="${cat.name}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=700&q=80'">
        <span class="cat-arrow">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M7 17L17 7M17 7H8M17 7v9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </span>
        <div class="cat-card-body">
          <span class="cat-badge">استكشفي التصنيف</span>
          <h3>${cat.name}</h3>
          <p>${cat.tagline}</p>
        </div>
      </a>
    `).join('');
  } catch (e) {
    console.error("فشل تحميل categories.json:", e);
    grid.innerHTML = '<p class="state-msg">تعذر تحميل التصنيفات حاليًا. تأكدي من تشغيل السيرفر المحلي.</p>';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initHeroSlider();
  renderCategoryCards();
});
