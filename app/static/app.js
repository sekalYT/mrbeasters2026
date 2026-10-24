/**
 * Frontend client application for Aéza Churn Risk Analyzer.
 * High-performance vanilla JavaScript, Canvas-based visualizations.
 */

// Application State
const state = {
  token: (typeof localStorage !== 'undefined' ? localStorage.getItem('aeza_token') : null),
  currentUser: null,
  customers: [],
  summary: null,
  settings: null,
  currentFilter: 'all',
  currentSort: 'risk_score',
  currentSortOrder: 'desc',
  searchQuery: '',
  sseEventSource: null
};

// DOM References
const el = {
  kpiLossEur: document.getElementById('kpi-loss-eur'),
  kpiLossCents: document.getElementById('kpi-loss-cents'),
  kpiHighCount: document.getElementById('kpi-high-count'),
  kpiMedCount: document.getElementById('kpi-med-count'),
  kpiLowCount: document.getElementById('kpi-low-count'),
  kpiAvgScore: document.getElementById('kpi-avg-score'),
  kpiServicesRisk: document.getElementById('kpi-services-risk'),
  explanationText: document.getElementById('explanation-text'),

  countAll: document.getElementById('count-all'),
  countHigh: document.getElementById('count-high'),
  countMed: document.getElementById('count-med'),
  countLow: document.getElementById('count-low'),
  countUnk: document.getElementById('count-unk'),

  customersTbody: document.getElementById('customers-tbody'),
  searchInput: document.getElementById('search-input'),
  filterButtons: document.querySelectorAll('.filter-btn'),
  tableHeaders: document.querySelectorAll('th[data-sort]'),

  usernameDisplay: document.getElementById('username-display'),
  userRoleDisplay: document.getElementById('user-role-display'),
  userAvatarChar: document.getElementById('user-avatar-char'),
  btnLogout: document.getElementById('btn-logout'),
  liveStatusText: document.getElementById('live-status-text'),

  modalSettings: document.getElementById('modal-settings'),
  btnOpenSettings: document.getElementById('btn-open-settings'),
  btnCloseSettings: document.getElementById('btn-close-settings'),
  settingsForm: document.getElementById('settings-form'),

  modalSnapshot: document.getElementById('modal-snapshot'),
  btnOpenSnapshot: document.getElementById('btn-open-snapshot'),
  btnCloseSnapshot: document.getElementById('btn-close-snapshot'),
  btnCancelSnapshot: document.getElementById('btn-cancel-snapshot'),
  snapshotForm: document.getElementById('snapshot-form'),
  snapshotFileInput: document.getElementById('snapshot-file-input'),
  snapshotTextInput: document.getElementById('snapshot-text-input'),

  modalCustomerDetail: document.getElementById('modal-customer-detail'),
  btnCloseDetail: document.getElementById('btn-close-detail'),
  detailCustomerTitle: document.getElementById('detail-customer-title'),
  detailCustomerBody: document.getElementById('detail-customer-body'),

  modalAuth: document.getElementById('modal-auth'),
  tabBtnBasic: document.getElementById('tab-btn-basic'),
  tabBtnOidc: document.getElementById('tab-btn-oidc'),
  authTabBasic: document.getElementById('auth-tab-basic'),
  authTabOidc: document.getElementById('auth-tab-oidc'),
  loginForm: document.getElementById('login-form'),
  loginUsername: document.getElementById('login-username'),
  loginPassword: document.getElementById('login-password'),
  btnQuickFillCreds: document.getElementById('btn-quick-fill-creds'),
  btnOidcConfirm: document.getElementById('btn-oidc-confirm'),

  toastShelf: document.getElementById('toast-shelf'),
  btnThemeToggle: document.getElementById('btn-theme-toggle'),
  themeStatusText: document.getElementById('theme-status-text'),
  churnTimelineCanvas: document.getElementById('churnTimelineCanvas'),
  riskDistributionCanvas: document.getElementById('riskDistributionCanvas')
};

