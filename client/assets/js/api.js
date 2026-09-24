window.RoleVerseApi = {
  async request(path, options = {}) {
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
      const data = response.status === 204 ? null : await response.json();
      return { ok: response.ok, status: response.status, data };
    } catch (error) {
      return { ok: false, status: 0, data: null };
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
};
