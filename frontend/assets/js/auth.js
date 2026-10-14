const API_URL = "http://127.0.0.1:8000/api";

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

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
});

async function realizarLogin() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao efetuar login.");
        }

        // Armazena os dados do utilizador no localStorage do browser
        localStorage.setItem("userId", data.user.id);
        localStorage.setItem("userName", data.user.name);
        localStorage.setItem("userEmail", data.user.email);

        // Redireciona para o Dashboard principal
        window.location.href = "index.html";
    } catch (error) {
        alert("Falha no login: " + error.message);
    }
}

async function realizarRegisto() {
    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao criar conta.");
        }

        alert("Conta criada com sucesso! Faça login para continuar.");
        window.location.href = "login.html";
    } catch (error) {
        alert("Erro no registo: " + error.message);
    }
}