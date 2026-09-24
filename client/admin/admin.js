(() => {
  const root = document.documentElement;
  const i18n = window.RoleVerseI18n;
  const routes = ['overview', 'users', 'providers', 'usage', 'settings', 'audit'];
  const storage = {
    get(key, fallback) {
      try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : value;
      } catch (error) {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, value);
      } catch (error) {
        return false;
      }
      return true;
    },
  };
  const state = {
    locale: storage.get('roleverse-locale', 'en'),
    theme: storage.get('roleverse-theme', 'light'),
    route: 'overview',
    user: null,
    requestId: 0,
    dialogTarget: null,
    dialogMode: 'ban',
    providerId: null,
  };
  const select = (selector, parent = document) => parent.querySelector(selector);
  const selectAll = (selector, parent = document) => Array.from(parent.querySelectorAll(selector));
  const t = (key) => i18n[state.locale]?.[key] || i18n.en[key] || key;
  const isPersian = () => state.locale === 'fa';
  const formatDate = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat(isPersian() ? 'fa-IR' : 'en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  };
  const formatNumber = (value) => new Intl.NumberFormat(isPersian() ? 'fa-IR' : 'en-US').format(Number(value || 0));
  const formatCost = (micro, pricingAvailable = true) => {
    if (!pricingAvailable) return t('adminUnpriced');
    return `$${(Number(micro || 0) / 1_000_000).toFixed(4)}`;
  };
  const statusLabel = (status) => {
    const labels = {
      active: t('adminActiveStatus'),
      banned: t('adminBannedStatus'),
      enabled: t('adminEnabled'),
      disabled: t('adminDisabled'),
      degraded: t('adminDegraded'),
      complete: t('adminEnabled'),
      failed: t('adminDegraded'),
      cancelled: t('adminBannedStatus'),
      queued: t('adminLoading'),
      streaming: t('adminLoading'),
    };
    return labels[status] || status;
  };
  const icon = (id) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', `#${id}`);
    svg.append(use);
    return svg;
  };
  const text = (value) => document.createTextNode(String(value ?? ''));
  const element = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = String(value);
    return node;
  };
  const request = async (path, options = {}) => {
    try {
      const response = await fetch(path, {
        ...options,
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          ...(options.body ? { 'Content-Type': 'application/json' } : {}),
          ...(options.headers || {}),
        },
      });
      let data = null;
      const body = await response.text();
      if (body) {
        try {
          data = JSON.parse(body);
        } catch (error) {
          data = null;
        }
      }
      return { ok: response.ok, status: response.status, data };
    } catch (error) {
      return { ok: false, status: 0, data: null, error };
    }
  };
  const showToast = (message) => {
    const region = select('#admin-toast-region');
    const toast = element('div', 'admin-toast', message);
    region.append(toast);
    window.setTimeout(() => toast.remove(), 3000);
  };
  const setUpdated = () => {
    select('#admin-updated').textContent = `${t('adminLastUpdated')}: ${formatDate(new Date().toISOString())}`;
  };
  const applyTranslations = () => {
    root.lang = state.locale;
    root.dir = isPersian() ? 'rtl' : 'ltr';
    document.title = `${t('adminWorkspace')} — RoleVerse`;
    selectAll('[data-i18n]').forEach((node) => {
      node.textContent = t(node.dataset.i18n);
    });
    selectAll('[data-i18n-placeholder]').forEach((node) => {
      node.setAttribute('placeholder', t(node.dataset.i18nPlaceholder));
    });
    selectAll('[data-i18n-aria]').forEach((node) => {
      node.setAttribute('aria-label', t(node.dataset.i18nAria));
    });
    select('#admin-language-label').textContent = isPersian() ? 'فا' : 'EN';
    select('#admin-breadcrumb').textContent = t(`admin${state.route[0].toUpperCase()}${state.route.slice(1)}`);
    setUpdated();
  };
  const setTheme = () => {
    root.dataset.theme = state.theme;
    storage.set('roleverse-theme', state.theme);
  };
  const setRoute = (route) => {
    const nextRoute = routes.includes(route) ? route : 'overview';
    state.route = nextRoute;
    selectAll('[data-admin-page]').forEach((page) => {
      const active = page.dataset.adminPage === nextRoute;
      page.hidden = !active;
      page.classList.toggle('is-visible', active);
    });
    selectAll('[data-admin-route]').forEach((button) => {
      button.classList.toggle('is-active', button.dataset.adminRoute === nextRoute);
    });
    select('#admin-breadcrumb').textContent = t(`admin${nextRoute[0].toUpperCase()}${nextRoute.slice(1)}`);
    if (window.location.hash !== `#/${nextRoute}`) {
      window.history.replaceState(null, '', `#/${nextRoute}`);
    }
    select('#admin-content').focus({ preventScroll: true });
    void loadRoute();
  };
  const setLoading = (target, message = t('adminLoading')) => {
    const node = select(target);
    node.replaceChildren(element('div', 'admin-loading-state', message));
  };
  const setEmpty = (target, message = t('adminNoData')) => {
    const node = select(target);
    node.replaceChildren(element('div', 'admin-empty-state', message));
  };
  const table = (headers, rows) => {
    const wrap = document.createDocumentFragment();
    const node = element('table', 'admin-table');
    const head = element('thead');
    const headRow = element('tr');
    headers.forEach((header) => headRow.append(element('th', '', header)));
    head.append(headRow);
    const body = element('tbody');
    rows.forEach((cells) => {
      const row = element('tr');
      cells.forEach((cell) => {
        const node = document.createElement('td');
        if (cell instanceof Node) node.append(cell);
        else node.textContent = String(cell ?? '—');
        row.append(node);
      });
      body.append(row);
    });
    node.append(head, body);
    wrap.append(node);
    return wrap;
  };
  const metricCard = (label, value, note, iconId) => {
    const card = element('article', 'admin-metric-card');
    const heading = element('div', 'admin-metric-label');
    heading.append(element('span', '', label), icon(iconId));
    card.append(heading, element('strong', 'admin-metric-value', value), element('span', 'admin-metric-note', note));
    return card;
  };
  const loadOverview = async () => {
    const target = '#admin-metric-grid';
    const result = await request('/api/v1/admin/overview');
    if (!result.ok) throw new Error('overview');
    const metrics = result.data.metrics;
    const terminal = metrics.generations_complete + metrics.generations_total - metrics.generations_complete - metrics.generations_active;
    const completion = terminal > 0 ? `${Math.round((metrics.generations_complete / terminal) * 100)}%` : '—';
    const grid = document.createDocumentFragment();
    grid.append(
      metricCard(t('adminActiveUsers'), formatNumber(metrics.users_active), t('adminUsersCaption'), 'admin-icon-users'),
      metricCard(t('adminGenerationRuns'), formatNumber(metrics.generations_total), t('adminGenerationRuns'), 'admin-icon-overview'),
      metricCard(t('adminCompletionRate'), completion, t('adminUsageCaption'), 'admin-icon-usage'),
      metricCard(t('adminEstimatedCost'), formatCost(metrics.total_cost_micro, metrics.pricing_reported > 0), t('adminUsageCaption'), 'admin-icon-provider'),
    );
    select(target).replaceChildren(grid);
    const audit = document.createDocumentFragment();
    if (!result.data.recent_audit.length) audit.append(element('div', 'admin-empty-state', t('adminNoAudit')));
    result.data.recent_audit.forEach((event) => {
      const item = element('div', 'admin-event-item');
      const copy = element('div', 'admin-event-copy');
      copy.append(element('strong', '', event.action), element('span', '', `${event.entity_type} · ${event.entity_id.slice(0, 8)}`));
      item.append(element('span', 'admin-event-dot'), copy, element('time', 'admin-event-time', formatDate(event.created_at)));
      audit.append(item);
    });
    select('#admin-overview-audit').replaceChildren(audit);
    const providers = await request('/api/v1/admin/providers');
    const providerList = document.createDocumentFragment();
    if (!providers.ok || !providers.data.length) providerList.append(element('div', 'admin-empty-state', t('adminNoData')));
    (providers.ok ? providers.data : []).forEach((provider) => {
      const item = element('div', 'admin-health-item');
      const copy = element('div', 'admin-health-copy');
      copy.append(element('strong', '', provider.name), element('span', '', provider.base_url || provider.runtime_mode));
      const status = element('span', `admin-health-status is-${provider.status}`, statusLabel(provider.status));
      item.append(element('span', 'admin-health-dot'), copy, status);
      providerList.append(item);
    });
    select('#admin-overview-providers').replaceChildren(providerList);
  };
  const renderUsers = async () => {
    const target = '#admin-users-table';
    setLoading(target);
    const params = new URLSearchParams();
    const search = select('#admin-user-search').value.trim();
    const status = select('#admin-user-status').value;
    const role = select('#admin-user-role').value;
    if (search) params.set('search', search);
    if (status) params.set('status', status);
    if (role) params.set('role', role);
    const result = await request(`/api/v1/admin/users?${params.toString()}`);
    if (!result.ok) {
      setEmpty(target, t('adminRequestFailed'));
      return;
    }
    if (!result.data.items.length) {
      setEmpty(target, t('adminNoData'));
      return;
    }
    const rows = result.data.items.map((user) => {
      const statusNode = element('span', `admin-status-pill is-${user.status}`, statusLabel(user.status));
      const actions = element('div', 'admin-provider-actions');
      const banAction = element('button', 'admin-table-action', user.status === 'banned' ? t('adminUnban') : t('adminBan'));
      banAction.type = 'button';
      banAction.dataset.action = user.status === 'banned' ? 'unban' : 'ban';
      banAction.dataset.userId = user.id;
      banAction.dataset.userName = user.display_name || user.phone_masked;
      actions.append(banAction);
      if (user.id !== state.user?.id) {
        const roleAction = element('button', 'admin-table-action', user.role === 'admin' ? t('adminDemote') : t('adminPromote'));
        roleAction.type = 'button';
        roleAction.dataset.action = 'role';
        roleAction.dataset.userId = user.id;
        roleAction.dataset.userName = user.display_name || user.phone_masked;
        roleAction.dataset.nextRole = user.role === 'admin' ? 'user' : 'admin';
        actions.append(roleAction);
      }
      return [user.display_name || '—', user.phone_masked, user.role === 'admin' ? t('adminAdminRole') : t('adminUserRole'), statusNode, formatDate(user.last_login_at), actions];
    });
    select(target).replaceChildren(table([t('adminDisplayName'), t('adminPhone'), t('adminRole'), t('adminStatus'), t('adminLastLogin'), t('adminActions')], rows));
  };
  const renderProviders = async () => {
    const target = '#admin-providers-list';
    setLoading(target);
    const result = await request('/api/v1/admin/providers');
    if (!result.ok) {
      setEmpty(target, t('adminRequestFailed'));
      return;
    }
    if (!result.data.length) {
      setEmpty(target, t('adminNoData'));
      select('#admin-models-table').replaceChildren();
      return;
    }
    const list = document.createDocumentFragment();
    result.data.forEach((provider) => {
      const card = element('div', 'admin-provider-card');
      const copy = element('div', 'admin-provider-copy');
      copy.append(element('strong', '', provider.name), element('span', '', `${provider.slug} · ${provider.base_url || provider.runtime_mode}`));
      const status = element('span', `admin-status-pill is-${provider.status}`, statusLabel(provider.status));
      const source = element('span', 'admin-provider-status', provider.secret_source === 'none' ? t('adminNone') : provider.secret_source);
      card.append(copy, element('div', 'admin-provider-actions', ''));
      card.lastElementChild.append(status, source);
      list.append(card);
    });
    select(target).replaceChildren(list);
    const firstProvider = result.data[0];
    state.providerId = firstProvider.id;
    const models = await request(`/api/v1/admin/providers/${encodeURIComponent(firstProvider.id)}/models`);
    if (!models.ok || !models.data.length) {
      setEmpty('#admin-models-table', t('adminNoData'));
      return;
    }
    const rows = models.data.map((model) => [model.display_name || model.name, model.name, model.enabled ? t('adminEnabled') : t('adminDisabled'), formatNumber(model.context_window), formatNumber(model.max_output_tokens), formatCost(model.input_price_micro_per_million, model.pricing_available), formatCost(model.output_price_micro_per_million, model.pricing_available)]);
    select('#admin-models-table').replaceChildren(table([t('adminModelName'), t('adminModel'), t('adminStatus'), t('adminContextWindow'), t('adminOutputLimit'), t('adminInputPrice'), t('adminOutputPrice')], rows));
  };
  const renderUsage = async () => {
    const target = '#admin-usage-table';
    setLoading(target);
    const result = await request('/api/v1/admin/usage?limit=100');
    if (!result.ok) {
      setEmpty(target, t('adminRequestFailed'));
      return;
    }
    if (!result.data.items.length) {
      setEmpty(target, t('adminNoData'));
      return;
    }
    const rows = result.data.items.map((run) => {
      const usage = run.usage_available ? `${formatNumber(run.input_tokens)} / ${formatNumber(run.output_tokens)}` : t('adminUsageUnavailable');
      const cost = run.pricing_available ? formatCost(run.total_cost_micro) : t('adminUnpriced');
      return [formatDate(run.created_at), run.run_id.slice(0, 8), run.user_id.slice(0, 8), run.provider_name, run.model_name, statusLabel(run.status), usage, cost, run.finish_reason || '—'];
    });
    select(target).replaceChildren(table([t('adminTimestamp'), t('adminRunId'), t('adminUserRef'), t('adminProvider'), t('adminModel'), t('adminStatus'), t('adminUsage'), t('adminTotalCost'), t('adminFinishReason')], rows));
  };
  const renderSettings = async () => {
    const target = '#admin-settings-form';
    setLoading(target, t('adminLoading'));
    const result = await request('/api/v1/admin/settings');
    if (!result.ok) {
      setEmpty(target, t('adminRequestFailed'));
      return;
    }
    const values = Object.fromEntries(result.data.map((setting) => [setting.key, setting.value]));
    const form = select('#admin-settings-form');
    form.replaceChildren();
    const grid = element('div', 'admin-settings-grid');
    [
      ['generation_rate_limit_per_user', t('adminPerUserLimit')],
      ['generation_rate_limit_global', t('adminGlobalLimit')],
      ['generation_rate_limit_window_seconds', t('adminWindowSeconds')],
      ['generation_max_output_tokens', t('adminOutputLimit')],
    ].forEach(([key, label]) => {
      const field = element('label');
      field.append(element('span', '', label));
      const input = element('input');
      input.name = key;
      input.type = 'number';
      input.value = values[key] ?? '';
      field.append(input);
      grid.append(field);
    });
    const maintenance = element('label', 'admin-check-field');
    const checkbox = element('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'maintenance_mode';
    checkbox.checked = values.maintenance_mode === true;
    maintenance.append(checkbox, element('span', '', t('adminMaintenanceMode')));
    grid.append(maintenance);
    const actions = element('div', 'admin-form-actions');
    const submit = element('button', 'primary-button', t('adminSave'));
    submit.type = 'submit';
    actions.append(submit, element('span', 'admin-form-message'));
    form.append(grid, actions);
    const readonly = select('#admin-readonly-settings');
    const readOnlyValues = [[t('adminProvider'), 'Environment / mock-first'], [t('adminSecretSource'), t('adminNone')], [t('adminProviderHealth'), t('adminNoData')]];
    const readOnlyFragment = document.createDocumentFragment();
    readOnlyValues.forEach(([label, value]) => {
      const row = element('div', 'admin-readonly-item');
      row.append(element('span', 'admin-readonly-copy', label), element('strong', '', value));
      readOnlyFragment.append(row);
    });
    readonly.replaceChildren(readOnlyFragment);
  };
  const renderAudit = async () => {
    const target = '#admin-audit-table';
    setLoading(target);
    const result = await request('/api/v1/admin/audit?limit=100');
    if (!result.ok) {
      setEmpty(target, t('adminRequestFailed'));
      return;
    }
    if (!result.data.length) {
      setEmpty(target, t('adminNoAudit'));
      return;
    }
    const rows = result.data.map((event) => [formatDate(event.created_at), event.actor_user_id?.slice(0, 8) || t('adminNone'), event.action, `${event.entity_type} · ${event.entity_id.slice(0, 8)}`]);
    select(target).replaceChildren(table([t('adminTimestamp'), t('adminAuditActor'), t('adminAuditAction'), t('adminAuditTarget')], rows));
  };
  const loadRoute = async () => {
    const requestId = ++state.requestId;
    const access = select('#admin-access-state');
    if (!state.user || state.user.role !== 'admin') {
      access.hidden = false;
      return;
    }
    access.hidden = true;
    try {
      if (state.route === 'overview') await loadOverview();
      if (state.route === 'users') await renderUsers();
      if (state.route === 'providers') await renderProviders();
      if (state.route === 'usage') await renderUsage();
      if (state.route === 'settings') await renderSettings();
      if (state.route === 'audit') await renderAudit();
    } catch (error) {
      if (requestId === state.requestId) showToast(t('adminRequestFailed'));
    }
    if (requestId === state.requestId) setUpdated();
  };
  const openDialog = (user, mode) => {
    state.dialogTarget = user;
    state.dialogMode = mode;
    const title = select('#admin-dialog-title');
    const description = select('#admin-dialog-description');
    const reason = select('#admin-reason-field');
    title.textContent = mode === 'ban' ? t('adminBan') : t('adminUnban');
    description.textContent = mode === 'ban' ? `${t('adminBan')}: ${user.display_name || user.phone_masked}` : `${t('adminUnban')}: ${user.display_name || user.phone_masked}`;
    reason.hidden = mode !== 'ban';
    select('#admin-ban-reason').value = '';
    select('#admin-ban-reason').required = mode === 'ban';
    select('#admin-dialog-error').textContent = '';
    const dialog = select('#admin-action-dialog');
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    window.setTimeout(() => (mode === 'ban' ? select('#admin-ban-reason') : select('#admin-dialog-cancel')).focus(), 30);
  };
  const closeDialog = () => {
    const dialog = select('#admin-action-dialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  };
  const submitDialog = async (event) => {
    event.preventDefault();
    if (!state.dialogTarget) return;
    const button = select('#admin-dialog-submit');
    button.disabled = true;
    select('#admin-dialog-error').textContent = '';
    const path = `/api/v1/admin/users/${encodeURIComponent(state.dialogTarget.id)}/${state.dialogMode === 'ban' ? 'ban' : 'unban'}`;
    const result = await request(path, { method: 'POST', ...(state.dialogMode === 'ban' ? { body: JSON.stringify({ reason: select('#admin-ban-reason').value.trim() }) } : {}) });
    button.disabled = false;
    if (!result.ok) {
      select('#admin-dialog-error').textContent = result.status === 403 ? t('adminForbidden') : t('adminRequestFailed');
      return;
    }
    closeDialog();
    showToast(t('adminSettingsSaved'));
    await renderUsers();
  };
  const submitModel = async (event) => {
    event.preventDefault();
    if (!state.providerId) return;
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    values.context_window = Number(values.context_window);
    values.max_output_tokens = Number(values.max_output_tokens);
    values.input_price_micro_per_million = Number(values.input_price_micro_per_million);
    values.output_price_micro_per_million = Number(values.output_price_micro_per_million);
    values.pricing_available = form.elements.pricing_available.checked;
    const result = await request(`/api/v1/admin/providers/${encodeURIComponent(state.providerId)}/models`, { method: 'POST', body: JSON.stringify(values) });
    const message = select('#admin-model-error');
    if (!result.ok) {
      message.textContent = result.status === 409 ? t('adminRequestFailed') : t('adminSettingsInvalid');
      return;
    }
    message.textContent = '';
    form.reset();
    showToast(t('adminSettingsSaved'));
    await renderProviders();
  };
  const submitProvider = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    values.is_default = form.elements.is_default.checked;
    const result = await request('/api/v1/admin/providers', { method: 'POST', body: JSON.stringify(values) });
    const message = select('#admin-provider-error');
    if (!result.ok) {
      message.textContent = result.status === 409 ? t('adminRequestFailed') : t('adminSettingsInvalid');
      return;
    }
    message.textContent = '';
    form.reset();
    showToast(t('adminSettingsSaved'));
    await renderProviders();
  };
  const submitSettings = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const message = select('#admin-settings-message');
    const values = Object.fromEntries(new FormData(form).entries());
    const keys = ['generation_rate_limit_per_user', 'generation_rate_limit_global', 'generation_rate_limit_window_seconds', 'generation_max_output_tokens'];
    const results = [];
    for (const key of keys) {
      results.push(await request(`/api/v1/admin/settings/${key}`, { method: 'PATCH', body: JSON.stringify({ value: Number(values[key]) }) }));
    }
    results.push(await request('/api/v1/admin/settings/maintenance_mode', { method: 'PATCH', body: JSON.stringify({ value: form.elements.maintenance_mode.checked }) }));
    if (results.some((result) => !result.ok)) {
      message.textContent = t('adminSettingsInvalid');
      return;
    }
    message.textContent = t('adminSettingsSaved');
    showToast(t('adminSettingsSaved'));
  };
  const loadMe = async () => {
    const result = await request('/api/v1/admin/me');
    if (!result.ok) {
      state.user = null;
      select('#admin-access-state').hidden = false;
      select('#admin-access-title').textContent = result.status === 403 ? t('adminAccessDenied') : t('adminSignInRequired');
      select('#admin-access-message').textContent = result.status === 403 ? t('adminAccessDenied') : t('adminSignInRequired');
      return;
    }
    state.user = { ...result.data, display_name: '' };
    select('#admin-operator-name').textContent = 'Administrator';
    select('#admin-access-state').hidden = true;
  };
  const bind = () => {
    selectAll('[data-admin-route]').forEach((button) => button.addEventListener('click', () => setRoute(button.dataset.adminRoute)));
    selectAll('[data-admin-route-link]').forEach((button) => button.addEventListener('click', () => setRoute(button.dataset.adminRouteLink)));
    select('#admin-refresh').addEventListener('click', () => void loadRoute());
    select('#admin-language-toggle').addEventListener('click', () => {
      state.locale = isPersian() ? 'en' : 'fa';
      storage.set('roleverse-locale', state.locale);
      applyTranslations();
      void loadRoute();
    });
    select('#admin-theme-toggle').addEventListener('click', () => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark';
      setTheme();
    });
    select('#admin-menu-toggle').addEventListener('click', () => {
      select('#admin-sidebar').classList.add('is-open');
      select('#admin-sidebar-scrim').classList.add('is-visible');
    });
    select('#admin-sidebar-scrim').addEventListener('click', () => {
      select('#admin-sidebar').classList.remove('is-open');
      select('#admin-sidebar-scrim').classList.remove('is-visible');
    });
    select('#admin-users-filter').addEventListener('submit', (event) => {
      event.preventDefault();
      void renderUsers();
    });
    select('#admin-provider-form').addEventListener('submit', submitProvider);
    select('#admin-model-form').addEventListener('submit', submitModel);
    select('#admin-settings-form').addEventListener('submit', submitSettings);
    select('#admin-action-form').addEventListener('submit', submitDialog);
    select('#admin-dialog-close').addEventListener('click', closeDialog);
    select('#admin-dialog-cancel').addEventListener('click', closeDialog);
    select('#admin-logout').addEventListener('click', async () => {
      await request('/api/v1/auth/logout', { method: 'POST' });
      window.location.href = '../';
    });
    document.addEventListener('click', (event) => {
      const action = event.target.closest('[data-action]');
      if (!action) return;
      if (action.dataset.action === 'ban' || action.dataset.action === 'unban') {
        openDialog({ id: action.dataset.userId, display_name: action.dataset.userName, phone_masked: '' }, action.dataset.action);
      }
      if (action.dataset.action === 'role') {
        void request(`/api/v1/admin/users/${encodeURIComponent(action.dataset.userId)}/role`, {
          method: 'PATCH',
          body: JSON.stringify({ role: action.dataset.nextRole }),
        }).then((result) => {
          if (!result.ok) {
            showToast(t('adminForbidden'));
            return;
          }
          showToast(t('adminSettingsSaved'));
          void renderUsers();
        });
      }
    });
    window.addEventListener('hashchange', () => {
      const route = window.location.hash.replace(/^#\/?/, '').split('?')[0] || 'overview';
      setRoute(route);
    });
  };
  const init = async () => {
    setTheme();
    applyTranslations();
    bind();
    await loadMe();
    const route = window.location.hash.replace(/^#\/?/, '').split('?')[0] || 'overview';
    setRoute(route);
  };
  window.RoleVerseAdmin = { init, setRoute, refresh: loadRoute };
  void init();
})();
