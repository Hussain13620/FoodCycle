/**
 * FoodCycle - Client-Side Interactive Engine
 * Handles modals, toasts, countdowns, filtering, and chart helpers.
 */

// Toast notification helper
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info'}"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  if (window.lucide) {
    lucide.createIcons();
  }

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal open/close helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Initialize countdown timers on surplus items
function initCountdowns() {
  const countdownEls = document.querySelectorAll('[data-expiry]');
  countdownEls.forEach(el => {
    const expiryStr = el.getAttribute('data-expiry');
    if (!expiryStr) return;

    const expiryDate = new Date(expiryStr);
    const now = new Date();
    const diffMs = expiryDate - now;

    if (diffMs <= 0) {
      el.innerHTML = '<span class="badge badge-danger">Expired</span>';
      return;
    }

    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (hours < 1) {
      el.innerHTML = `<span class="badge badge-warning"><i data-lucide="clock"></i> Urgent: ${mins}m left</span>`;
    } else {
      el.innerHTML = `<span class="badge badge-leaf"><i data-lucide="clock"></i> ${hours}h ${mins}m left</span>`;
    }
  });
  if (window.lucide) lucide.createIcons();
}

// Client-side search and category filtering for marketplace
function filterMarketplace() {
  const searchInput = document.getElementById('marketplace-search');
  const categoryFilter = document.getElementById('marketplace-category');
  const dietaryFilter = document.getElementById('marketplace-dietary');

  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const category = categoryFilter ? categoryFilter.value : 'all';
  const dietary = dietaryFilter ? dietaryFilter.value : 'all';

  const cards = document.querySelectorAll('.marketplace-card');
  let visibleCount = 0;

  cards.forEach(card => {
    const dish = (card.getAttribute('data-dish') || '').toLowerCase();
    const cardCat = card.getAttribute('data-category') || '';
    const isVeg = card.getAttribute('data-veg') === 'true';

    let matchesSearch = !query || dish.includes(query);
    let matchesCategory = (category === 'all') || (cardCat === category);
    let matchesDietary = (dietary === 'all') ||
      (dietary === 'veg' && isVeg) ||
      (dietary === 'nonveg' && !isVeg);

    if (matchesSearch && matchesCategory && matchesDietary) {
      card.style.display = '';
      visibleCount++;
    } else {
      card.style.display = 'none';
    }
  });

  const emptyMsg = document.getElementById('marketplace-empty-results');
  if (emptyMsg) {
    emptyMsg.style.display = (visibleCount === 0 && cards.length > 0) ? 'block' : 'none';
  }
}

// Quick demo login credential filler
function fillDemoLogin(role) {
  const emailInput = document.getElementById('login-email');
  const passwordInput = document.getElementById('login-password');
  if (!emailInput || !passwordInput) return;

  if (role === 'restaurant') {
    emailInput.value = 'restaurant@foodcycle.org';
    passwordInput.value = 'demo123';
    showToast('Loaded demo restaurant credentials (The Spice Pavilion)');
  } else if (role === 'ngo') {
    emailInput.value = 'ngo@foodcycle.org';
    passwordInput.value = 'demo123';
    showToast('Loaded demo NGO credentials (Annapurna Food Relief)');
  }
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  if (window.lucide) {
    lucide.createIcons();
  }

  // Countdowns
  initCountdowns();
  setInterval(initCountdowns, 60000);

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });

  // Alert dismiss buttons
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) alert.remove();
    });
  });
});
