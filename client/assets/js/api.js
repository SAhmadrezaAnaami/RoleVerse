window.RoleVerseApi = {
  async getHealth() {
    try {
      const response = await fetch('/api/v1/health', {
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      return null;
    }
  },
};
