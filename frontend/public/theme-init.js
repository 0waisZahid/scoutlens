try {
  const theme = localStorage.getItem("scoutlens.theme");
  if (theme === "light" || theme === "dark") {
    document.documentElement.dataset.theme = theme;
  }
} catch {}
