/**
 * GESTÃO DE SESSÃO POR COOKIE HTTP-ONLY & MODO CONVIDADO 1-CLICK — FINANCETRACKER 3.0
 * O token JWT trafega exclusivamente em Cookie HttpOnly/SameSite=Lax (protegido contra XSS).
 */
const API_URL =
    window.location.protocol === "file:" ||
    window.location.port === "5500" ||
    window.location.port === "5501"
        ? "http://127.0.0.1:8000/api"
        : "/api";

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");
    const demoBtn = document.getElementById("btn-demo-login");

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            await realizarLogin();
        });
    }

    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            await realizarRegisto();
        });
    }

    if (demoBtn) {
        demoBtn.addEventListener("click", async () => {
            await iniciarModoDemo();
        });
    }
});

function showAuthToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        container.setAttribute("role", "status");
        container.setAttribute("aria-live", "polite");
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `cyber-toast toast-${type}`;
    const icon =
        type === "success" ? "✓" : type === "error" ? "✕" : type === "warning" ? "⚠" : "ℹ";

    const iconSpan = document.createElement("span");
    iconSpan.className = "toast-icon";
    iconSpan.textContent = icon;

    const textSpan = document.createElement("span");
    textSpan.className = "toast-text";
    textSpan.textContent = message;

    toast.appendChild(iconSpan);
    toast.appendChild(textSpan);
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}

function saveUserSessionMeta(user) {
    // Nunca gravamos o token JWT no localStorage (ele reside apenas no Cookie HttpOnly).
    localStorage.removeItem("accessToken");
    localStorage.setItem("userId", String(user.id));
    localStorage.setItem("userName", user.name);
    localStorage.setItem("userEmail", user.email);
    localStorage.setItem("isDemo", user.is_demo ? "true" : "false");
}

async function iniciarModoDemo() {
    const btnDemo = document.getElementById("btn-demo-login");
    const originalText = btnDemo ? btnDemo.innerText : "🧪 Testar Agora (Modo Convidado)";
    if (btnDemo) {
        btnDemo.disabled = true;
        btnDemo.innerText = "⚡ Gerando ambiente de demonstração...";
    }

    try {
        const response = await fetch(`${API_URL}/demo`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Erro ao iniciar o Modo Convidado.");
        }

        saveUserSessionMeta(data.user);
        showAuthToast("✨ Modo Convidado ativado! Redirecionando para o Dashboard...", "success");

        setTimeout(() => {
            window.location.href = "index.html";
        }, 500);
    } catch (error) {
        console.error("Falha no modo demo:", error);
        showAuthToast(error.message, "error");
        if (btnDemo) {
            btnDemo.disabled = false;
            btnDemo.innerText = originalText;
        }
    }
}

async function realizarLogin() {
    const btnSubmit = document.querySelector("#login-form button[type='submit']");
    const originalText = btnSubmit ? btnSubmit.innerText : "Entrar";
    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerText = "A autenticar...";
    }

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Erro ao efetuar login. Verifique as credenciais.");
        }

        saveUserSessionMeta(data.user);
        showAuthToast("Login efetuado com sucesso! Redirecionando...", "success");

        setTimeout(() => {
            window.location.href = "index.html";
        }, 500);
    } catch (error) {
        showAuthToast(error.message, "error");
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerText = originalText;
        }
    }
}

async function realizarRegisto() {
    const btnSubmit = document.querySelector("#register-form button[type='submit']");
    const originalText = btnSubmit ? btnSubmit.innerText : "Registrar";
    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerText = "A criar conta...";
    }

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (password.length < 8) {
        showAuthToast("A senha deve ter no mínimo 8 caracteres.", "warning");
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerText = originalText;
        }
        return;
    }

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ name, email, password }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Erro ao criar conta.");
        }

        saveUserSessionMeta(data.user);
        showAuthToast("Conta criada com sucesso! Redirecionando para o Dashboard...", "success");
        setTimeout(() => {
            window.location.href = "index.html";
        }, 700);
    } catch (error) {
        showAuthToast(error.message, "error");
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerText = originalText;
        }
    }
}
