// URL dinâmica para a API: usa /api em produção (Vercel) e http://127.0.0.1:8000/api localmente
const API_URL = (window.location.protocol === "file:" || window.location.port === "5500" || window.location.port === "5501")
    ? "http://127.0.0.1:8000/api"
    : "/api";

// --- Autenticação & Sessão ---
const token = localStorage.getItem("accessToken");
const storedUserId = localStorage.getItem("userId");
const currentUserName = localStorage.getItem("userName") || "Utilizador Conectado";

// Redireciona para o login se o utilizador não estiver autenticado
if (!storedUserId && !token) {
    window.location.href = "login.html";
}

const currentUserId = storedUserId ? parseInt(storedUserId) : 1;

// Estado global de dados e filtros
let state = {
    allTransactions: [],
    summary: null,
    filters: {
        search: "",
        type: "",
        category: ""
    },
    chartMode: "all",
    pendingDeleteId: null
};

// Headers com Bearer Token caso disponível
function getAuthHeaders(includeContentType = true) {
    const headers = {};
    if (includeContentType) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
}

// --- Inicialização ---
document.addEventListener("DOMContentLoaded", () => {
    console.log("FinanceTracker v2.0 Front-end inicializado com sucesso.");

    // Nome na barra superior
    const userDisplay = document.getElementById("user-display");
    if (userDisplay) userDisplay.innerText = currentUserName;

    // Data padrão de hoje no formulário
    const dateInput = document.getElementById("transaction_date");
    if (dateInput) {
        dateInput.value = new Date().toISOString().split("T")[0];
    }

    // Eventos
    configurarLogout();
    configurarFormularioCadastro();
    configurarFiltros();
    configurarExportacao();
    configurarModais();
    configurarAbasGrafico();

    // Carregamento de dados
    carregarDados();
});

// --- Sistema de Notificações Cyberpunk Toast ---
function showCyberToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `cyber-toast toast-${type}`;

    const icons = {
        success: "✓",
        error: "✕",
        warning: "⚠",
        info: "ℹ"
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || "ℹ"}</span>
        <span class="toast-text">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}

// --- Logout ---
function configurarLogout() {
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            localStorage.clear();
            showCyberToast("Sessão encerrada com sucesso.", "info");
            setTimeout(() => {
                window.location.href = "login.html";
            }, 600);
        });
    }
}

// --- Carregamento Centralizado de Dados ---
async function carregarDados() {
    await Promise.all([
        buscarTransacoes(),
        buscarResumoEPrevisao()
    ]);
}

async function buscarTransacoes() {
    try {
        const queryParams = new URLSearchParams();
        if (state.filters.type) queryParams.append("type", state.filters.type);
        if (state.filters.category) queryParams.append("category", state.filters.category);
        if (state.filters.search) queryParams.append("search", state.filters.search);

        const url = `${API_URL}/transactions/${currentUserId}?${queryParams.toString()}`;
        const response = await fetch(url, { headers: getAuthHeaders(false) });

        if (!response.ok) throw new Error("Falha ao carregar transações.");

        const data = await response.json();
        state.allTransactions = data.transactions || [];
        renderizarListaTransacoes(state.allTransactions);
    } catch (error) {
        console.error("Erro ao carregar transações:", error);
        showCyberToast("Não foi possível carregar o histórico de transações.", "error");
    }
}

async function buscarResumoEPrevisao() {
    try {
        const response = await fetch(`${API_URL}/transactions/${currentUserId}/summary`, {
            headers: getAuthHeaders(false)
        });

        if (!response.ok) throw new Error("Falha ao obter resumo e projeção.");

        const summary = await response.json();
        state.summary = summary;
        renderizarHUD(summary);
        renderizarPrevisaoInteligente(summary.forecast);
        renderizarGraficoColunas();
    } catch (error) {
        console.error("Erro ao carregar resumo:", error);
    }
}