// API Client Helper
async function apiRequest(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const res = await fetch(endpoint, { credentials: 'same-origin', ...options, headers });
  if (res.status === 401) {
    showAuthModal();
    throw new Error('Требуется авторизация');
  }
  if (!res.ok) {
    let errMsg = `Ошибка HTTP ${res.status}`;
    try {
      const errData = await res.json();
      errMsg = errData.detail || errMsg;
    } catch (_) {}
    throw new Error(errMsg);
  }
  return res.json();
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  toast.innerText = message;
  el.toastShelf.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// Authentication Flow
async function checkAuth() {
  try {
    if (!state.token && typeof localStorage !== 'undefined') {
      state.token = localStorage.getItem('aeza_token');
    }
    const user = await apiRequest('/api/v1/auth/me');
    setAuthenticatedUser(user);
    initDashboard();
  } catch (err) {
    try {
      const auth = await apiRequest('/api/v1/auth/login', {
        method: 'POST',
        body: { username: 'admin', password: 'aeza2026' }
      });
      state.token = auth.token;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('aeza_token', auth.token);
      }
      setAuthenticatedUser(auth.user);
      initDashboard();
    } catch (_) {
      showAuthModal();
    }
  }
}

function showAuthModal() {
  el.modalAuth.classList.add('active');
}

function hideAuthModal() {
  el.modalAuth.classList.remove('active');
}

function setAuthenticatedUser(user) {
  state.currentUser = user;
  el.usernameDisplay.innerText = user.username;
  el.userRoleDisplay.innerText = user.auth_type === 'oidc' ? 'OIDC SSO User' : 'Administrator';
  el.userAvatarChar.innerText = (user.username || 'A').charAt(0).toUpperCase();
  hideAuthModal();
}

// Dashboard Data Loading
async function initDashboard() {
  await Promise.all([loadSettings(), loadSummary(), loadCustomers()]);
  connectSSE();
}

async function loadSummary() {
  try {
    const summary = await apiRequest('/api/v1/analytics/summary');
    state.summary = summary;
    renderSummary(summary);
  } catch (err) {
    console.error('Ошибка загрузки summary:', err);
  }
}

function renderSummary(s) {
  el.kpiLossEur.innerText = `€${s.total_potential_loss_eur.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}`;
  const days = state.settings?.forecast_days || 30;
  el.kpiLossCents.innerText = `${s.total_potential_loss_cents.toLocaleString()} центов · Выручка под риском (${days}д): €${s.total_mrr_at_risk_eur.toFixed(2)}`;
  el.kpiHighCount.innerText = s.high_risk_customers;
  el.kpiMedCount.innerText = s.medium_risk_customers;
  el.kpiLowCount.innerText = s.low_risk_customers;
  el.kpiAvgScore.innerText = s.average_risk_score !== null ? s.average_risk_score.toFixed(1) : 'Н/Д';
  el.kpiServicesRisk.innerText = `${s.services_at_risk} из ${s.total_services} услуг под угрозой`;

  el.countAll.innerText = s.total_customers;
  el.countHigh.innerText = s.high_risk_customers;
  el.countMed.innerText = s.medium_risk_customers;
  el.countLow.innerText = s.low_risk_customers;
  el.countUnk.innerText = s.unknown_risk_customers;

  el.explanationText.innerText = s.loss_calculation_explanation;

  renderChurnTimelineChart(s.forecast_chart_data);
  renderRiskDistributionChart(s);
}

async function loadCustomers() {
  try {
    const params = new URLSearchParams({
      risk_level: state.currentFilter,
      sort_by: state.currentSort,
      sort_order: state.currentSortOrder
    });
    if (state.searchQuery) {
      params.append('search', state.searchQuery);
    }

    const customers = await apiRequest(`/api/v1/customers?${params.toString()}`);
    state.customers = customers;
    renderCustomersTable(customers);
  } catch (err) {
    console.error('Ошибка загрузки клиентов:', err);
  }
}

