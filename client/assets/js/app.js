(() => {
  const data = window.RoleVerseData;
  const i18n = window.RoleVerseI18n;
  const api = window.RoleVerseApi;
  const root = document.documentElement;
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
    activeCharacterId: 'luna',
    activeView: 'chat',
    messagesByCharacter: Object.fromEntries(
      data.characters.map((character) => [character.id, character.messages.map((message) => ({ ...message }))]),
    ),
    favorites: new Set(data.favoriteIds),
    rateLimitRemaining: 20,
    isResponding: false,
    authStep: 'phone',
    authPhone: '',
    currentUser: null,
    remoteConversations: new Map(),
    remoteMessages: new Map(),
    remoteCharacters: new Map(),
  };
  const replies = {
    luna: 'Then let’s make tonight a little more impossible. I’ll bring the stars; you bring the question.',
    rowan: 'A map is only useful when it leaves room for a detour. I know one that starts right here.',
    mira: 'That question changes the shape of the room around it. I like where your curiosity is taking us.',
    orion: 'Careful. Once you start asking better questions, every ordinary door starts whispering.',
    sage: 'Begin with the part that feels unfinished. That is usually where the answer is hiding.',
    nova: 'I’ll put it in the next postcard. By the time you receive it, we may both be somewhere else.',
  };
  const characterById = new Map(data.characters.map((character) => [character.id, character]));
  const select = (selector, parent = document) => parent.querySelector(selector);
  const selectAll = (selector, parent = document) => Array.from(parent.querySelectorAll(selector));
  const getCharacter = (id) => characterById.get(id) || data.characters[0];
  const characterSlugs = {
    luna: 'luna-vale',
    rowan: 'rowan-vale',
    mira: 'mira-sol',
    orion: 'orion-ash',
    sage: 'sage-nox',
    nova: 'nova-wren',
  };
  const getCharacterSlug = (character) => character.slug || characterSlugs[character.id] || character.id;
  const getTranslation = (key) => i18n[state.locale]?.[key] || i18n.en[key] || key;
  const isPersian = () => state.locale === 'fa';
  const getLocalTime = () =>
    new Intl.DateTimeFormat(isPersian() ? 'fa-IR' : 'en-US', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date());

  const formatServerTime = (value) => {
    if (!value) {
      return getLocalTime();
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return getLocalTime();
    }
    return new Intl.DateTimeFormat(isPersian() ? 'fa-IR' : 'en-US', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  };

  const normalizeApiMessage = (message) => ({
    role: message.role,
    content: message.content,
    time: formatServerTime(message.created_at),
    id: message.id,
    position: message.position,
  });

  const createRequestId = () => {
    if (window.crypto?.randomUUID) {
      return window.crypto.randomUUID();
    }
    return `request-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  async function loadRemoteCharacters(locale = state.locale) {
    const result = await api.getCharacters({ locale });
    if (!result.ok) {
      return;
    }
    const avatarClasses = ['avatar-luna', 'avatar-rowan', 'avatar-mira', 'avatar-orion', 'avatar-sage'];
    result.data.forEach((remote, index) => {
      const existing = data.characters.find((character) => getCharacterSlug(character) === remote.slug);
      const localizedName = remote.name;
      const localizedTagline = remote.tagline;
      const normalized = {
        ...(existing || {}),
        id: existing?.id || remote.id,
        slug: remote.slug,
        name: locale === 'fa' ? existing?.name || localizedName : localizedName,
        nameFa: locale === 'fa' ? localizedName : existing?.nameFa || localizedName,
        role: locale === 'fa' ? existing?.role || localizedTagline : localizedTagline,
        roleFa: locale === 'fa' ? localizedTagline : existing?.roleFa || localizedTagline,
        description: remote.description,
        descriptionFa: locale === 'fa' ? remote.description : existing?.descriptionFa || remote.description,
        category: remote.category,
        categoryFa: locale === 'fa' ? remote.category : existing?.categoryFa || remote.category,
        tags: remote.tags,
        tagsFa: locale === 'fa' ? remote.tags : existing?.tagsFa || remote.tags,
        accentStart: remote.accent_start,
        accentEnd: remote.accent_end,
        gradientStart: remote.accent_start,
        gradientEnd: remote.accent_end,
        greeting: remote.greeting || existing?.greeting || '',
        greetingFa: locale === 'fa' ? remote.greeting : existing?.greetingFa || remote.greeting,
        avatar: existing?.avatar || localizedName.slice(0, 2).toUpperCase(),
        avatarClass: existing?.avatarClass || avatarClasses[index % avatarClasses.length],
      };
      if (existing) {
        Object.assign(existing, normalized);
        characterById.set(existing.id, existing);
      } else {
        data.characters.push(normalized);
        characterById.set(normalized.id, normalized);
        state.messagesByCharacter[normalized.id] = [
          { role: 'assistant', content: normalized.greeting, time: getLocalTime() },
        ];
      }
      state.remoteCharacters.set(remote.slug, normalized);
    });
    renderConversationList();
    renderGrids();
    updateActiveCharacter();
    renderMessages();
  }

  function applyTranslations() {
    root.lang = state.locale;
    root.dir = isPersian() ? 'rtl' : 'ltr';
    select('#language-label').textContent = isPersian() ? 'فا' : 'EN';
    selectAll('[data-i18n]').forEach((element) => {
      element.textContent = getTranslation(element.dataset.i18n);
    });
    selectAll('[data-i18n-placeholder]').forEach((element) => {
      element.setAttribute('placeholder', getTranslation(element.dataset.i18nPlaceholder));
    });
    selectAll('[data-i18n-aria]').forEach((element) => {
      element.setAttribute('aria-label', getTranslation(element.dataset.i18nAria));
    });
    const languageLabel = isPersian() ? 'فا' : 'EN';
    select('#language-toggle').setAttribute('aria-label', `${languageLabel} — ${getTranslation('changeLanguage')}`);
    select('.avatar-top').setAttribute('aria-label', `AM — ${getTranslation('openAccount')}`);
    document.title = isPersian()
      ? 'رول‌ورس — شخصیت‌های تو، داستان‌های تو'
      : 'RoleVerse — Your characters, your stories';
  }

  function setTheme(theme, announce = false) {
    state.theme = theme;
    root.dataset.theme = theme;
    storage.set('roleverse-theme', theme);
    select('#theme-toggle').setAttribute('aria-label', getTranslation('toggleTheme'));
    if (announce) {
      showToast(getTranslation('themeChanged'));
    }
  }

  function setLocale(locale, announce = false) {
    state.locale = locale;
    storage.set('roleverse-locale', locale);
    applyTranslations();
    renderConversationList();
    renderGrids();
    updateActiveCharacter();
    renderMessages();
    void loadRemoteCharacters(locale);
    if (announce) {
      showToast(getTranslation('languageChanged'));
    }
  }

  function renderConversationList() {
    const list = select('#conversation-list');
    list.replaceChildren();
    data.conversations.forEach((conversation) => {
      const character = getCharacter(conversation.characterId);
      const remoteConversation = state.remoteConversations.get(conversation.characterId);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `conversation-item${conversation.characterId === state.activeCharacterId ? ' is-active' : ''}`;
      button.dataset.characterId = conversation.characterId;
      button.setAttribute('aria-current', conversation.characterId === state.activeCharacterId ? 'page' : 'false');

      const avatar = document.createElement('span');
      avatar.className = `avatar avatar-small ${character.avatarClass}`;
      avatar.textContent = character.avatar;
      avatar.setAttribute('aria-hidden', 'true');

      const copy = document.createElement('span');
      copy.className = 'conversation-item-copy';
      const name = document.createElement('strong');
      name.textContent = isPersian() ? character.nameFa : character.name;
      const preview = document.createElement('span');
      preview.textContent = remoteConversation
        ? remoteConversation.last_message_preview || remoteConversation.title
        : isPersian() ? conversation.previewFa : conversation.preview;
      copy.append(name, preview);

      const time = document.createElement('time');
      time.textContent = remoteConversation
        ? formatServerTime(remoteConversation.updated_at)
        : isPersian() ? conversation.timeFa : conversation.time;

      button.append(avatar, copy, time);
      button.addEventListener('click', () => selectCharacter(conversation.characterId));
      list.append(button);
    });
  }

  function createCharacterCard(character) {
    const card = document.createElement('article');
    card.className = 'character-card';

    const visual = document.createElement('div');
    visual.className = 'character-card-visual';
    visual.style.setProperty('--card-gradient-start', character.gradientStart);
    visual.style.setProperty('--card-gradient-end', character.gradientEnd);

    const avatar = document.createElement('span');
    avatar.className = `avatar ${character.avatarClass}`;
    avatar.textContent = character.avatar;
    avatar.setAttribute('aria-hidden', 'true');

    const label = document.createElement('span');
    label.className = 'card-visual-label';
    label.textContent = isPersian() ? character.categoryFa : character.category;

    const heart = document.createElement('button');
    heart.type = 'button';
    heart.className = 'card-heart';
    heart.setAttribute('aria-pressed', state.favorites.has(character.id) ? 'true' : 'false');
    heart.setAttribute('aria-label', getTranslation(state.favorites.has(character.id) ? 'removeFavorite' : 'addFavorite'));
    heart.innerHTML = '<svg class="icon icon-sm"><use href="#icon-heart"></use></svg>';
    heart.addEventListener('click', (event) => {
      event.stopPropagation();
      toggleFavorite(character.id);
    });

    visual.append(avatar, label, heart);

    const body = document.createElement('div');
    body.className = 'character-card-body';
    const title = document.createElement('h2');
    title.textContent = isPersian() ? character.nameFa : character.name;
    const description = document.createElement('p');
    description.textContent = isPersian() ? character.descriptionFa : character.description;
    const footer = document.createElement('div');
    footer.className = 'character-card-footer';
    const role = document.createElement('span');
    role.textContent = isPersian() ? character.roleFa : character.role;
    const action = document.createElement('button');
    action.type = 'button';
    action.textContent = getTranslation('startChat');
    action.addEventListener('click', (event) => {
      event.stopPropagation();
      selectCharacter(character.id);
    });
    footer.append(role, action);
    body.append(title, description, footer);
    card.append(visual, body);

    card.addEventListener('click', () => selectCharacter(character.id));
    return card;
  }

  function renderGrids() {
    const search = (select('#character-search')?.value || '').trim().toLowerCase();
    const filtered = data.characters.filter((character) => {
      const searchable = [character.name, character.nameFa, character.role, character.roleFa, character.category, character.categoryFa]
        .join(' ')
        .toLowerCase();
      return searchable.includes(search);
    });
    [
      ['#discover-grid', filtered],
      ['#marketplace-grid', data.characters],
      ['#favorites-grid', data.characters.filter((character) => state.favorites.has(character.id))],
    ].forEach(([selector, characters]) => {
      const grid = select(selector);
      grid.replaceChildren(...characters.map((character) => createCharacterCard(character)));
    });
  }

  function updateActiveCharacter() {
    const character = getCharacter(state.activeCharacterId);
    const name = isPersian() ? character.nameFa : character.name;
    const role = isPersian() ? character.roleFa : character.role;
    const activeAvatar = select('#active-avatar');
    activeAvatar.className = `avatar avatar-large ${character.avatarClass}`;
    activeAvatar.textContent = character.avatar;
    select('#chat-view-title').textContent = isPersian() ? `لحظه‌ای آرام با ${name}` : `A quiet moment with ${name}`;
    select('#active-character-subtitle').textContent = isPersian()
      ? `${role} · آخرین گفت‌وگوی تو را به خاطر دارد`
      : `${role} · remembers your last conversation`;
    select('#message-input').setAttribute('aria-label', isPersian() ? `پیام به ${name}` : `Message ${name}`);
    select('#typing-indicator span:last-child').textContent = `${name} ${getTranslation('typing')}`;

    const panelName = select('[data-i18n="lunaName"]');
    const panelRole = select('[data-i18n="stargazer"]');
    const panelDescription = select('[data-i18n="lunaDescription"]');
    const panelStatus = select('.availability-pill span:last-child');
    panelName.textContent = name;
    panelRole.textContent = role;
    panelDescription.textContent = isPersian() ? character.descriptionFa : character.description;
    panelStatus.textContent = isPersian() ? character.statusFa : character.status;
    selectAll('.tag').forEach((tag, index) => {
      tag.textContent = isPersian() ? character.tagsFa[index] || character.tags[index] : character.tags[index];
    });
    const favoriteButton = select('[data-action="favorite"]');
    favoriteButton.classList.toggle('is-favorite', state.favorites.has(character.id));
    favoriteButton.setAttribute('aria-pressed', state.favorites.has(character.id) ? 'true' : 'false');
    renderConversationList();
  }

  function renderMessages() {
    const list = select('#message-list');
    const character = getCharacter(state.activeCharacterId);
    const messages = state.messagesByCharacter[character.id] || [];
    const fragment = document.createDocumentFragment();
    const divider = document.createElement('div');
    divider.className = 'day-divider';
    divider.textContent = getTranslation('today');
    fragment.append(divider);

    messages.forEach((message) => {
      const article = document.createElement('article');
      article.className = `message message-${message.role}`;
      article.setAttribute('aria-label', `${message.role === 'user' ? getTranslation('you') : (isPersian() ? character.nameFa : character.name)} · ${message.time}`);

      if (message.role === 'assistant') {
        const avatar = document.createElement('span');
        avatar.className = `avatar avatar-message ${character.avatarClass}`;
        avatar.textContent = character.avatar;
        avatar.setAttribute('aria-hidden', 'true');
        article.append(avatar);
      }

      const body = document.createElement('div');
      body.className = 'message-body';
      const meta = document.createElement('div');
      meta.className = 'message-meta';
      const time = document.createElement('time');
      time.textContent = message.time;
      const name = document.createElement('strong');
      name.textContent = message.role === 'user' ? getTranslation('you') : (isPersian() ? character.nameFa : character.name);
      meta.append(time, name);

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';
      bubble.setAttribute('dir', 'auto');
      bubble.textContent = message.content;
      body.append(meta, bubble);
      article.append(body);

      if (message.role === 'user') {
        const avatar = document.createElement('span');
        avatar.className = 'avatar avatar-message avatar-alex';
        avatar.textContent = 'AM';
        avatar.setAttribute('aria-hidden', 'true');
        article.append(avatar);
      }
      fragment.append(article);
    });
    list.replaceChildren(fragment);
    requestAnimationFrame(() => {
      list.scrollTop = list.scrollHeight;
    });
  }

  function appendMessage(role, content) {
    const characterId = state.activeCharacterId;
    state.messagesByCharacter[characterId].push({
      role,
      content,
      time: getLocalTime(),
    });
    renderMessages();
  }

  function setView(view) {
    const validViews = ['chat', 'discover', 'marketplace', 'favorites'];
    const nextView = validViews.includes(view) ? view : 'chat';
    state.activeView = nextView;
    selectAll('[data-view]').forEach((section) => {
      const isVisible = section.dataset.view === nextView;
      section.hidden = !isVisible;
      section.classList.toggle('is-visible', isVisible);
    });
    selectAll('[data-view-target]').forEach((item) => {
      const isActive = item.dataset.viewTarget === nextView;
      item.classList.toggle('is-active', isActive);
      if (isActive) {
        item.setAttribute('aria-current', 'page');
      } else {
        item.removeAttribute('aria-current');
      }
    });
    select('#breadcrumb-current').textContent = getTranslation(nextView);
    closeSidebar();
  }

  function selectCharacter(characterId) {
    if (!characterById.has(characterId)) {
      return;
    }
    state.activeCharacterId = characterId;
    updateActiveCharacter();
    renderMessages();
    void loadRemoteMessages(character);
    setView('chat');
    if (window.location.hash !== '#/chat') {
      window.history.replaceState(null, '', '#/chat');
    }
  }

  function toggleFavorite(characterId) {
    if (state.favorites.has(characterId)) {
      state.favorites.delete(characterId);
      showToast(getTranslation('favoriteRemoved'));
    } else {
      state.favorites.add(characterId);
      showToast(getTranslation('favoriteAdded'));
    }
    updateActiveCharacter();
    renderGrids();
  }

  async function loadRemoteConversations() {
    if (!state.currentUser) {
      return;
    }
    const result = await api.getConversations();
    if (!result.ok) {
      if (result.status === 401) {
        state.currentUser = null;
      }
      return;
    }
    state.remoteConversations.clear();
    result.data.forEach((conversation) => {
      const character = data.characters.find(
        (item) => getCharacterSlug(item) === conversation.character.slug,
      );
      if (character) {
        state.remoteConversations.set(character.id, conversation);
        if (!data.conversations.some((item) => item.characterId === character.id)) {
          data.conversations.push({
            id: conversation.id,
            characterId: character.id,
            preview: '',
            previewFa: '',
            time: conversation.updated_at,
            timeFa: conversation.updated_at,
          });
        }
      }
    });
    renderConversationList();
  }

  async function loadRemoteMessages(character) {
    const conversation = state.remoteConversations.get(character.id);
    if (!conversation) {
      return false;
    }
    const result = await api.getMessages(conversation.id);
    if (!result.ok) {
      if (result.status === 401) {
        state.currentUser = null;
      }
      return false;
    }
    state.remoteMessages.set(conversation.id, result.data);
    state.messagesByCharacter[character.id] = result.data.map(normalizeApiMessage);
    renderMessages();
    return true;
  }

  async function ensureRemoteConversation(character) {
    if (!state.currentUser) {
      return null;
    }
    let conversation = state.remoteConversations.get(character.id);
    if (!conversation) {
      const result = await api.createConversation({
        characterSlug: getCharacterSlug(character),
        locale: state.locale,
      });
      if (!result.ok) {
        if (result.status === 401) {
          state.currentUser = null;
        }
        showToast(getTranslation('authUnavailable'));
        return null;
      }
      conversation = result.data;
      state.remoteConversations.set(character.id, conversation);
      renderConversationList();
    }
    await loadRemoteMessages(character);
    return conversation;
  }

  function showToast(message) {
    const region = select('#toast-region');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.setAttribute('role', 'status');
    toast.textContent = message;
    region.append(toast);
    window.setTimeout(() => toast.remove(), 2800);
  }

  function setAuthError(message = '') {
    const error = select('#auth-error');
    error.textContent = message;
    error.hidden = !message;
  }

  function updateAuthStep() {
    const isOtpStep = state.authStep === 'otp';
    const phoneInput = select('#phone-input');
    const otpField = select('#otp-field');
    const otpInput = select('#otp-input');
    const submitButton = select('#auth-form button[type="submit"]');
    const title = select('#auth-dialog .dialog-heading h2');
    const description = select('#auth-dialog .dialog-heading p:last-child');
    phoneInput.disabled = isOtpStep;
    otpField.hidden = !isOtpStep;
    otpInput.required = isOtpStep;
    submitButton.dataset.i18n = isOtpStep ? 'verifyOtp' : 'sendOtp';
    submitButton.textContent = getTranslation(submitButton.dataset.i18n);
    title.dataset.i18n = isOtpStep ? 'verifyOtpTitle' : 'signInTitle';
    title.textContent = getTranslation(title.dataset.i18n);
    description.dataset.i18n = isOtpStep ? 'verifyOtpDescription' : 'signInDescription';
    description.textContent = getTranslation(description.dataset.i18n);
    if (isOtpStep) {
      window.setTimeout(() => otpInput.focus(), 50);
    }
  }

  function resetAuthForm() {
    state.authStep = 'phone';
    state.authPhone = '';
    select('#auth-form').reset();
    setAuthError();
    updateAuthStep();
  }

  function openAuthDialog() {
    const dialog = select('#auth-dialog');
    resetAuthForm();
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }
    window.setTimeout(() => select('#phone-input').focus(), 50);
  }

  function closeAuthDialog() {
    const dialog = select('#auth-dialog');
    if (typeof dialog.close === 'function') {
      dialog.close();
    } else {
      dialog.removeAttribute('open');
    }
  }

  function updateUserProfile(user) {
    if (!user) {
      return;
    }
    state.currentUser = user;
    const displayName = user.display_name || 'RoleVerse member';
    select('.profile-copy strong').textContent = displayName;
    const initials = displayName
      .split(' ')
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
    selectAll('.avatar-top, .profile-button .avatar').forEach((avatar) => {
      avatar.textContent = initials || 'RV';
    });
  }

  async function submitAuth(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) {
      return;
    }
    const submitButton = select('#auth-form button[type="submit"]');
    submitButton.disabled = true;
    setAuthError();
    try {
      if (state.authStep === 'phone') {
        const phone = select('#phone-input').value.trim();
        const result = await api.requestOtp(phone);
        if (!result.ok) {
          setAuthError(result.status === 429 ? result.data?.detail || getTranslation('authError') : getTranslation('authUnavailable'));
          return;
        }
        state.authPhone = phone;
        state.authStep = 'otp';
        updateAuthStep();
        return;
      }
      const code = select('#otp-input').value.trim();
      const result = await api.verifyOtp(state.authPhone, code);
      if (!result.ok) {
        setAuthError(result.status === 429 ? result.data?.detail || getTranslation('authError') : getTranslation('authError'));
        return;
      }
      updateUserProfile(result.data?.user);
      await loadRemoteConversations();
      await ensureRemoteConversation(getCharacter(state.activeCharacterId));
      closeAuthDialog();
      showToast(getTranslation('loginSuccess'));
    } finally {
      submitButton.disabled = false;
    }
  }

  function openSidebar() {
    select('#sidebar').classList.add('is-open');
    select('#sidebar-scrim').classList.add('is-visible');
  }

  function closeSidebar() {
    select('#sidebar').classList.remove('is-open');
    select('#sidebar-scrim').classList.remove('is-visible');
  }

  function resetComposer() {
    const input = select('#message-input');
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  }

  async function sendMessage() {
    if (state.isResponding) {
      return;
    }
    const input = select('#message-input');
    const content = input.value.trim();
    if (!content) {
      input.focus();
      return;
    }
    if (!state.currentUser && state.rateLimitRemaining <= 0) {
      showToast(getTranslation('messageLimit'));
      return;
    }
    const character = getCharacter(state.activeCharacterId);
    const messageList = select('#message-list');
    const typing = select('#typing-indicator');
    const sendButton = select('#send-message');
    state.isResponding = true;
    messageList.setAttribute('aria-busy', 'true');
    typing.classList.add('is-visible');
    typing.setAttribute('aria-hidden', 'false');
    sendButton.disabled = true;
    try {
      if (state.currentUser) {
        const conversation = await ensureRemoteConversation(character);
        if (!conversation) {
          return;
        }
        const result = await api.sendMessage(conversation.id, {
          content,
          clientRequestId: createRequestId(),
        });
        if (!result.ok) {
          if (result.status === 401) {
            state.currentUser = null;
          }
          showToast(getTranslation('authUnavailable'));
          return;
        }
        state.messagesByCharacter[character.id].push(
          normalizeApiMessage(result.data.user_message),
          normalizeApiMessage(result.data.assistant_message),
        );
        renderMessages();
        input.value = '';
        resetComposer();
        showToast(getTranslation('responseReady'));
        return;
      }
      state.rateLimitRemaining -= 1;
      appendMessage('user', content);
      input.value = '';
      resetComposer();
      showToast(getTranslation('messageSent'));
      window.setTimeout(() => {
        appendMessage('assistant', replies[character.id] || replies.luna);
        showToast(getTranslation('responseReady'));
      }, 900);
    } finally {
      typing.classList.remove('is-visible');
      typing.setAttribute('aria-hidden', 'true');
      messageList.setAttribute('aria-busy', 'false');
      sendButton.disabled = false;
      state.isResponding = false;
    }
  }

  function updateHealth(health) {
    const status = select('#health-status');
    const label = select('.status-label', status);
    if (health) {
      status.dataset.state = 'online';
      label.dataset.i18n = 'serviceOnline';
      label.textContent = getTranslation('serviceOnline');
    } else {
      status.dataset.state = 'offline';
      label.dataset.i18n = 'serviceOffline';
      label.textContent = getTranslation('serviceOffline');
    }
  }

  function bindEvents() {
    selectAll('[data-view-target]').forEach((item) => {
      item.addEventListener('click', () => {
        const view = item.dataset.viewTarget;
        window.history.replaceState(null, '', `#/${view}`);
        setView(view);
      });
    });
    select('#theme-toggle').addEventListener('click', () => {
      setTheme(state.theme === 'dark' ? 'light' : 'dark', true);
    });
    select('#language-toggle').addEventListener('click', () => {
      setLocale(isPersian() ? 'en' : 'fa', true);
    });
    select('#message-input').addEventListener('input', resetComposer);
    select('#message-input').addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        void sendMessage();
      }
    });
    select('#composer').addEventListener('submit', (event) => {
      event.preventDefault();
      void sendMessage();
    });
    select('#character-search').addEventListener('input', renderGrids);
    select('#auth-form').addEventListener('submit', submitAuth);
    document.addEventListener('click', (event) => {
      const actionElement = event.target.closest('[data-action]');
      if (!actionElement) {
        return;
      }
      const action = actionElement.dataset.action;
      if (action === 'open-sidebar') {
        openSidebar();
      } else if (action === 'close-sidebar') {
        closeSidebar();
      } else if (action === 'open-auth') {
        openAuthDialog();
      } else if (action === 'close-auth') {
        closeAuthDialog();
      } else if (action === 'new-chat') {
        const character = getCharacter(state.activeCharacterId);
        if (state.currentUser) {
          void ensureRemoteConversation(character).then((conversation) => {
            if (conversation) {
              setView('chat');
              showToast(getTranslation('newChatCreated'));
            }
          });
        } else {
          state.messagesByCharacter[character.id] = [
            { role: 'assistant', content: isPersian() ? character.greetingFa : character.greeting, time: getLocalTime() },
          ];
          renderMessages();
          setView('chat');
          showToast(getTranslation('newChatCreated'));
        }
      } else if (action === 'favorite') {
        toggleFavorite(state.activeCharacterId);
      } else if (action === 'more') {
        showToast(getTranslation('profileComingSoon'));
      } else if (action === 'open-character') {
        showToast(getTranslation('profileComingSoon'));
      } else if (action === 'browse-marketplace') {
        window.history.replaceState(null, '', '#/discover');
        setView('discover');
      }
    });
    window.addEventListener('hashchange', () => {
      const route = window.location.hash.replace(/^#\/?/, '').split('?')[0];
      setView(route);
    });
    window.addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        select('#message-input').focus();
      }
      if (event.key === 'Escape') {
        closeSidebar();
      }
    });
    select('#auth-dialog').addEventListener('click', (event) => {
      if (event.target === event.currentTarget) {
        closeAuthDialog();
      }
    });
  }

  function init() {
    root.dataset.theme = state.theme;
    applyTranslations();
    renderConversationList();
    renderGrids();
    updateActiveCharacter();
    renderMessages();
    const route = window.location.hash.replace(/^#\/?/, '').split('?')[0] || 'chat';
    setView(route);
    bindEvents();
    void loadRemoteCharacters(state.locale);
    api.getHealth().then(updateHealth);
    api.getMe().then(async (result) => {
      if (result.ok) {
        updateUserProfile(result.data);
        await loadRemoteConversations();
        await loadRemoteMessages(getCharacter(state.activeCharacterId));
      }
    });
  }

  init();
})();
