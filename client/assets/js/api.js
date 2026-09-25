window.RoleVerseApi = {
  csrfToken() {
    const prefix = 'roleverse_csrf=';
    const value = document.cookie.split(';').map((item) => item.trim()).find((item) => item.startsWith(prefix));
    return value ? decodeURIComponent(value.slice(prefix.length)) : '';
  },
  async request(path, options = {}) {
    const method = String(options.method || 'GET').toUpperCase();
    const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method);
    const token = this.csrfToken();
    try {
      const response = await fetch(path, {
        ...options,
        credentials: 'include',
        cache: 'no-store',
        redirect: 'error',
        headers: {
          Accept: 'application/json',
          ...(options.body ? { 'Content-Type': 'application/json' } : {}),
          ...(unsafe && token ? { 'X-CSRF-Token': token } : {}),
          ...(options.headers || {}),
        },
      });
      let data = null;
      if (response.status !== 204) {
        const text = await response.text();
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (error) {
            data = null;
          }
        }
      }
      return { ok: response.ok, status: response.status, data };
    } catch (error) {
      return { ok: false, status: 0, data: null, error };
    }
  },
  async consumeEventStream(response, onEvent) {
    if (!response.body) {
      throw new Error('Streaming is not supported by this browser.');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let eventName = 'message';
    let dataLines = [];
    let eventCount = 0;
    let totalBytes = 0;
    let expectedSequence = 1;
    const maxBufferBytes = 256 * 1024;
    const maxEventBytes = 128 * 1024;
    const maxStreamBytes = 2 * 1024 * 1024;
    const maxEvents = 10000;
    const dispatch = async () => {
      if (dataLines.length === 0) {
        eventName = 'message';
        return;
      }
      const rawData = dataLines.join('\n');
      dataLines = [];
      if (rawData.length > maxEventBytes) {
        throw new Error('The server returned an oversized stream event.');
      }
      eventCount += 1;
      if (eventCount > maxEvents) {
        throw new Error('The server returned too many stream events.');
      }
      if (rawData === '[DONE]') {
        eventName = 'message';
        return;
      }
      let data;
      try {
        data = JSON.parse(rawData);
      } catch (error) {
        throw new Error('The server returned an invalid stream event.');
      }
      if (data && data.sequence !== undefined) {
        if (!Number.isInteger(data.sequence) || data.sequence !== expectedSequence) {
          throw new Error('The server returned an invalid stream sequence.');
        }
        expectedSequence += 1;
      }
      await onEvent(eventName, data);
      eventName = 'message';
    };
    const consume = async (final = false) => {
      if (buffer.length > maxBufferBytes) {
        throw new Error('The server returned an oversized stream buffer.');
      }
      let boundary = buffer.match(/\r?\n\r?\n/);
      while (boundary) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        for (const line of frame.split(/\r?\n/)) {
          if (line.startsWith(':')) {
            continue;
          }
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).replace(/^ /, ''));
          }
        }
        await dispatch();
        boundary = buffer.match(/\r?\n\r?\n/);
      }
      if (final && buffer.length > 0) {
        for (const line of buffer.split(/\r?\n/)) {
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).replace(/^ /, ''));
          }
        }
        await dispatch();
        buffer = '';
      }
    };
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (value) {
          totalBytes += value.byteLength;
          if (totalBytes > maxStreamBytes) {
            throw new Error('The server returned an oversized stream.');
          }
        }
        if (done) {
          buffer += decoder.decode();
          await consume(true);
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        await consume();
      }
    } catch (error) {
      try {
        await reader.cancel();
      } catch (cancelError) {
        void cancelError;
      }
      throw error;
    } finally {
      reader.releaseLock();
    }
  },
  async getHealth() {
    const result = await this.request('/api/v1/health');
    return result.ok ? result.data : null;
  },
  async requestOtp(phone) {
    return this.request('/api/v1/auth/otp/request', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
  },
  async verifyOtp(phone, code) {
    return this.request('/api/v1/auth/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ phone, code }),
    });
  },
  async getMe() {
    return this.request('/api/v1/auth/me');
  },
  async logout() {
    return this.request('/api/v1/auth/logout', { method: 'POST' });
  },
  async getCharacters({ locale = 'en', search = '', category = '' } = {}) {
    const params = new URLSearchParams({ locale });
    if (search) params.set('search', search);
    if (category) params.set('category', category);
    return this.request(`/api/v1/characters?${params.toString()}`);
  },
  async getConversations() {
    return this.request('/api/v1/conversations');
  },
  async createConversation({ characterSlug, locale = 'en', title = '' }) {
    return this.request('/api/v1/conversations', {
      method: 'POST',
      body: JSON.stringify({ character_slug: characterSlug, locale, ...(title ? { title } : {}) }),
    });
  },
  async getMessages(conversationId, limit = 100) {
    return this.request(`/api/v1/conversations/${encodeURIComponent(conversationId)}/messages?limit=${limit}`);
  },
  async sendMessage(conversationId, { content, clientRequestId, mode = 'preview' }) {
    return this.request(`/api/v1/conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, client_request_id: clientRequestId, mode }),
    });
  },
  async generateMessage(conversationId, messageId) {
    return this.request(`/api/v1/conversations/${encodeURIComponent(conversationId)}/messages/${encodeURIComponent(messageId)}/response`, { method: 'POST' });
  },
  async getGenerationStatus(conversationId, runId) {
    return this.request(`/api/v1/conversations/${encodeURIComponent(conversationId)}/generations/${encodeURIComponent(runId)}`);
  },
  async cancelGeneration(conversationId, runId) {
    return this.request(`/api/v1/conversations/${encodeURIComponent(conversationId)}/generations/${encodeURIComponent(runId)}/cancel`, {
      method: 'POST',
    });
  },
  async streamMessage(conversationId, messageId, { signal, onEvent } = {}) {
    try {
      const response = await fetch(
        `/api/v1/conversations/${encodeURIComponent(conversationId)}/messages/${encodeURIComponent(messageId)}/responses`,
        {
          method: 'POST',
          credentials: 'include',
          cache: 'no-store',
          redirect: 'error',
          headers: {
            Accept: 'text/event-stream',
            ...(this.csrfToken() ? { 'X-CSRF-Token': this.csrfToken() } : {}),
          },
          signal,
        },
      );
      if (!response.ok) {
        let data = null;
        try {
          data = await response.json();
        } catch (error) {
          data = null;
        }
        return { ok: false, status: response.status, data };
      }
      await this.consumeEventStream(response, onEvent);
      return { ok: true, status: response.status, data: null };
    } catch (error) {
      return { ok: false, status: 0, data: null, error };
    }
  },
};