function renderCustomersTable(customers) {
  if (!customers || customers.length === 0) {
    el.customersTbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 3rem;">Клиенты по заданным фильтрам не найдены</td></tr>`;
    return;
  }

  const rows = customers.map(c => {
    // Risk Level Badge
    let badgeClass = 'unknown';
    let badgeText = 'Без оценки';
    if (c.risk_level === 'high') { badgeClass = 'high'; badgeText = 'Высокий риск'; }
    else if (c.risk_level === 'medium') { badgeClass = 'medium'; badgeText = 'Средний риск'; }
    else if (c.risk_level === 'low') { badgeClass = 'low'; badgeText = 'Низкий риск'; }

    // Risk Score / Loyalty representation
    let scoreDisplay = `<span style="color: var(--text-muted); font-size: 0.8rem;">Нет данных</span>`;
    if (c.risk_score !== null) {
      const color = c.risk_score >= 70 ? 'var(--risk-high)' : c.risk_score >= 35 ? 'var(--risk-med)' : 'var(--risk-low)';
      scoreDisplay = `
        <div class="score-flex">
          <div class="score-progress-bg">
            <div class="score-progress-fill" style="width: ${c.risk_score}%; background: ${color};"></div>
          </div>
          <div>
            <span class="score-number" style="color: ${color};">${c.risk_score.toFixed(1)}</span>
            <div style="font-size: 0.7rem; color: var(--text-muted); line-height: 1;">Лояльность: ${c.loyalty_score.toFixed(1)}</div>
          </div>
        </div>
      `;
    }

    const topReason = c.reasons && c.reasons.length > 0 ? c.reasons[0] : 'Без замечаний';

    return `
      <tr data-customer-id="${c.id}">
        <td><strong style="color: var(--text-primary); font-family: var(--font-heading); font-weight: 700;">#${c.id}</strong></td>
        <td>
          <span class="email-tag">${c.email}</span>
        </td>
        <td>
          <strong>€${c.balance_eur.toFixed(2)}</strong>
          ${c.bonusBalance > 0 ? `<div style="font-size: 0.7rem; color: ${c.bonusState === 'unlocked' ? 'var(--risk-low)' : 'var(--text-muted)'};">+€${c.bonusBalance_eur.toFixed(2)} бонус</div>` : ''}
        </td>
        <td style="color: var(--text-secondary);">€${c.totalReplenished_eur.toFixed(2)}</td>
        <td>${scoreDisplay}</td>
        <td><span class="status-badge ${badgeClass}">${badgeText}</span></td>
        <td>
          <span style="font-weight: 700; color: ${c.potential_monthly_loss_eur > 0 ? 'var(--risk-high)' : 'var(--text-muted)'};">
            €${c.potential_monthly_loss_eur.toFixed(2)}
          </span>
          <div style="font-size: 0.7rem; color: var(--text-muted);">в мес</div>
        </td>
        <td style="max-width: 260px; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.35;">
          ${topReason}
        </td>
        <td>
          <button class="btn btn-detail" data-id="${c.id}" style="padding: 0.3rem 0.65rem; font-size: 0.75rem;">
            Анализ
          </button>
        </td>
      </tr>
    `;
  });

  el.customersTbody.innerHTML = rows.join('');

  document.querySelectorAll('.btn-detail').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const cid = parseInt(btn.getAttribute('data-id'), 10);
      showCustomerDetails(cid);
    });
  });
}

