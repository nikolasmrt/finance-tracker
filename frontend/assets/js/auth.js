// URL dinâmica para a API: usa /api em produção (Vercel) e http://127.0.0.1:8000/api localmente
const API_URL = (window.location.protocol === "file:" || window.location.port === "5500" || window.location.port === "5501")
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
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `cyber-toast toast-${type}`;
    const icon = type === "success" ? "✓" : (type === "error" ? "✕" : (type === "warning" ? "⚠" : "ℹ"));

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-text">${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 400);
    }, 3500);
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
            credentials: "include" // Permite gravação segura do cookie HTTP-Only
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao iniciar o Modo Convidado.");
        }

        // Armazena identificadores de sessão no storage
        localStorage.setItem("userId", data.user.id);
        localStorage.setItem("userName", data.user.name);
        localStorage.setItem("userEmail", data.user.email);
        localStorage.setItem("isDemo", "true");
        if (data.access_token) {
            localStorage.setItem("accessToken", data.access_token);
        }

        showAuthToast("✨ Modo Convidado ativado! Redirecionando para o Dashboard...", "success");

        setTimeout(() => {
            window.location.href = "index.html";
        }, 600);
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
            credentials: "include", // Envia e armazena cookies HTTP-Only
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao efetuar login. Verifique as credenciais.");
        }

        // Armazena dados de sessão
        if (data.access_token) {
            localStorage.setItem("accessToken", data.access_token);
        }
        localStorage.setItem("userId", data.user.id);
        localStorage.setItem("userName", data.user.name);
        localStorage.setItem("userEmail", data.user.email);
        localStorage.setItem("isDemo", data.user.is_demo ? "true" : "false");

        showAuthToast("Login efetuado com sucesso! Redirecionando...", "success");

        setTimeout(() => {
            window.location.href = "index.html";
        }, 600);
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

    if (password.length < 6) {
        showAuthToast("A senha deve ter no mínimo 6 caracteres.", "warning");
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
            body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao criar conta.");
        }

        showAuthToast("Conta criada com sucesso! Faça login para aceder.", "success");
        setTimeout(() => {
            window.location.href = "login.html";
        }, 1000);
    } catch (error) {
        showAuthToast(error.message, "error");
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerText = originalText;
        }
    }
}
