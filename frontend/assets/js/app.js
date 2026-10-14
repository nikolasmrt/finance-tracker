const API_URL = "http://127.0.0.1:8000/api";
// Recupera o ID e nome do utilizador autenticado no localStorage (padrão 1 se não logado)
let currentUserId = localStorage.getItem("userId") ? parseInt(localStorage.getItem("userId")) : 1;
let currentUserName = localStorage.getItem("userName") || "Usuário não logado";

document.addEventListener("DOMContentLoaded", () => {
    console.log("FinanceTracker Front-end inicializado.");
    
    // Atualiza nome na barra superior
    const userDisplay = document.getElementById("user-display");
    if (userDisplay) userDisplay.innerText = currentUserName;

    // Configura botão de logout
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            localStorage.clear();
            window.location.href = "login.html";
        });
    }

    verificarConexaoAPI();
    configurarEventosFormulario();
});

async function verificarConexaoAPI() {
    try {
        const response = await fetch("http://127.0.0.1:8000/");
        const data = await response.json();
        console.log("Status da API Python:", data.status);
        carregarTransacoes(currentUserId);
    } catch (error) {
        console.error("Erro crítico: Back-end inacessível.", error);
    }
}

function configurarEventosFormulario() {
    const transactionForm = document.getElementById("transaction-form");
    if (transactionForm) {
        transactionForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            await submeterTransacao();
        });
    }
}

async function submeterTransacao() {
    const type = document.getElementById("type").value;
    const amount = parseFloat(document.getElementById("amount").value);
    const description = document.getElementById("description").value;
    const category = document.getElementById("category").value;

    const payload = {
        user_id: currentUserId,
        type,
        amount,
        description,
        category,
        transaction_date: new Date().toISOString().split('T')[0]
    };

    try {
        const response = await fetch(`${API_URL}/transactions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("Erro ao registar movimentação.");
        
        document.getElementById("transaction-form").reset();
        carregarTransacoes(currentUserId);
    } catch (error) {
        console.error("Erro:", error);
        alert("Erro ao salvar transação.");
    }
}

async function carregarTransacoes(userId) {
    try {
        const response = await fetch(`${API_URL}/transactions/${userId}`);
        if (!response.ok) throw new Error("Erro ao buscar transações.");
        
        const data = await response.json();
        renderizarDashboard(data.transactions);
        renderizarGraficoColunas(data.transactions);
    } catch (error) {
        console.error("Erro ao carregar histórico:", error);
    }
}

async function removerTransacao(id) {
    if (!confirm("Tem certeza que deseja remover esta movimentação?")) return;

    try {
        const response = await fetch(`${API_URL}/transactions/${id}`, {
            method: "DELETE"
        });

        if (!response.ok) throw new Error("Erro ao eliminar transação.");

        carregarTransacoes(currentUserId);
    } catch (error) {
        console.error("Erro:", error);
        alert("Não foi possível excluir a transação.");
    }
}

function renderizarDashboard(transactions) {
    const listaContainer = document.getElementById("transactions-list");
    const elDeposits = document.getElementById("total-deposits");
    const elExpenses = document.getElementById("total-expenses");
    const elBalance = document.getElementById("net-balance");

    if (!transactions || transactions.length === 0) {
        listaContainer.innerHTML = `<p class="empty-msg">Nenhuma movimentação registrada ainda.</p>`;
        elDeposits.innerText = "R$ 0,00";
        elExpenses.innerText = "R$ 0,00";
        elBalance.innerText = "R$ 0,00";
        return;
    }

    let totalDeposits = 0;
    let totalExpenses = 0;
    let htmlContent = "";

    transactions.forEach(tx => {
        const valorFormatado = Number(tx.amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        
        if (tx.type === "income") {
            totalDeposits += Number(tx.amount);
        } else {
            totalExpenses += Number(tx.amount);
        }

        htmlContent += `
            <div class="transaction-item ${tx.type}">
                <div class="tx-info">
                    <strong>${tx.description}</strong>
                    <span>${tx.category} • ${tx.transaction_date}</span>
                </div>
                <div class="tx-right">
                    <div class="tx-amount ${tx.type}">
                        ${tx.type === 'income' ? '+' : '-'} ${valorFormatado}
                    </div>
                    <button class="btn-delete" onclick="removerTransacao(${tx.id})" title="Remover transação">🗑️</button>
                </div>
            </div>
        `;
    });

    const netBalance = totalDeposits - totalExpenses;

    elDeposits.innerText = totalDeposits.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    elExpenses.innerText = totalExpenses.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    elBalance.innerText = netBalance.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    
    listaContainer.innerHTML = htmlContent;
}

function renderizarGraficoColunas(transactions) {
    const chartContainer = document.getElementById("column-chart");

    if (!transactions || transactions.length === 0) {
        chartContainer.innerHTML = `<p class="empty-msg">Sem dados suficientes para gerar o gráfico.</p>`;
        return;
    }

    // Agrupar gastos/entradas por categoria
    const categorias = {};
    transactions.forEach(tx => {
        if (!categorias[tx.category]) {
            categorias[tx.category] = 0;
        }
        // Soma os valores (entradas positivas, saídas negativas ou absolutas)
        categorias[tx.category] += Math.abs(Number(tx.amount));
    });

    const entradas = Object.entries(categorias);
    const maxVal = Math.max(...entradas.map(item => item[1]), 1);

    let chartHtml = "";
    entradas.forEach(([cat, val]) => {
        const alturaPercentual = Math.round((val / maxVal) * 100);
        const valFormatado = val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

        chartHtml += `
            <div class="chart-bar-wrapper" title="${cat}: ${valFormatado}">
                <div class="chart-bar" style="height: ${alturaPercentual}%;"></div>
                <span class="chart-bar-label">${cat}</span>
            </div>
        `;
    });

    chartContainer.innerHTML = chartHtml;
}