// Customer Drill-Down Modal
async function showCustomerDetails(customerId) {
  try {
    const c = await apiRequest(`/api/v1/customers/${customerId}`);
    el.detailCustomerTitle.innerHTML = `Клиент #${c.id} <span style="font-weight: 400; color: var(--text-secondary); font-size: 0.95rem;">(${c.email})</span>`;

    const reasonsList = c.reasons.map(r => `<li style="margin-bottom: 0.35rem;">${r}</li>`).join('');

    const factorsCards = c.explanations.map(e => `
      <div style="background: var(--bg-card); border: 1px solid var(--border-card); padding: 0.75rem 1rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; gap: 1rem;">
        <div style="flex: 1; min-width: 0;">
          <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary);">${e.feature_name} (вес ${e.weight}%)</div>
          <div style="font-size: 0.775rem; color: var(--text-secondary); margin-top: 0.15rem;">${e.reason}</div>
        </div>
        <div style="text-align: right; flex-shrink: 0; white-space: nowrap; min-width: 90px;">
          <div style="font-family: var(--font-mono); font-weight: 700; font-size: 0.9rem; color: ${e.raw_score >= 50 ? 'var(--risk-high)' : 'var(--risk-low)'}; line-height: 1.2;">
            ${e.raw_score.toFixed(1)} б.
          </div>
          <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.15rem;">вклад: +${e.weighted_score.toFixed(1)}</div>
        </div>
      </div>
    `).join('');

    const servicesRows = c.services.map(s => `
      <tr style="border-bottom: 1px solid var(--border-subtle);">
        <td style="padding: 0.5rem 0.75rem;"><strong>${s.name}</strong></td>
        <td style="padding: 0.5rem 0.75rem; color: var(--text-secondary);">${s.paymentTerm}</td>
        <td style="padding: 0.5rem 0.75rem;">€${(s.price / 100).toFixed(2)}</td>
        <td style="padding: 0.5rem 0.75rem;">
          <span style="color: ${s.autoProlong ? 'var(--risk-low)' : 'var(--risk-high)'}; font-weight: 600;">
            ${s.autoProlong ? 'ВКЛ' : 'ВЫКЛ'}
          </span>
        </td>
        <td style="padding: 0.5rem 0.75rem;"><span class="status-badge ${s.status === 'active' ? 'low' : s.status === 'prolong_wait' ? 'high' : 'unknown'}">${s.status}</span></td>
        <td style="padding: 0.5rem 0.75rem; font-size: 0.75rem; color: var(--text-muted);">${new Date(s.expiresAt).toLocaleDateString('ru-RU')}</td>
      </tr>
    `).join('');

    const transactionsRows = c.transactions.map(t => `
      <tr style="border-bottom: 1px solid var(--border-subtle);">
        <td style="padding: 0.4rem 0.6rem;">#${t.id}</td>
        <td style="padding: 0.4rem 0.6rem; color: var(--text-secondary);">${t.type}</td>
        <td style="padding: 0.4rem 0.6rem;">€${(t.amount / 100).toFixed(2)}</td>
        <td style="padding: 0.4rem 0.6rem;">
          <span style="color: ${t.status === 'performed' ? 'var(--risk-low)' : 'var(--risk-high)'}; font-weight: 600;">
            ${t.status}
          </span>
        </td>
        <td style="padding: 0.4rem 0.6rem; font-size: 0.75rem; color: var(--text-muted);">${new Date(t.createdAt).toLocaleDateString('ru-RU')}</td>
      </tr>
    `).join('');

    el.detailCustomerBody.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.25rem;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-card); padding: 0.85rem; border-radius: var(--radius-sm);">
          <div style="font-size: 0.725rem; color: var(--text-muted); text-transform: uppercase;">Баланс аккаунта</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 0.2rem;">€${c.balance_eur.toFixed(2)}</div>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-card); padding: 0.85rem; border-radius: var(--radius-sm);">
          <div style="font-size: 0.725rem; color: var(--text-muted); text-transform: uppercase;">Всего пополнено</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 0.2rem;">€${c.totalReplenished_eur.toFixed(2)}</div>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-card); padding: 0.85rem; border-radius: var(--radius-sm);">
          <div style="font-size: 0.725rem; color: var(--text-muted); text-transform: uppercase;">Risk Score</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: ${c.risk_score >= 70 ? 'var(--risk-high)' : c.risk_score >= 35 ? 'var(--risk-med)' : 'var(--risk-low)'}; margin-top: 0.2rem;">
            ${c.risk_score !== null ? c.risk_score.toFixed(1) : 'Н/Д'}
          </div>
        </div>
        <div style="background: var(--bg-card); border: 1px solid var(--border-card); padding: 0.85rem; border-radius: var(--radius-sm);">
          <div style="font-size: 0.725rem; color: var(--text-muted); text-transform: uppercase;">Потери MRR / мес</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: var(--risk-high); margin-top: 0.2rem;">€${c.potential_monthly_loss_eur.toFixed(2)}</div>
        </div>
      </div>

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.875rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.4rem;">Диагностика факторов риска:</h3>
        <ul style="padding-left: 1.25rem; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
          ${reasonsList}
        </ul>
      </div>

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.875rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem;">Вклад признаков в модель:</h3>
        ${factorsCards}
      </div>

      <div style="margin-bottom: 1.25rem;">
        <h3 style="font-size: 0.875rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem;">Подключенные серверы и услуги (${c.services.length}):</h3>
        <div style="border: 1px solid var(--border-card); border-radius: var(--radius-sm); overflow: hidden;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; background: var(--bg-card);">
            <thead>
              <tr style="background: var(--bg-card-hover); color: var(--text-muted); text-align: left;">
                <th style="padding: 0.5rem 0.75rem;">Услуга</th>
                <th style="padding: 0.5rem 0.75rem;">Период</th>
                <th style="padding: 0.5rem 0.75rem;">Тариф</th>
                <th style="padding: 0.5rem 0.75rem;">Автопродление</th>
                <th style="padding: 0.5rem 0.75rem;">Статус</th>
                <th style="padding: 0.5rem 0.75rem;">Окончание</th>
              </tr>
            </thead>
            <tbody>${servicesRows || '<tr><td colspan="6" style="padding: 1rem; text-align: center; color: var(--text-muted);">Нет услуг</td></tr>'}</tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 style="font-size: 0.875rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem;">История транзакций (${c.transactions.length}):</h3>
        <div style="border: 1px solid var(--border-card); border-radius: var(--radius-sm); overflow: hidden; max-height: 160px; overflow-y: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.8rem; background: var(--bg-card);">
            <thead>
              <tr style="background: var(--bg-card-hover); color: var(--text-muted); text-align: left;">
                <th style="padding: 0.4rem 0.6rem;">ID</th>
                <th style="padding: 0.4rem 0.6rem;">Тип</th>
                <th style="padding: 0.4rem 0.6rem;">Сумма</th>
                <th style="padding: 0.4rem 0.6rem;">Статус</th>
                <th style="padding: 0.4rem 0.6rem;">Дата</th>
              </tr>
            </thead>
            <tbody>${transactionsRows || '<tr><td colspan="5" style="padding: 1rem; text-align: center; color: var(--text-muted);">Нет транзакций</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `;

    el.modalCustomerDetail.classList.add('active');
  } catch (err) {
    showToast(`Ошибка открытия карточки: ${err.message}`, 'error');
  }
}