// --- Renderização do HUD e Indicadores Principais ---
function renderizarHUD(summary) {
    const elDeposits = document.getElementById("total-deposits");
    const elExpenses = document.getElementById("total-expenses");
    const elBalance = document.getElementById("net-balance");
    const depositsCount = document.getElementById("deposits-count");
    const expensesCount = document.getElementById("expenses-count");
    const balanceStatus = document.getElementById("balance-status");

    const formatMoney = (val) => Number(val).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

    if (elDeposits) elDeposits.innerText = formatMoney(summary.total_deposits);
    if (elExpenses) elExpenses.innerText = formatMoney(summary.total_expenses);
    if (elBalance) elBalance.innerText = formatMoney(summary.net_balance);

    const totalIncomeCount = summary.categories.reduce((acc, c) => acc + (c.total_income > 0 ? c.count : 0), 0);
    const totalExpenseCount = summary.categories.reduce((acc, c) => acc + (c.total_expense > 0 ? c.count : 0), 0);

    if (depositsCount) depositsCount.innerText = `${totalIncomeCount} entradas registradas`;
    if (expensesCount) expensesCount.innerText = `${totalExpenseCount} saídas registradas`;

    if (balanceStatus) {
        if (summary.net_balance > 0) {
            balanceStatus.innerText = "Balanço positivo";
            balanceStatus.style.color = "var(--success-green)";
        } else if (summary.net_balance < 0) {
            balanceStatus.innerText = "Balanço negativo";
            balanceStatus.style.color = "var(--danger-red)";
        } else {
            balanceStatus.innerText = "Balanço neutro";
            balanceStatus.style.color = "var(--text-secondary)";
        }
    }
}

// --- Renderização da Previsão Inteligente (30 Dias) ---
function renderizarPrevisaoInteligente(forecast) {
    if (!forecast) return;

    const formatMoney = (val) => Number(val).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

    const elProjected = document.getElementById("forecast-projected-balance");
    const elDailyExpense = document.getElementById("forecast-daily-expense");
    const elDailyIncome = document.getElementById("forecast-daily-income");
    const elSavingsRate = document.getElementById("forecast-savings-rate");
    const elAdvice = document.getElementById("forecast-message");
    const elBadge = document.getElementById("forecast-badge");

    if (elProjected) elProjected.innerText = formatMoney(forecast.projected_balance_30d);
    if (elDailyExpense) elDailyExpense.innerText = formatMoney(forecast.daily_average_expense);
    if (elDailyIncome) elDailyIncome.innerText = formatMoney(forecast.daily_average_income);
    if (elSavingsRate) elSavingsRate.innerText = `${forecast.savings_rate.toFixed(1)}%`;
    if (elAdvice) elAdvice.innerText = forecast.message;

    if (elBadge) {
        elBadge.className = "forecast-badge";
        if (forecast.status === "positive") {
            elBadge.classList.add("badge-positive");
            elBadge.innerText = "Tendência Saudável";
        } else if (forecast.status === "critical") {
            elBadge.classList.add("badge-critical");
            elBadge.innerText = "Risco de Déficit";
        } else if (forecast.status === "warning") {
            elBadge.classList.add("badge-warning");
            elBadge.innerText = "Alerta de Gastos";
        } else {
            elBadge.classList.add("badge-neutral");
            elBadge.innerText = "Sem Dados Suficientes";
        }
    }
}

