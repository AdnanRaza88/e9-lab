(() => {
  // Same origin when served from the Railway app itself; otherwise the live backend.
  const API_BASE_URL =
    window.location.origin === "https://web-production-e5526.up.railway.app"
      ? ""
      : "https://web-production-e5526.up.railway.app";

  const tabs = document.querySelectorAll('.auth-tab');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const headline = document.getElementById('authHeadline');
  const subline = document.getElementById('authSubline');
  const footerSwitch = document.getElementById('footerSwitch');
  const switchToRegister = document.getElementById('switchToRegister');
  const toast = document.getElementById('toast');

  const copy = {
    login: {
      headline: 'Welcome back',
      subline: "Log in to keep grading with your rubrics.",
      footer: 'New here? <a href="#" id="switchToRegister">Create an account</a>'
    },
    register: {
      headline: 'Create your account',
      subline: 'Set a username and password to start building rubrics.',
      footer: 'Already have an account? <a href="#" id="switchToLogin">Log in</a>'
    }
  };

  function setTab(name) {
    tabs.forEach(t => {
      const active = t.dataset.tab === name;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', String(active));
    });

    loginForm.hidden = name !== 'login';
    registerForm.hidden = name !== 'register';

    headline.textContent = copy[name].headline;
    subline.textContent = copy[name].subline;
    footerSwitch.innerHTML = copy[name].footer;

    bindFooterLink();
  }

  function bindFooterLink() {
    const link = footerSwitch.querySelector('a');
    if (!link) return;
    link.addEventListener('click', e => {
      e.preventDefault();
      setTab(link.id === 'switchToRegister' ? 'register' : 'login');
    });
  }

  tabs.forEach(tab => {
    tab.addEventListener('click', () => setTab(tab.dataset.tab));
  });

  switchToRegister.addEventListener('click', e => {
    e.preventDefault();
    setTab('register');
  });

  // Password visibility toggles
  document.querySelectorAll('.field-visibility').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.target);
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
      btn.classList.toggle('is-visible', !showing);
    });
  });

  function showError(el, message) {
    el.textContent = message;
    el.hidden = false;
  }

  function hideError(el) {
    el.hidden = true;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.hidden = false;
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => { toast.hidden = true; }, 200);
    }, 2200);
  }

  function playCheck(button) {
    button.classList.add('is-checked');
    setTimeout(() => button.classList.remove('is-checked'), 900);
  }

  async function authRequest(path, username, password) {
    const res = await fetch(API_BASE_URL + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.access_token) {
      throw new Error((data.error && data.error.message) || 'Something went wrong. Please try again.');
    }
    return data;
  }

  function finishAuth(data, username) {
    localStorage.setItem('e9_token', data.access_token);
    localStorage.setItem('e9_username', username);
    window.location.href = 'app.html';
  }

  // Login submit
  loginForm.addEventListener('submit', async e => {
    e.preventDefault();
    const errorEl = document.getElementById('loginError');
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!username || !password) {
      showError(errorEl, 'Enter your username and password to continue.');
      return;
    }
    hideError(errorEl);

    const button = loginForm.querySelector('.btn');
    button.disabled = true;
    try {
      const data = await authRequest('/auth/login', username, password);
      playCheck(button);
      finishAuth(data, username);
    } catch (err) {
      showError(errorEl, err.message);
      button.disabled = false;
    }
  });

  // Register submit
  registerForm.addEventListener('submit', async e => {
    e.preventDefault();
    const errorEl = document.getElementById('registerError');
    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value;

    if (username.length < 3) {
      showError(errorEl, 'Usernames need at least 3 characters.');
      return;
    }
    if (password.length < 8) {
      showError(errorEl, 'Passwords need at least 8 characters.');
      return;
    }
    hideError(errorEl);

    const button = registerForm.querySelector('.btn');
    button.disabled = true;
    try {
      const data = await authRequest('/auth/register', username, password);
      playCheck(button);
      showToast(`Account created. Welcome, ${username}.`);
      setTimeout(() => finishAuth(data, username), 700);
    } catch (err) {
      showError(errorEl, err.message);
      button.disabled = false;
    }
  });
})();