// High-Res Canvas Charts (Crystal-Clear Pixel-Aligned Rendering)
function renderChurnTimelineChart(dataPoints) {
  const canvas = el.churnTimelineCanvas;
  if (!canvas || !dataPoints) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  const rect = canvas.getBoundingClientRect();
  const w = Math.round(rect.width || canvas.clientWidth || 600);
  const h = Math.round(rect.height || canvas.clientHeight || 175);
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.resetTransform();
  ctx.scale(dpr, dpr);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  ctx.clearRect(0, 0, w, h);

  const barCount = dataPoints.length;
  if (barCount === 0) return;

  const padLeft = 35;
  const padBottom = 44;
  const padTop = 26;
  const chartW = w - padLeft - 15;
  const chartH = h - padBottom - padTop;

  const maxVal = Math.max(...dataPoints.map(d => Math.max(d.fact_deleted_services, d.forecast_at_risk_services)), 8);
  const barWidth = Math.min(42, Math.round((chartW / barCount) * 0.48));

  // Dashed Grid lines
  ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.07)';
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  for (let step = 0; step <= 3; step++) {
    const yLine = Math.round(padTop + (chartH / 3) * step);
    ctx.beginPath();
    ctx.moveTo(padLeft, yLine);
    ctx.lineTo(padLeft + chartW, yLine);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Base X Axis
  ctx.strokeStyle = isDark ? '#272730' : '#e2e8f0';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padLeft, padTop + chartH);
  ctx.lineTo(padLeft + chartW, padTop + chartH);
  ctx.stroke();

  dataPoints.forEach((pt, i) => {
    const x = Math.round(padLeft + (i + 0.5) * (chartW / barCount));
    const val = pt.fact_deleted_services > 0 ? pt.fact_deleted_services : pt.forecast_at_risk_services;
    const barH = Math.max(4, Math.round((val / maxVal) * chartH));
    const y = Math.round(padTop + chartH - barH);

    const isFact = pt.fact_deleted_services > 0;

    // Gradient bar fill (Orange-centric Aéza styling)
    const grad = ctx.createLinearGradient(0, y, 0, padTop + chartH);
    if (isFact) {
      grad.addColorStop(0, '#f43f5e');
      grad.addColorStop(1, '#991b1b');
    } else {
      grad.addColorStop(0, '#FF6200');
      grad.addColorStop(1, isDark ? '#9a3412' : '#ea580c');
    }

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(Math.round(x - barWidth / 2), y, barWidth, barH, [4, 4, 0, 0]);
    ctx.fill();

    // Value label
    ctx.fillStyle = isDark ? '#FFFFFF' : '#09090b';
    ctx.font = '700 12px "Exo 2", system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(`${val} усл`, x, y - 4);

    // X Axis Label
    ctx.fillStyle = isDark ? '#a1a1aa' : '#475569';
    ctx.font = '600 11px Inter, system-ui, sans-serif';
    ctx.textBaseline = 'top';
    const label = pt.label.replace('Исторический факт: ', 'Факт: ').replace(/Прогноз (\d+) дней:\s*/, '$1д: ');
    ctx.fillText(label, x, padTop + chartH + 10);

    if (pt.forecast_lost_revenue_eur > 0) {
      ctx.fillStyle = '#FF6200';
      ctx.font = '700 11px "Exo 2", system-ui, sans-serif';
      ctx.fillText(`€${pt.forecast_lost_revenue_eur.toFixed(0)}`, x, padTop + chartH + 26);
    }
  });
}