// --- Renderização da Lista de Transações ---
function renderizarListaTransacoes(transactions) {
    const listaContainer = document.getElementById("transactions-list");
    if (!listaContainer) return;

    if (!transactions || transactions.length === 0) {
        listaContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📭</span>
                <p class="empty-msg">Nenhuma movimentação encontrada com os filtros selecionados.</p>
            </div>
        `;
        return;
    }

    let html = "";
    transactions.forEach(tx => {
        const valorFormatado = Number(tx.amount).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
        const isIncome = tx.type === "income";

        html += `
            <div class="transaction-item ${tx.type}" data-id="${tx.id}">
                <div class="tx-badge-type">${isIncome ? "ENTRADA" : "SAÍDA"}</div>
                <div class="tx-info">
                    <strong class="tx-title">${escapeHtml(tx.description)}</strong>
                    <span class="tx-meta">
                        <span class="category-tag">${escapeHtml(tx.category)}</span>
                        <span>•</span>
                        <span>📅 ${tx.transaction_date}</span>
                    </span>
                </div>
                <div class="tx-right">
                    <div class="tx-amount ${tx.type}">
                        ${isIncome ? "+" : "-"} ${valorFormatado}
                    </div>
                    <div class="tx-actions">
                        <button class="btn-action btn-edit" onclick="abrirModalEdicao(${tx.id})" title="Editar movimentação">✏️</button>
                        <button class="btn-action btn-delete" onclick="solicitarExclusao(${tx.id})" title="Remover movimentação">🗑️</button>
                    </div>
                </div>
            </div>
        `;
    });

    listaContainer.innerHTML = html;
}

// --- Renderização do Gráfico de Colunas Analítico ---
function renderizarGraficoColunas() {
    const chartContainer = document.getElementById("column-chart");
    if (!chartContainer || !state.summary) return;

    const categories = state.summary.categories || [];
    if (categories.length === 0) {
        chartContainer.innerHTML = `<p class="empty-msg">Sem movimentações suficientes para gerar o gráfico.</p>`;
        return;
    }

    // Filtra conforme o modo ativo da aba: "all", "expense", "income"
    let chartData = [];
    if (state.chartMode === "expense") {
        chartData = categories
            .map(c => ({ category: c.category, value: c.total_expense, type: "expense" }))
            .filter(c => c.value > 0);
    } else if (state.chartMode === "income") {
        chartData = categories
            .map(c => ({ category: c.category, value: c.total_income, type: "income" }))
            .filter(c => c.value > 0);
    } else {
        // Geral: soma o volume financeiro
        chartData = categories
            .map(c => ({ category: c.category, value: c.total_expense + c.total_income, type: "both" }))
            .filter(c => c.value > 0);
    }

    if (chartData.length === 0) {
        chartContainer.innerHTML = `<p class="empty-msg">Nenhum valor para o modo "${state.chartMode}".</p>`;
        return;
    }

    const maxValue = Math.max(...chartData.map(d => d.value), 1);
    const totalVolume = chartData.reduce((acc, d) => acc + d.value, 0);

    let html = "";
    chartData.forEach(d => {
        const heightPct = Math.max(8, Math.round((d.value / maxValue) * 100));
        const sharePct = ((d.value / totalVolume) * 100).toFixed(1);
        const valFormatted = d.value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

        html += `
            <div class="chart-bar-wrapper" title="${escapeHtml(d.category)}: ${valFormatted} (${sharePct}%)">
                <span class="chart-val-top">${valFormatted}</span>
                <div class="chart-bar-outer">
                    <div class="chart-bar ${d.type}" style="height: ${heightPct}%;">
                        <span class="chart-pct">${sharePct}%</span>
                    </div>
                </div>
                <span class="chart-bar-label">${escapeHtml(d.category)}</span>
            </div>
        `;
    });

    chartContainer.innerHTML = html;
}

function configurarAbasGrafico() {
    const tabs = document.querySelectorAll(".chart-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            state.chartMode = tab.dataset.mode || "all";
            renderizarGraficoColunas();
        });
    });
}

// --- Formulário de Cadastro de Transação ---
function configurarFormularioCadastro() {
    const form = document.getElementById("transaction-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById("btn-submit-tx");
        const originalText = submitBtn.innerText;
        submitBtn.disabled = true;
        submitBtn.innerText = "Registrando...";

        const payload = {
            user_id: currentUserId,
            type: document.getElementById("type").value,
            amount: parseFloat(document.getElementById("amount").value),
            description: document.getElementById("description").value,
            category: document.getElementById("category").value,
            transaction_date: document.getElementById("transaction_date").value || new Date().toISOString().split("T")[0]
        };

        try {
            const response = await fetch(`${API_URL}/transactions`, {
                method: "POST",
                headers: getAuthHeaders(true),
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Erro ao criar transação.");
            }

            showCyberToast("Movimentação registrada com sucesso!", "success");
            form.reset();
            document.getElementById("transaction_date").value = new Date().toISOString().split("T")[0];

            await carregarDados();
        } catch (error) {
            console.error("Erro:", error);
            showCyberToast(error.message, "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = originalText;
        }
    });
}

// --- Filtros em Tempo Real ---
function configurarFiltros() {
    const inputSearch = document.getElementById("filter-search");
    const selectType = document.getElementById("filter-type");
    const selectCategory = document.getElementById("filter-category");
    const btnClear = document.getElementById("btn-clear-filters");

    let debounceTimer = null;

    if (inputSearch) {
        inputSearch.addEventListener("input", (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                state.filters.search = e.target.value.trim();
                buscarTransacoes();
            }, 250);
        });
    }

    if (selectType) {
        selectType.addEventListener("change", (e) => {
            state.filters.type = e.target.value;
            buscarTransacoes();
        });
    }

    if (selectCategory) {
        selectCategory.addEventListener("change", (e) => {
            state.filters.category = e.target.value;
            buscarTransacoes();
        });
    }

    if (btnClear) {
        btnClear.addEventListener("click", () => {
            state.filters = { search: "", type: "", category: "" };
            if (inputSearch) inputSearch.value = "";
            if (selectType) selectType.value = "";
            if (selectCategory) selectCategory.value = "";
            buscarTransacoes();
            showCyberToast("Filtros limpos.", "info");
        });
    }
}

// --- Exportação de Dados (CSV e JSON) ---
function configurarExportacao() {
    const btnCsv = document.getElementById("btn-export-csv");
    const btnJson = document.getElementById("btn-export-json");

    if (btnCsv) {
        btnCsv.addEventListener("click", async () => {
            try {
                showCyberToast("Gerando exportação CSV...", "info");
                const res = await fetch(`${API_URL}/transactions/${currentUserId}/export?format=csv`, {
                    headers: getAuthHeaders(false)
                });
                if (!res.ok) throw new Error("Erro ao gerar CSV.");
                const blob = await res.blob();
                baixarArquivo(blob, `finance_tracker_${currentUserId}_${new Date().toISOString().slice(0, 10)}.csv`);
                showCyberToast("Download do CSV iniciado!", "success");
            } catch (err) {
                showCyberToast("Falha ao exportar CSV.", "error");
            }
        });
    }

    if (btnJson) {
        btnJson.addEventListener("click", async () => {
            try {
                showCyberToast("Gerando exportação JSON...", "info");
                const res = await fetch(`${API_URL}/transactions/${currentUserId}/export?format=json`, {
                    headers: getAuthHeaders(false)
                });
                if (!res.ok) throw new Error("Erro ao gerar JSON.");
                const data = await res.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                baixarArquivo(blob, `finance_tracker_${currentUserId}_${new Date().toISOString().slice(0, 10)}.json`);
                showCyberToast("Download do JSON iniciado!", "success");
            } catch (err) {
                showCyberToast("Falha ao exportar JSON.", "error");
            }
        });
    }
}

function baixarArquivo(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}

// --- Modais: Edição & Confirmação ---
function configurarModais() {
    // Fechar modais ao clicar no X ou fora
    const editModal = document.getElementById("edit-modal");
    const confirmModal = document.getElementById("confirm-modal");

    document.getElementById("btn-close-edit-modal")?.addEventListener("click", () => fecharModal(editModal));
    document.getElementById("btn-cancel-edit")?.addEventListener("click", () => fecharModal(editModal));

    document.getElementById("btn-close-confirm-modal")?.addEventListener("click", () => fecharModal(confirmModal));
    document.getElementById("btn-confirm-cancel")?.addEventListener("click", () => fecharModal(confirmModal));

    // Submissão do Form de Edição
    const editForm = document.getElementById("edit-transaction-form");
    if (editForm) {
        editForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const id = document.getElementById("edit-id").value;
            const payload = {
                type: document.getElementById("edit-type").value,
                amount: parseFloat(document.getElementById("edit-amount").value),
                description: document.getElementById("edit-description").value,
                category: document.getElementById("edit-category").value,
                transaction_date: document.getElementById("edit-date").value
            };

            try {
                const res = await fetch(`${API_URL}/transactions/${id}`, {
                    method: "PUT",
                    headers: getAuthHeaders(true),
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Erro ao salvar alterações.");

                showCyberToast("Movimentação atualizada com sucesso!", "success");
                fecharModal(editModal);
                await carregarDados();
            } catch (err) {
                showCyberToast(err.message, "error");
            }
        });
    }

    // Ação de confirmar exclusão
    const btnConfirmDelete = document.getElementById("btn-confirm-delete");
    if (btnConfirmDelete) {
        btnConfirmDelete.addEventListener("click", async () => {
            if (!state.pendingDeleteId) return;

            try {
                const res = await fetch(`${API_URL}/transactions/${state.pendingDeleteId}`, {
                    method: "DELETE",
                    headers: getAuthHeaders(false)
                });

                if (!res.ok) throw new Error("Erro ao excluir transação.");

                showCyberToast("Movimentação excluída com sucesso!", "success");
                fecharModal(confirmModal);
                state.pendingDeleteId = null;
                await carregarDados();
            } catch (err) {
                showCyberToast("Não foi possível excluir a transação.", "error");
            }
        });
    }
}

function fecharModal(modal) {
    if (modal) modal.classList.add("hidden");
}

function abrirModal(modal) {
    if (modal) modal.classList.remove("hidden");
}

// Chamado a partir do botão Editar
window.abrirModalEdicao = function(id) {
    const tx = state.allTransactions.find(t => t.id === id);
    if (!tx) return;

    document.getElementById("edit-id").value = tx.id;
    document.getElementById("edit-type").value = tx.type;
    document.getElementById("edit-amount").value = tx.amount;
    document.getElementById("edit-description").value = tx.description;
    document.getElementById("edit-category").value = tx.category;
    document.getElementById("edit-date").value = tx.transaction_date;

    abrirModal(document.getElementById("edit-modal"));
};

// Chamado a partir do botão Excluir
window.solicitarExclusao = function(id) {
    state.pendingDeleteId = id;
    abrirModal(document.getElementById("confirm-modal"));
};

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m];
    });
}