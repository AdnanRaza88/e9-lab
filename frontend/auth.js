const API_BASE_URL = "http://localhost:8000";

const el = (id) => document.getElementById(id);

function toast(message, type) {
  const node = el("toast");
  node.textContent = message;
  node.className = "toast" + (type ? " " + type : "");
  node.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { node.hidden = true; }, 3500);
}

const copy = {
  login: {
    headline: "Welcome back",
    subline: "Log in to keep grading with your rubrics.",
    footer: 'New here? <a href="#" id="switchToRegister">Create an account</a>'
  },
  register: {
    headline: "Create your account",
    subline: "Set up a rubric once, score reports in minutes.",
    footer: 'Already have an account? <a href="#" id="switchToLogin">Log in</a>'
  }
};

function switchTab(tab) {
  document.querySelectorAll(".auth-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  el("loginForm").hidden = tab !== "login";
  el("registerForm").hidden = tab !== "register";
  el("authHeadline").textContent = copy[tab].headline;
  el("authSubline").textContent = copy[tab].subline;
  el("footerSwitch").innerHTML = copy[tab].footer;

  const switchLink = tab === "login" ? el("switchToRegister") : el("switchToLogin");
  if (switchLink) {
    switchLink.addEventListener("click", (event) => {
      event.preventDefault();
      switchTab(tab === "login" ? "register" : "login");
    });
  }
}

document.querySelectorAll(".auth-tab").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

function onAuthSuccess(data, username) {
  localStorage.setItem("e9_token", data.access_token);
  localStorage.setItem("e9_username", username);
  window.location.href = "app.html";
}

el("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  el("loginError").hidden = true;
  const username = el("loginUsername").value.trim();

  try {
    const response = await fetch(API_BASE_URL + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password: el("loginPassword").value })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "could not log in, check your username and password");
    }
    onAuthSuccess(data, username);
  } catch (err) {
    el("loginError").textContent = err.message;
    el("loginError").hidden = false;
  }
});

el("registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  el("registerError").hidden = true;
  const username = el("registerUsername").value.trim();

  try {
    const response = await fetch(API_BASE_URL + "/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password: el("registerPassword").value })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "could not create your account");
    }
    onAuthSuccess(data, username);
  } catch (err) {
    el("registerError").textContent = err.message;
    el("registerError").hidden = false;
  }
});

function init() {
  if (localStorage.getItem("e9_token")) {
    window.location.href = "app.html";
    return;
  }
  const params = new URLSearchParams(window.location.search);
  const requestedTab = params.get("tab");
  switchTab(requestedTab === "register" ? "register" : "login");
}

init();
