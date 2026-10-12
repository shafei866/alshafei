/* category.js — صفحة المنتجات حسب التصنيف واستدعاء JSON */

let CURRENT_PRODUCTS = [];

async function initCategoryPage() {
  const slug = qs('cat');
  const grid = document.getElementById('productGrid');
  const emptyState = document.getElementById('emptyState');
  const chipsContainer = document.getElementById('categoryChips');

  try {
    const [categories, products] = await Promise.all([getCategories(), getProducts()]);
    const category = categories.find(c => c.slug === slug) || categories[0];

    if (!category) {
      document.getElementById('catTitle').textContent = 'التصنيف غير موجود';
      return;
    }

    document.title = `${category.name} | الشافعي`;
    document.getElementById('catBannerImg').src = category.banner;
    document.getElementById('catBannerImg').alt = category.name;
    document.getElementById('catTitle').textContent = category.name;
    document.getElementById('breadcrumbName').textContent = category.name;

    chipsContainer.innerHTML = categories.map(c => `
      <a class="cat-chip${c.slug === category.slug ? ' is-active' : ''}" href="category.html?cat=${encodeURIComponent(c.slug)}">
        ${c.name}
      </a>
    `).join('');

    const filtered = products.filter(p => p.categorySlug === category.slug);
    CURRENT_PRODUCTS = filtered;

    document.getElementById('catCount').textContent = `${filtered.length} قطع مختارة`;

    if (filtered.length === 0) {
      emptyState.hidden = false;
      grid.hidden = true;
      return;
    }

    grid.innerHTML = filtered.map((p, index) => `
      <article class="product-card" data-id="${p.id}" style="animation-delay: ${Math.min(index * 0.08, 0.6)}s">
        <figure>
          <img src="${p.image}" alt="${p.title}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=600&q=80'">
        </figure>
        <div class="product-card-body">
          <span class="product-tag">${p.tag}</span>
          <h3>${p.title}</h3>
          <button class="explore-btn" type="button">
            استكشفي القطعة
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M19 12H5M5 12l6-6M5 12l6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
      </article>
    `).join('');

    grid.querySelectorAll('.product-card').forEach(card => {
      card.addEventListener('click', () => {
        const prod = CURRENT_PRODUCTS.find(p => p.id === card.dataset.id);
        attachProductModal(prod);
      });
    });

  } catch (e) {
    grid.innerHTML = '';
    emptyState.hidden = false;
    emptyState.textContent = 'حدث خطأ أثناء تحميل القطع. تأكدي من تشغيل السيرفر المحلي.';
  }
}

document.addEventListener('DOMContentLoaded', initCategoryPage);
