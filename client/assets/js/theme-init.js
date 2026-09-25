(() => {
  try {
    const savedTheme = localStorage.getItem('roleverse-theme');
    if (savedTheme === 'dark' || savedTheme === 'light') {
      document.documentElement.dataset.theme = savedTheme;
    }
  } catch (error) {
    document.documentElement.dataset.theme = 'light';
  }
})();
