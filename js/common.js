/* common.js — استدعاء JSON النظيف كما في ويب القهوة */

const DATA_PATHS = {
  categories: 'data/categories.json',
  products: 'data/products.json'
};

async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error('تعذر تحميل البيانات من: ' + path);
  return await res.json();
}

function getCategories() { return loadJSON(DATA_PATHS.categories); }
function getProducts() { return loadJSON(DATA_PATHS.products); }

function qs(param) {
  return new URLSearchParams(window.location.search).get(param);
}

/* تفعيل القائمة الجانبية في الهواتف والتابلت */
function initMobileMenu() {
  const toggle = document.getElementById('menuToggle');
  const nav = document.getElementById('mainNav');
  if (!toggle || !nav) return;

  toggle.addEventListener('click', () => {
    nav.classList.toggle('is-open');
  });

  document.addEventListener('click', (e) => {
    if (!toggle.contains(e.target) && !nav.contains(e.target)) {
      nav.classList.remove('is-open');
    }
  });
}

/* تذييل الصفحة المشترك */
async function renderFooterCategories() {
  const el = document.getElementById('footerCats');
  if (!el) return;
  try {
    const categories = await getCategories();
    el.innerHTML = categories.map(c =>
      `<li><a href="category.html?cat=${encodeURIComponent(c.slug)}">${c.name}</a></li>`
    ).join('');
  } catch (e) {}
}

/* نافذة تفاصيل المنتج المشتركة */
function attachProductModal(product) {
  if (!product) return;

  document.getElementById('modalTag').textContent = product.tag;
  document.getElementById('modalTitle').textContent = product.title;
  document.getElementById('modalDesc').textContent = product.description;
  document.getElementById('modalOrigin').textContent = product.craftsmanship || 'مختارة بعناية للمجموعة الرمضانية';
  document.getElementById('modalDims').textContent = product.dimensions;
  document.getElementById('modalStyling').textContent = product.styling;

  const gallery = (product.gallery && product.gallery.length) ? product.gallery : [product.image];
  const mainImg = document.getElementById('modalMainImg');
  mainImg.src = gallery[0];
  mainImg.alt = product.title;

  const thumbsWrap = document.getElementById('modalThumbs');
  thumbsWrap.innerHTML = gallery.map((src, i) => `
    <button class="modal-thumb${i === 0 ? ' is-active' : ''}" data-src="${src}" aria-label="صورة ${i + 1}">
      <img src="${src}" alt="" onerror="this.src='https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=150&q=80'">
    </button>
  `).join('');

  thumbsWrap.querySelectorAll('.modal-thumb').forEach(btn => {
    btn.addEventListener('click', () => {
      thumbsWrap.querySelectorAll('.modal-thumb').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      mainImg.src = btn.dataset.src;
    });
  });

  const overlay = document.getElementById('modalOverlay');
  overlay.classList.add('is-open');
  document.body.style.overflow = 'hidden';
}

function initModalCloseHandlers() {
  const overlay = document.getElementById('modalOverlay');
  const closeBtn = document.getElementById('modalClose');
  if (!overlay || !closeBtn) return;

  const close = () => {
    overlay.classList.remove('is-open');
    document.body.style.overflow = '';
  };

  closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.classList.contains('is-open')) close();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initMobileMenu();
  renderFooterCategories();
  initModalCloseHandlers();
});