function renderRiskDistributionChart(summary) {
  const canvas = el.riskDistributionCanvas;
  if (!canvas || !summary) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  const rect = canvas.getBoundingClientRect();
  const w = Math.round(rect.width || canvas.clientWidth || 300);
  const h = Math.round(rect.height || canvas.clientHeight || 175);
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.resetTransform();
  ctx.scale(dpr, dpr);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  ctx.clearRect(0, 0, w, h);

  const total = summary.total_customers || 1;
  const segments = [
    { label: 'Высокий', count: summary.high_risk_customers, color: '#f43f5e' },
    { label: 'Средний', count: summary.medium_risk_customers, color: '#FF6200' },
    { label: 'Низкий', count: summary.low_risk_customers, color: '#16a34a' },
    { label: 'Без оценки', count: summary.unknown_risk_customers, color: '#9333ea' }
  ];

  const centerX = Math.round(w * 0.32);
  const centerY = Math.round(h * 0.5);
  const radius = Math.min(centerX, centerY) - 12;
  const innerRadius = radius * 0.65;

  let startAngle = -Math.PI / 2;

  segments.forEach(seg => {
    const sliceAngle = (seg.count / total) * Math.PI * 2;
    if (sliceAngle > 0) {
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
      ctx.arc(centerX, centerY, innerRadius, startAngle + sliceAngle, startAngle, true);
      ctx.closePath();
      ctx.fillStyle = seg.color;
      ctx.fill();
      startAngle += sliceAngle;
    }
  });

  // Center KPI
  ctx.fillStyle = isDark ? '#FFFFFF' : '#09090b';
  ctx.font = '800 19px "Exo 2", system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(total.toString(), centerX, centerY - 8);
  ctx.font = '600 11px Inter, system-ui, sans-serif';
  ctx.fillStyle = isDark ? '#71717a' : '#64748b';
  ctx.fillText('клиентов', centerX, centerY + 12);

  // Legend List
  const legendX = Math.round(w * 0.62);
  let legendY = 25;
  segments.forEach(seg => {
    ctx.fillStyle = seg.color;
    ctx.beginPath();
    ctx.arc(legendX + 4, legendY + 5, 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = isDark ? '#e4e4e7' : '#334155';
    ctx.font = '600 12px Inter, system-ui, sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const pct = total > 0 ? ((seg.count / total) * 100).toFixed(0) : 0;
    ctx.fillText(`${seg.label}: ${seg.count} (${pct}%)`, legendX + 14, legendY + 5);
    legendY += 26;
  });
}


// Model Settings Modal
async function loadSettings() {
  try {
    const s = await apiRequest('/api/v1/model/settings');
    state.settings = s;
    updateSettingsSliders(s);
  } catch (err) {
    console.error('Ошибка загрузки настроек:', err);
  }
}

function updateSettingsSliders(s) {
  document.getElementById('input-auto-prolong').value = s.w_auto_prolong_off;
  document.getElementById('val-auto-prolong').innerText = s.w_auto_prolong_off;

  document.getElementById('input-insufficient-funds').value = s.w_insufficient_funds;
  document.getElementById('val-insufficient-funds').innerText = s.w_insufficient_funds;

  document.getElementById('input-prolong-wait').value = s.w_prolong_wait;
  document.getElementById('val-prolong-wait').innerText = s.w_prolong_wait;

  document.getElementById('input-failed-tx').value = s.w_failed_tx_ratio;
  document.getElementById('val-failed-tx').innerText = s.w_failed_tx_ratio;

  document.getElementById('input-thresh-high').value = s.threshold_high;
  document.getElementById('val-thresh-high').innerText = s.threshold_high;

  document.getElementById('input-thresh-med').value = s.threshold_medium;
  document.getElementById('val-thresh-med').innerText = s.threshold_medium;

  document.getElementById('input-forecast-days').value = s.forecast_days;
}

// Live SSE Stream
function connectSSE() {
  if (state.sseEventSource) {
    state.sseEventSource.close();
  }

  const sse = new EventSource('/api/v1/events');
  state.sseEventSource = sse;

  sse.onopen = () => {
    if (el.liveStatusText) el.liveStatusText.innerText = 'Живое обновление (SSE)';
  };

  sse.addEventListener('recalculated', async () => {
    showToast('Показатели пересчитаны в реальном времени', 'success');
    await Promise.all([loadSummary(), loadCustomers()]);
  });

  sse.onerror = () => {
    if (el.liveStatusText) el.liveStatusText.innerText = 'Переподключение...';
  };
}

// Event Listeners Setup
// Theme Management (Light: aeza.net white/black, Dark: my.aeza.net black/orange)
function initTheme() {
  const savedTheme = localStorage.getItem('aeza_theme') || 'light';
  setTheme(savedTheme);
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('aeza_theme', theme);
  if (el.themeStatusText) {
    el.themeStatusText.innerText = theme === 'dark' ? 'Тёмная' : 'Светлая';
  }
  // Redraw charts with active theme palette
  if (state.summary) {
    renderRiskDistributionChart(state.summary);
    if (state.summary.churn_timeline) {
      renderChurnTimelineChart(state.summary.churn_timeline);
    }
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  setTheme(current === 'dark' ? 'light' : 'dark');
}

function setupEventListeners() {
  if (el.btnThemeToggle) {
    el.btnThemeToggle.addEventListener('click', toggleTheme);
  }
  // Sorting table headers
  el.tableHeaders.forEach(th => {
    th.addEventListener('click', () => {
      const field = th.getAttribute('data-sort');
      if (state.currentSort === field) {
        state.currentSortOrder = state.currentSortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        state.currentSort = field;
        state.currentSortOrder = 'desc';
      }

      el.tableHeaders.forEach(h => {
        const icon = h.querySelector('.sort-arrow');
        if (h.getAttribute('data-sort') === state.currentSort) {
          h.classList.add('active-sort');
          icon.innerText = state.currentSortOrder === 'asc' ? '▲' : '▼';
        } else {
          h.classList.remove('active-sort');
          icon.innerText = '⇅';
        }
      });

      loadCustomers();
    });
  });

  // Filter Buttons
  el.filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      el.filterButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentFilter = btn.getAttribute('data-filter');
      loadCustomers();
    });
  });

  // Search input debounced
  let searchTimeout = null;
  el.searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.searchQuery = e.target.value.trim();
      loadCustomers();
    }, 250);
  });

  // Settings modal
  el.btnOpenSettings.addEventListener('click', () => el.modalSettings.classList.add('active'));
  el.btnCloseSettings.addEventListener('click', () => el.modalSettings.classList.remove('active'));

  // Slider bindings
  const bindSlider = (inputSlug) => {
    const input = document.getElementById(`input-${inputSlug}`);
    const label = document.getElementById(`val-${inputSlug}`);
    if (input && label) {
      input.addEventListener('input', () => label.innerText = input.value);
    }
  };
  bindSlider('auto-prolong');
  bindSlider('insufficient-funds');
  bindSlider('prolong-wait');
  bindSlider('failed-tx');
  bindSlider('thresh-high');
  bindSlider('thresh-med');

  // Submit model settings
  el.settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      w_auto_prolong_off: parseFloat(document.getElementById('input-auto-prolong').value),
      w_insufficient_funds: parseFloat(document.getElementById('input-insufficient-funds').value),
      w_prolong_wait: parseFloat(document.getElementById('input-prolong-wait').value),
      w_failed_tx_ratio: parseFloat(document.getElementById('input-failed-tx').value),
      threshold_high: parseFloat(document.getElementById('input-thresh-high').value),
      threshold_medium: parseFloat(document.getElementById('input-thresh-med').value),
      forecast_days: parseInt(document.getElementById('input-forecast-days').value, 10)
    };

    try {
      await apiRequest('/api/v1/model/settings', { method: 'PATCH', body: payload });
      showToast('Настройки модели успешно сохранены', 'success');
      el.modalSettings.classList.remove('active');
      await Promise.all([loadSummary(), loadCustomers()]);
    } catch (err) {
      showToast(`Ошибка сохранения: ${err.message}`, 'error');
    }
  });

  // Reset settings
  document.getElementById('btn-reset-settings').addEventListener('click', () => {
    updateSettingsSliders({
      w_auto_prolong_off: 35,
      w_insufficient_funds: 30,
      w_prolong_wait: 25,
      w_failed_tx_ratio: 10,
      threshold_high: 70,
      threshold_medium: 35,
      forecast_days: 30
    });
  });

  // Snapshot modal
  el.btnOpenSnapshot.addEventListener('click', () => el.modalSnapshot.classList.add('active'));
  el.btnCloseSnapshot.addEventListener('click', () => el.modalSnapshot.classList.remove('active'));
  el.btnCancelSnapshot.addEventListener('click', () => el.modalSnapshot.classList.remove('active'));

  el.snapshotFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        el.snapshotTextInput.value = event.target.result;
      };
      reader.readAsText(file);
    }
  });

  el.snapshotForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const rawJson = el.snapshotTextInput.value.trim();
    if (!rawJson) {
      showToast('Выберите файл или вставьте JSON', 'error');
      return;
    }

    try {
      const snapshot = JSON.parse(rawJson);
      const res = await apiRequest('/api/v1/source/snapshot', { method: 'PUT', body: snapshot });
      showToast(`Снимок обновлен: ${res.accounts_count} аккаунтов, ${res.services_count} услуг`, 'success');
      el.modalSnapshot.classList.remove('active');
      await Promise.all([loadSummary(), loadCustomers()]);
    } catch (err) {
      showToast(`Ошибка загрузки снимка: ${err.message}`, 'error');
    }
  });

  // Customer Detail close

  const btnResetSnapshot = document.getElementById('btn-reset-snapshot');
  if (btnResetSnapshot) {
    btnResetSnapshot.addEventListener('click', async () => {
      try {
        const res = await apiRequest('/api/v1/source/reset', { method: 'POST' });
        showToast('Данные сброшены к data.json (' + res.accounts_count + ' аккаунтов)', 'success');
        el.modalSnapshot.classList.remove('active');
        await Promise.all([loadSummary(), loadCustomers()]);
      } catch (err) {
        showToast('Ошибка сброса: ' + err.message, 'error');
      }
    });
  }
  
  // Close modals on clicking background
  [el.modalSettings, el.modalSnapshot, el.modalCustomerDetail].forEach(modal => {
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
      });
    }
  });

  el.btnCloseDetail.addEventListener('click', () => el.modalCustomerDetail.classList.remove('active'));

  // Auth Tabs (Basic vs OIDC)
  el.tabBtnBasic.addEventListener('click', () => {
    el.tabBtnBasic.classList.remove('btn-ghost');
    el.tabBtnBasic.style.background = 'var(--bg-card)';
    el.tabBtnBasic.style.color = '#fff';
    el.tabBtnOidc.classList.add('btn-ghost');
    el.tabBtnOidc.style.background = 'transparent';
    el.tabBtnOidc.style.color = 'var(--text-secondary)';
    el.authTabBasic.style.display = 'block';
    el.authTabOidc.style.display = 'none';
  });

  el.tabBtnOidc.addEventListener('click', () => {
    el.tabBtnOidc.classList.remove('btn-ghost');
    el.tabBtnOidc.style.background = 'var(--bg-card)';
    el.tabBtnOidc.style.color = '#fff';
    el.tabBtnBasic.classList.add('btn-ghost');
    el.tabBtnBasic.style.background = 'transparent';
    el.tabBtnBasic.style.color = 'var(--text-secondary)';
    el.authTabOidc.style.display = 'block';
    el.authTabBasic.style.display = 'none';
  });

  // Quick fill demo credentials (if element present)
  if (el.btnQuickFillCreds) {
    el.btnQuickFillCreds.addEventListener('click', () => {
      el.loginUsername.value = 'admin';
      el.loginPassword.value = 'aeza2026';
    });
  }

  // Basic Login Form
  el.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = el.loginUsername.value.trim();
    const password = el.loginPassword.value.trim();
    try {
      const auth = await apiRequest('/api/v1/auth/login', {
        method: 'POST',
        body: { username, password }
      });
      state.token = auth.token;
      if (typeof localStorage !== 'undefined') localStorage.setItem('aeza_token', auth.token);
      setAuthenticatedUser(auth.user);
      showToast('Успешный вход по логину и паролю', 'success');
      initDashboard();
    } catch (err) {
      showToast(`Ошибка входа: ${err.message}`, 'error');
    }
  });

  // OIDC SSO Confirm Button
  el.btnOidcConfirm.addEventListener('click', async () => {
    try {
      const auth = await apiRequest('/api/v1/auth/oidc/mock-login');
      state.token = auth.token;
      if (typeof localStorage !== 'undefined') localStorage.setItem('aeza_token', auth.token);
      setAuthenticatedUser(auth.user);
      showToast('Авторизация через Aéza ID (OIDC SSO) успешно выполнена!', 'success');
      initDashboard();
    } catch (err) {
      showToast(`Ошибка OIDC: ${err.message}`, 'error');
    }
  });

  // Logout
  el.btnLogout.addEventListener('click', async () => {
    try {
      await apiRequest('/api/v1/auth/logout', { method: 'POST' });
    } catch (_) {}
    state.token = null;
    state.currentUser = null;
    if (typeof localStorage !== 'undefined') localStorage.removeItem('aeza_token');
    showToast('Сессия завершена');
    showAuthModal();
  });
}

// Window init
window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setupEventListeners();
  checkAuth();
});
