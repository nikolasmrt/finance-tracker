// URL dinâmica para a API: usa /api em produção (Vercel) e http://127.0.0.1:8000/api localmente
const API_URL = (window.location.protocol === "file:" || window.location.port === "5500" || window.location.port === "5501")
    ? "http://127.0.0.1:8000/api"
    : "/api";

// --- Estado Global da Aplicação ---
let state = {
    userId: localStorage.getItem("userId") ? parseInt(localStorage.getItem("userId")) : null,
    userName: localStorage.getItem("userName") || "Utilizador",
    userEmail: localStorage.getItem("userEmail") || "",
    isDemo: localStorage.getItem("isDemo") === "true",
    currency: localStorage.getItem("preferredCurrency") || "BRL",
    theme: localStorage.getItem("theme") || "cyberpunk",
    privacyMode: localStorage.getItem("privacy_mode") === "true",
    
    // Transações & Paginação
    transactions: [],
    pagination: {
        page: 1,
        limit: 8,
        total_records: 0,
        total_pages: 1
    },
    filters: {
        search: "",
        tag: "",
        type: "",
        category: ""
    },

    // Resumos, Orçamentos, Metas, Contas e Linha do Tempo
    summary: null,
    budgets: [],
    goals: [],
    bills: [],
    timelineData: null,
    timelineChartInstance: null,
    chartMode: "all",
    pendingDeleteTxId: null
};

// --- Formatação de Moeda Multi-Moeda (com suporte a Modo Privacidade) ---
function formatCurrency(val) {
    if (state.privacyMode) {
        return "••••••";
    }
    const num = Number(val) || 0;
    const map = {
        BRL: { locale: "pt-BR", currency: "BRL" },
        USD: { locale: "en-US", currency: "USD" },
        EUR: { locale: "de-DE", currency: "EUR" }
    };
    const cfg = map[state.currency] || map.BRL;
    return num.toLocaleString(cfg.locale, { style: "currency", currency: cfg.currency });
}

// Headers padrão com credenciais seguras
function getFetchOptions(method = "GET", body = null) {
    const options = {
        method,
        credentials: "include" // Transmite e armazena os cookies HTTP-Only automaticamente
    };

    const headers = {};
    const localToken = localStorage.getItem("accessToken");
    if (localToken) {
        headers["Authorization"] = `Bearer ${localToken}`;
    }

    if (body) {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }
    options.headers = headers;
    return options;
}

// --- Inicialização da Aplicação ---
document.addEventListener("DOMContentLoaded", async () => {
    console.log("FinanceTracker v2.1 Front-end inicializado.");

    // Aplica tema e moeda salvos
    aplicarTema(state.theme);
    inicializarMoeda();

    // Valida sessão via /api/me (verifica Cookie HTTP-Only ou Token)
    const autenticado = await validarSessao();
    if (!autenticado) return;

    // Atualiza cabeçalho com nome e modo demo
    atualizarPerfilHeader();

    // Data padrão de hoje no formulário
    const dateInput = document.getElementById("transaction_date");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];

    // Registra todos os eventos de interface
    configurarLogout();
    configurarTema();
    configurarMoeda();
    configurarModoPrivacidade();
    configurarComandosVoz();
    configurarNotificacoesPush();
    configurarNavegacaoMobile();
    configurarFocusTrapModais();
    configurarAtalhosTeclado();
    configurarFormularioTransacao();
    configurarFiltrosEPaginacao();
    configurarExportacao();
    configurarSimuladorCenarios();
    configurarModais();
    configurarAbasGrafico();
    inicializarPWA();

    // Carrega dados completos
    await carregarTodosOsDados();
});

// --- Validação de Sessão & Guarda de Rota ---
async function validarSessao() {
    try {
        const response = await fetch(`${API_URL}/me`, getFetchOptions("GET"));
        if (!response.ok) throw new Error("Não autenticado");
        const userData = await response.json();

        state.userId = userData.id;
        state.userName = userData.name;
        state.userEmail = userData.email;
        state.isDemo = Boolean(userData.is_demo);

        localStorage.setItem("userId", userData.id);
        localStorage.setItem("userName", userData.name);
        localStorage.setItem("userEmail", userData.email);
        localStorage.setItem("isDemo", state.isDemo ? "true" : "false");

        return true;
    } catch (error) {
        console.warn("Sessão não identificada. Redirecionando para login.");
        localStorage.clear();
        window.location.href = "login.html";
        return false;
    }
}

function atualizarPerfilHeader() {
    const userDisplay = document.getElementById("user-display");
    const demoBadge = document.getElementById("demo-badge-indicator");
    if (userDisplay) userDisplay.innerText = state.userName;

    if (demoBadge) {
        if (state.isDemo) {
            demoBadge.classList.remove("hidden");
        } else {
            demoBadge.classList.add("hidden");
        }
    }
}

// --- Alternância de Tema (Cyberpunk vs Clean) ---
function aplicarTema(theme) {
    state.theme = theme;
    localStorage.setItem("theme", theme);

    const themeLabel = document.getElementById("theme-label");
    const themeIcon = document.getElementById("theme-icon");

    if (theme === "clean") {
        document.body.setAttribute("data-theme", "clean");
        if (themeLabel) themeLabel.innerText = "Clean Dark";
        if (themeIcon) themeIcon.innerText = "🌙";
    } else {
        document.body.removeAttribute("data-theme");
        if (themeLabel) themeLabel.innerText = "Cyberpunk";
        if (themeIcon) themeIcon.innerText = "⚡";
    }
}

function configurarTema() {
    const btnTheme = document.getElementById("theme-toggle-btn");
    if (btnTheme) {
        btnTheme.addEventListener("click", () => {
            const next = state.theme === "clean" ? "cyberpunk" : "clean";
            aplicarTema(next);
            showCyberToast(`Tema alterado para ${next === 'clean' ? 'Clean Minimal' : 'Cyberpunk Neon'}!`, "info");
        });
    }
}

// --- Configuração Multi-Moeda ---
function inicializarMoeda() {
    const select = document.getElementById("currency-select");
    if (select) {
        select.value = state.currency;
    }
}

function configurarMoeda() {
    const select = document.getElementById("currency-select");
    if (select) {
        select.addEventListener("change", (e) => {
            state.currency = e.target.value;
            localStorage.setItem("preferredCurrency", state.currency);
            showCyberToast(`Moeda alterada para ${state.currency}`, "info");

            // Re-renderiza todos os componentes monetários
            if (state.summary) {
                renderizarHUD(state.summary);
                renderizarPrevisaoInteligente(state.summary.forecast);
                atualizarSimuladorCenarios();
            }
            renderizarListaTransacoes(state.transactions);
            renderizarOrcamentos(state.budgets);
            renderizarMetas(state.goals);
            renderizarGraficoColunas();
        });
    }
}

// --- Atalhos de Teclado Globais ---
function configurarAtalhosTeclado() {
    window.addEventListener("keydown", (e) => {
        // Ignora se estiver digitando em campo de texto a menos que seja ESC
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
        const isInput = activeTag === "input" || activeTag === "textarea" || activeTag === "select";

        if (e.key === "Escape") {
            fecharTodosModais();
            return;
        }

        if (isInput) return;

        if (e.key === "n" || e.key === "N") {
            e.preventDefault();
            const descInput = document.getElementById("description");
            if (descInput) {
                descInput.focus();
                descInput.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        } else if (e.key === "f" || e.key === "F" || e.key === "/") {
            e.preventDefault();
            const searchInput = document.getElementById("filter-search");
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
}

// --- Notificações Cyberpunk Toast ---
function showCyberToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `cyber-toast toast-${type}`;
    const icons = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };

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
        logoutBtn.addEventListener("click", async () => {
            try {
                await fetch(`${API_URL}/logout`, getFetchOptions("POST"));
            } catch (e) {
                console.error(e);
            }
            localStorage.clear();
            showCyberToast("Sessão encerrada com sucesso.", "info");
            setTimeout(() => window.location.href = "login.html", 400);
        });
    }
}

// --- Carregamento Unificado de Dados ---
async function carregarTodosOsDados() {
    await Promise.all([
        buscarTransacoes(),
        buscarResumoEPrevisao(),
        carregarOrcamentos(),
        carregarMetas(),
        carregarContasAlertas(),
        carregarEvolucaoPatrimonial()
    ]);
}

// --- Busca de Transações com Paginação e Filtros ---
async function buscarTransacoes() {
    try {
        const q = new URLSearchParams();
        q.append("page", state.pagination.page);
        q.append("limit", state.pagination.limit);
        if (state.filters.type) q.append("type", state.filters.type);
        if (state.filters.category) q.append("category", state.filters.category);
        if (state.filters.search) q.append("search", state.filters.search);
        if (state.filters.tag) q.append("tag", state.filters.tag);

        const res = await fetch(`${API_URL}/transactions/${state.userId}?${q.toString()}`, getFetchOptions("GET"));
        if (!res.ok) throw new Error("Erro ao buscar transações");

        const data = await res.json();
        state.transactions = data.transactions || [];
        state.pagination = data.pagination || { page: 1, limit: 8, total_records: 0, total_pages: 1 };

        renderizarListaTransacoes(state.transactions);
        renderizarBarraPaginacao();
    } catch (err) {
        console.error("Falha ao buscar transações:", err);
    }
}

function renderizarBarraPaginacao() {
    const p = state.pagination;
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");
    const indicator = document.getElementById("page-indicator");

    if (btnPrev) btnPrev.disabled = p.page <= 1;
    if (btnNext) btnNext.disabled = p.page >= p.total_pages;

    if (indicator) {
        indicator.innerText = `Página ${p.page} de ${p.total_pages} (${p.total_records} registro${p.total_records === 1 ? '' : 's'})`;
    }
}

function configurarFiltrosEPaginacao() {
    const inputSearch = document.getElementById("filter-search");
    const inputTag = document.getElementById("filter-tag");
    const selectType = document.getElementById("filter-type");
    const selectCategory = document.getElementById("filter-category");
    const btnClear = document.getElementById("btn-clear-filters");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");

    let debounceTimer = null;
    if (inputSearch) {
        inputSearch.addEventListener("input", (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                state.filters.search = e.target.value.trim();
                state.pagination.page = 1; // Reseta para primeira página
                buscarTransacoes();
            }, 250);
        });
    }

    if (inputTag) {
        inputTag.addEventListener("input", (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                state.filters.tag = e.target.value.trim();
                state.pagination.page = 1;
                buscarTransacoes();
            }, 250);
        });
    }

    if (selectType) {
        selectType.addEventListener("change", (e) => {
            state.filters.type = e.target.value;
            state.pagination.page = 1;
            buscarTransacoes();
        });
    }

    if (selectCategory) {
        selectCategory.addEventListener("change", (e) => {
            state.filters.category = e.target.value;
            state.pagination.page = 1;
            buscarTransacoes();
        });
    }

    if (btnClear) {
        btnClear.addEventListener("click", () => {
            state.filters = { search: "", tag: "", type: "", category: "" };
            if (inputSearch) inputSearch.value = "";
            if (inputTag) inputTag.value = "";
            if (selectType) selectType.value = "";
            if (selectCategory) selectCategory.value = "";
            state.pagination.page = 1;
            buscarTransacoes();
            showCyberToast("Filtros limpos.", "info");
        });
    }

    if (btnPrev) {
        btnPrev.addEventListener("click", () => {
            if (state.pagination.page > 1) {
                state.pagination.page -= 1;
                buscarTransacoes();
            }
        });
    }

    if (btnNext) {
        btnNext.addEventListener("click", () => {
            if (state.pagination.page < state.pagination.total_pages) {
                state.pagination.page += 1;
                buscarTransacoes();
            }
        });
    }
}

// --- Resumo & Previsão Inteligente ---
async function buscarResumoEPrevisao() {
    try {
        const res = await fetch(`${API_URL}/transactions/${state.userId}/summary`, getFetchOptions("GET"));
        if (!res.ok) throw new Error("Erro ao buscar resumo");

        const summary = await res.json();
        state.summary = summary;
        renderizarHUD(summary);
        renderizarPrevisaoInteligente(summary.forecast);
        atualizarSimuladorCenarios();
        renderizarGraficoColunas();
    } catch (err) {
        console.error("Falha ao carregar resumo:", err);
    }
}

function renderizarHUD(summary) {
    const elDeposits = document.getElementById("total-deposits");
    const elExpenses = document.getElementById("total-expenses");
    const elBalance = document.getElementById("net-balance");
    const depositsCount = document.getElementById("deposits-count");
    const expensesCount = document.getElementById("expenses-count");
    const balanceStatus = document.getElementById("balance-status");

    if (elDeposits) elDeposits.innerText = formatCurrency(summary.total_deposits);
    if (elExpenses) elExpenses.innerText = formatCurrency(summary.total_expenses);
    if (elBalance) elBalance.innerText = formatCurrency(summary.net_balance);

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

function renderizarPrevisaoInteligente(forecast) {
    if (!forecast) return;

    const elProjected = document.getElementById("forecast-projected-balance");
    const elDailyExpense = document.getElementById("forecast-daily-expense");
    const elDailyIncome = document.getElementById("forecast-daily-income");
    const elSavingsRate = document.getElementById("forecast-savings-rate");
    const elAdvice = document.getElementById("forecast-message");
    const elBadge = document.getElementById("forecast-badge");

    if (elProjected) elProjected.innerText = formatCurrency(forecast.projected_balance_30d);
    if (elDailyExpense) elDailyExpense.innerText = formatCurrency(forecast.daily_average_expense);
    if (elDailyIncome) elDailyIncome.innerText = formatCurrency(forecast.daily_average_income);
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

// --- Simulador de Cenários ("E se...") ---
function configurarSimuladorCenarios() {
    const slider = document.getElementById("sim-slider");
    const categorySelect = document.getElementById("sim-category");

    if (slider) {
        slider.addEventListener("input", (e) => {
            const pct = e.target.value;
            const pctDisplay = document.getElementById("sim-pct-display");
            if (pctDisplay) pctDisplay.innerText = `${pct}%`;
            atualizarSimuladorCenarios();
        });
    }

    if (categorySelect) {
        categorySelect.addEventListener("change", () => {
            atualizarSimuladorCenarios();
        });
    }
}

function atualizarSimuladorCenarios() {
    if (!state.summary || !state.summary.forecast) return;

    const slider = document.getElementById("sim-slider");
    const categorySelect = document.getElementById("sim-category");
    const elSavingsVal = document.getElementById("sim-savings-val");
    const elNewBalance = document.getElementById("sim-new-balance");

    const pctCut = slider ? parseFloat(slider.value) / 100 : 0.15;
    const selectedCat = categorySelect ? categorySelect.value : "all";

    // Calcula a base de despesas conforme categoria selecionada
    let targetExpense = 0;
    if (selectedCat === "all") {
        targetExpense = state.summary.total_expenses;
    } else {
        const catItem = state.summary.categories.find(c => c.category === selectedCat);
        targetExpense = catItem ? catItem.total_expense : 0;
    }

    // Economia estimada em 30 dias com base no corte percentual
    const monthlyEconomy = targetExpense * pctCut;
    const baseProjectedBalance = state.summary.forecast.projected_balance_30d;
    const newProjectedBalance = baseProjectedBalance + monthlyEconomy;

    if (elSavingsVal) elSavingsVal.innerText = `+ ${formatCurrency(monthlyEconomy)}`;
    if (elNewBalance) elNewBalance.innerText = `Novo saldo projetado: ${formatCurrency(newProjectedBalance)}`;
}

// --- Renderização da Lista de Transações com Empty State Moderno ---
function renderizarListaTransacoes(transactions) {
    const listaContainer = document.getElementById("transactions-list");
    if (!listaContainer) return;

    if (!transactions || transactions.length === 0) {
        listaContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📭</span>
                <h4>Nenhuma movimentação encontrada</h4>
                <p class="empty-msg">Cadastre sua primeira receita ou despesa no formulário ao lado ou use o botão de atalho.</p>
                <button type="button" class="btn-secondary" onclick="focarFormulario()">+ Criar Movimentação</button>
            </div>
        `;
        return;
    }

    let html = "";
    transactions.forEach(tx => {
        const isIncome = tx.type === "income";

        // Tags / Etiquetas
        let tagsHtml = "";
        if (tx.tags && tx.tags.trim()) {
            const rawTags = tx.tags.split(/[\s,]+/).filter(t => t.length > 0);
            tagsHtml = `<div class="tags-container">${rawTags.map(t => {
                const cleanTag = t.startsWith("#") ? t : `#${t}`;
                return `<button type="button" class="tag-badge" onclick="filtrarPorTag('${escapeHtml(cleanTag)}')" title="Filtrar por ${cleanTag}">${escapeHtml(cleanTag)}</button>`;
            }).join("")}</div>`;
        }

        // Data de Vencimento e Liquidação
        let billStatusHtml = "";
        if (tx.due_date) {
            const isPaid = tx.is_paid !== false;
            billStatusHtml = `<span>•</span> <span class="bill-badge ${isPaid ? 'paid' : 'upcoming'}">Venc: ${tx.due_date} (${isPaid ? 'Liquidada' : 'Pendente'})</span>`;
        }

        html += `
            <div class="transaction-item ${tx.type}" data-id="${tx.id}">
                <div class="tx-badge-type">${isIncome ? "ENTRADA" : "SAÍDA"}</div>
                <div class="tx-info">
                    <strong class="tx-title">${escapeHtml(tx.description)}</strong>
                    <span class="tx-meta">
                        <span class="category-tag">${escapeHtml(tx.category)}</span>
                        <span>•</span>
                        <span>📅 ${tx.transaction_date}</span>
                        ${billStatusHtml}
                    </span>
                    ${tagsHtml}
                </div>
                <div class="tx-right">
                    <div class="tx-amount ${tx.type} privacy-value">
                        ${isIncome ? "+" : "-"} ${formatCurrency(tx.amount)}
                    </div>
                    <div class="tx-actions">
                        <button class="btn-action btn-edit" onclick="abrirModalEdicao(${tx.id})" title="Editar movimentação" aria-label="Editar ${escapeHtml(tx.description)}">✏️</button>
                        <button class="btn-action btn-delete" onclick="solicitarExclusao(${tx.id})" title="Remover movimentação" aria-label="Remover ${escapeHtml(tx.description)}">🗑️</button>
                    </div>
                </div>
            </div>
        `;
    });

    listaContainer.innerHTML = html;
}

window.filtrarPorTag = function(tag) {
    state.filters.tag = tag;
    const inputTag = document.getElementById("filter-tag");
    if (inputTag) inputTag.value = tag;
    state.pagination.page = 1;
    buscarTransacoes();
    showCyberToast(`Filtrando movimentações com a tag ${tag}`, "info");
    announceToA11y(`Filtro aplicado para a tag ${tag}`);
};

window.focarFormulario = function() {
    const input = document.getElementById("description");
    if (input) {
        input.focus();
        input.scrollIntoView({ behavior: "smooth", block: "center" });
    }
};

// --- Orçamentos Mensais por Categoria (Budgets) ---
async function carregarOrcamentos() {
    try {
        const res = await fetch(`${API_URL}/budgets/${state.userId}`, getFetchOptions("GET"));
        if (!res.ok) throw new Error("Erro ao carregar orçamentos");
        const budgets = await res.json();
        state.budgets = budgets || [];
        renderizarOrcamentos(state.budgets);
    } catch (err) {
        console.error("Falha ao carregar orçamentos:", err);
    }
}

function renderizarOrcamentos(budgets) {
    const container = document.getElementById("budgets-list");
    if (!container) return;

    if (!budgets || budgets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🎯</span>
                <p class="empty-msg">Nenhum orçamento configurado ainda. Defina limites para categorias como Alimentação, Lazer ou Moradia.</p>
            </div>
        `;
        return;
    }

    let html = "";
    budgets.forEach(b => {
        const pctClamped = Math.min(100, b.percentage_used);
        const statusLabel = b.status === "exceeded" ? "🚨 Estourado" : (b.status === "warning" ? "⚠️ Alerta (>80%)" : "✓ No Limite");

        html += `
            <div class="budget-card budget-status-${b.status}">
                <div class="budget-card-header">
                    <strong>${escapeHtml(b.category)}</strong>
                    <div class="budget-actions">
                        <span class="budget-badge ${b.status}">${statusLabel}</span>
                        <button class="btn-mini-delete" onclick="removerOrcamento(${b.id})" title="Remover orçamento">✕</button>
                    </div>
                </div>
                <div class="budget-progress-track">
                    <div class="budget-progress-fill ${b.status}" style="width: ${pctClamped}%;"></div>
                </div>
                <div class="budget-card-footer">
                    <span>Gasto: <strong>${formatCurrency(b.spent_this_month)}</strong></span>
                    <span>Teto: <strong>${formatCurrency(b.monthly_limit)}</strong> (${b.percentage_used.toFixed(1)}%)</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

window.removerOrcamento = async function(id) {
    if (!confirm("Deseja remover este teto orçamentário?")) return;
    try {
        const res = await fetch(`${API_URL}/budgets/${id}`, getFetchOptions("DELETE"));
        if (!res.ok) throw new Error("Erro ao excluir orçamento");
        showCyberToast("Orçamento removido com sucesso!", "success");
        await carregarOrcamentos();
    } catch (err) {
        showCyberToast(err.message, "error");
    }
};

// --- Metas Financeiras (Savings Goals) ---
async function carregarMetas() {
    try {
        const res = await fetch(`${API_URL}/goals/${state.userId}`, getFetchOptions("GET"));
        if (!res.ok) throw new Error("Erro ao carregar metas");
        const goals = await res.json();
        state.goals = goals || [];
        renderizarMetas(state.goals);
    } catch (err) {
        console.error("Falha ao carregar metas:", err);
    }
}

function renderizarMetas(goals) {
    const container = document.getElementById("goals-list");
    if (!container) return;

    if (!goals || goals.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🏆</span>
                <p class="empty-msg">Nenhuma meta criada ainda. Defina objetivos como Fundo de Emergência, Viagem ou Compra Importante.</p>
            </div>
        `;
        return;
    }

    let html = "";
    goals.forEach(g => {
        const isComplete = g.progress_percentage >= 100;
        html += `
            <div class="goal-card ${isComplete ? 'goal-complete' : ''}">
                <div class="goal-header">
                    <h4>${escapeHtml(g.title)}</h4>
                    <button class="btn-mini-delete" onclick="removerMeta(${g.id})" title="Remover meta">✕</button>
                </div>
                <div class="goal-progress-track">
                    <div class="goal-progress-fill" style="width: ${g.progress_percentage}%;"></div>
                </div>
                <div class="goal-stats">
                    <span>${formatCurrency(g.current_amount)} de ${formatCurrency(g.target_amount)}</span>
                    <strong class="goal-pct">${g.progress_percentage.toFixed(1)}%</strong>
                </div>
                ${g.target_date ? `<span class="goal-date">📅 Alvo: ${g.target_date}</span>` : ''}
                <button class="btn-deposit-goal" onclick="abrirModalAporte(${g.id}, '${escapeHtml(g.title)}')">+ Aportar Valor</button>
            </div>
        `;
    });

    container.innerHTML = html;
}

window.removerMeta = async function(id) {
    if (!confirm("Deseja remover esta meta financeira?")) return;
    try {
        const res = await fetch(`${API_URL}/goals/${id}`, getFetchOptions("DELETE"));
        if (!res.ok) throw new Error("Erro ao excluir meta");
        showCyberToast("Meta removida com sucesso!", "success");
        await carregarMetas();
    } catch (err) {
        showCyberToast(err.message, "error");
    }
};

window.abrirModalAporte = function(id, title) {
    document.getElementById("deposit-goal-id").value = id;
    const titleEl = document.getElementById("deposit-goal-title");
    if (titleEl) titleEl.innerText = `Aportar na meta: ${title}`;
    abrirModal(document.getElementById("deposit-goal-modal"));
};

// --- Gráfico de Colunas Analítico ---
function renderizarGraficoColunas() {
    const chartContainer = document.getElementById("column-chart");
    if (!chartContainer || !state.summary) return;

    const categories = state.summary.categories || [];
    if (categories.length === 0) {
        chartContainer.innerHTML = `<p class="empty-msg">Sem movimentações suficientes para gerar o gráfico.</p>`;
        return;
    }

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
        chartData = categories
            .map(c => ({ category: c.category, value: c.total_expense + c.total_income, type: "both" }))
            .filter(c => c.value > 0);
    }

    if (chartData.length === 0) {
        chartContainer.innerHTML = `<p class="empty-msg">Nenhum dado encontrado para a visualização selecionada.</p>`;
        return;
    }

    const maxValue = Math.max(...chartData.map(d => d.value), 1);
    const totalVolume = chartData.reduce((acc, d) => acc + d.value, 0);

    let html = "";
    chartData.forEach(d => {
        const heightPct = Math.max(8, Math.round((d.value / maxValue) * 100));
        const sharePct = ((d.value / totalVolume) * 100).toFixed(1);
        const valFormatted = formatCurrency(d.value);

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
function configurarFormularioTransacao() {
    const form = document.getElementById("transaction-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById("btn-submit-tx");
        const originalText = submitBtn.innerText;
        submitBtn.disabled = true;
        submitBtn.innerText = "Registrando...";

        const payload = {
            user_id: state.userId,
            type: document.getElementById("type").value,
            amount: parseFloat(document.getElementById("amount").value),
            description: document.getElementById("description").value,
            category: document.getElementById("category").value,
            tags: document.getElementById("tags") ? document.getElementById("tags").value.trim() : "",
            due_date: document.getElementById("due_date") && document.getElementById("due_date").value ? document.getElementById("due_date").value : null,
            is_paid: document.getElementById("is_paid") ? document.getElementById("is_paid").checked : true,
            transaction_date: document.getElementById("transaction_date").value || new Date().toISOString().split("T")[0]
        };

        try {
            const res = await fetch(`${API_URL}/transactions`, getFetchOptions("POST", payload));
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || "Erro ao registrar transação.");

            showCyberToast("Movimentação registrada com sucesso!", "success");
            form.reset();
            document.getElementById("transaction_date").value = new Date().toISOString().split("T")[0];
            const isPaidCheck = document.getElementById("is_paid");
            if (isPaidCheck) isPaidCheck.checked = true;

            await carregarTodosOsDados();
        } catch (err) {
            showCyberToast(err.message, "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = originalText;
        }
    });
}

// --- Exportação de Dados (CSV / JSON) ---
function configurarExportacao() {
    const btnCsv = document.getElementById("btn-export-csv");
    const btnJson = document.getElementById("btn-export-json");

    if (btnCsv) {
        btnCsv.addEventListener("click", async () => {
            try {
                showCyberToast("Gerando exportação CSV...", "info");
                const res = await fetch(`${API_URL}/transactions/${state.userId}/export?format=csv`, getFetchOptions("GET"));
                if (!res.ok) throw new Error("Erro ao gerar CSV.");
                const blob = await res.blob();
                baixarArquivo(blob, `finance_tracker_${state.userId}_${new Date().toISOString().slice(0, 10)}.csv`);
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
                const res = await fetch(`${API_URL}/transactions/${state.userId}/export?format=json`, getFetchOptions("GET"));
                if (!res.ok) throw new Error("Erro ao gerar JSON.");
                const data = await res.json();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
                baixarArquivo(blob, `finance_tracker_${state.userId}_${new Date().toISOString().slice(0, 10)}.json`);
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

// --- Modais: Edição, Exclusão, Orçamentos e Metas ---
function configurarModais() {
    const editModal = document.getElementById("edit-modal");
    const confirmModal = document.getElementById("confirm-modal");
    const budgetModal = document.getElementById("budget-modal");
    const goalModal = document.getElementById("goal-modal");
    const depositGoalModal = document.getElementById("deposit-goal-modal");

    // Gatilhos de Abertura
    document.getElementById("btn-open-budget-modal")?.addEventListener("click", () => abrirModal(budgetModal));
    document.getElementById("btn-open-goal-modal")?.addEventListener("click", () => abrirModal(goalModal));

    // Fechamento de Modais
    document.getElementById("btn-close-edit-modal")?.addEventListener("click", () => fecharModal(editModal));
    document.getElementById("btn-cancel-edit")?.addEventListener("click", () => fecharModal(editModal));

    document.getElementById("btn-close-confirm-modal")?.addEventListener("click", () => fecharModal(confirmModal));
    document.getElementById("btn-confirm-cancel")?.addEventListener("click", () => fecharModal(confirmModal));

    document.getElementById("btn-close-budget-modal")?.addEventListener("click", () => fecharModal(budgetModal));
    document.getElementById("btn-cancel-budget")?.addEventListener("click", () => fecharModal(budgetModal));

    document.getElementById("btn-close-goal-modal")?.addEventListener("click", () => fecharModal(goalModal));
    document.getElementById("btn-cancel-goal")?.addEventListener("click", () => fecharModal(goalModal));

    document.getElementById("btn-close-deposit-goal-modal")?.addEventListener("click", () => fecharModal(depositGoalModal));
    document.getElementById("btn-cancel-deposit-goal")?.addEventListener("click", () => fecharModal(depositGoalModal));

    // Submissão de Edição de Transação
    document.getElementById("edit-transaction-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const id = document.getElementById("edit-id").value;
        const payload = {
            type: document.getElementById("edit-type").value,
            amount: parseFloat(document.getElementById("edit-amount").value),
            description: document.getElementById("edit-description").value,
            category: document.getElementById("edit-category").value,
            tags: document.getElementById("edit-tags") ? document.getElementById("edit-tags").value.trim() : "",
            due_date: document.getElementById("edit-due-date") && document.getElementById("edit-due-date").value ? document.getElementById("edit-due-date").value : null,
            is_paid: document.getElementById("edit-is-paid") ? document.getElementById("edit-is-paid").checked : true,
            transaction_date: document.getElementById("edit-date").value
        };

        try {
            const res = await fetch(`${API_URL}/transactions/${id}`, getFetchOptions("PUT", payload));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Erro ao salvar alterações.");

            showCyberToast("Movimentação atualizada com sucesso!", "success");
            fecharModal(editModal);
            await carregarTodosOsDados();
        } catch (err) {
            showCyberToast(err.message, "error");
        }
    });

    // Submissão de Confirmação de Exclusão
    document.getElementById("btn-confirm-delete")?.addEventListener("click", async () => {
        if (!state.pendingDeleteTxId) return;
        try {
            const res = await fetch(`${API_URL}/transactions/${state.pendingDeleteTxId}`, getFetchOptions("DELETE"));
            if (!res.ok) throw new Error("Erro ao excluir transação.");

            showCyberToast("Movimentação excluída com sucesso!", "success");
            fecharModal(confirmModal);
            state.pendingDeleteTxId = null;
            await carregarTodosOsDados();
        } catch (err) {
            showCyberToast(err.message, "error");
        }
    });

    // Submissão de Orçamento de Categoria
    document.getElementById("budget-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            category: document.getElementById("budget-category").value,
            monthly_limit: parseFloat(document.getElementById("budget-limit").value)
        };

        try {
            const res = await fetch(`${API_URL}/budgets`, getFetchOptions("POST", payload));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Erro ao salvar orçamento.");

            showCyberToast(`Teto orçamentário para ${payload.category} definido!`, "success");
            document.getElementById("budget-form").reset();
            fecharModal(budgetModal);
            await carregarOrcamentos();
        } catch (err) {
            showCyberToast(err.message, "error");
        }
    });

    // Submissão de Nova Meta
    document.getElementById("goal-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
            title: document.getElementById("goal-title").value,
            target_amount: parseFloat(document.getElementById("goal-target").value),
            current_amount: parseFloat(document.getElementById("goal-current").value || 0),
            target_date: document.getElementById("goal-date").value || null
        };

        try {
            const res = await fetch(`${API_URL}/goals`, getFetchOptions("POST", payload));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Erro ao criar meta.");

            showCyberToast(`Meta "${payload.title}" criada com sucesso!`, "success");
            document.getElementById("goal-form").reset();
            fecharModal(goalModal);
            await carregarMetas();
        } catch (err) {
            showCyberToast(err.message, "error");
        }
    });

    // Submissão de Aporte em Meta
    document.getElementById("deposit-goal-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const id = document.getElementById("deposit-goal-id").value;
        const addAmount = parseFloat(document.getElementById("deposit-goal-amount").value);

        try {
            const res = await fetch(`${API_URL}/goals/${id}`, getFetchOptions("PUT", { add_amount: addAmount }));
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Erro ao registrar aporte.");

            showCyberToast(`Aporte de ${formatCurrency(addAmount)} registrado!`, "success");
            document.getElementById("deposit-goal-form").reset();
            fecharModal(depositGoalModal);
            await carregarMetas();
        } catch (err) {
            showCyberToast(err.message, "error");
        }
    });
}

let lastFocusedElement = null;

function fecharModal(modal) {
    if (modal) {
        modal.classList.add("hidden");
        if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
            lastFocusedElement.focus();
        }
    }
}

function abrirModal(modal) {
    if (modal) {
        lastFocusedElement = document.activeElement;
        modal.classList.remove("hidden");
        const focusable = modal.querySelector('button:not([disabled]), input:not([disabled]), select:not([disabled]), [href]');
        if (focusable) focusable.focus();
    }
}

function fecharTodosModais() {
    document.querySelectorAll(".modal-overlay").forEach(m => m.classList.add("hidden"));
    if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
        lastFocusedElement.focus();
    }
}

window.abrirModalEdicao = function(id) {
    const tx = state.transactions.find(t => t.id === id);
    if (!tx) return;

    document.getElementById("edit-id").value = tx.id;
    document.getElementById("edit-type").value = tx.type;
    document.getElementById("edit-amount").value = tx.amount;
    document.getElementById("edit-description").value = tx.description;
    document.getElementById("edit-category").value = tx.category;
    document.getElementById("edit-date").value = tx.transaction_date;
    
    const editTags = document.getElementById("edit-tags");
    if (editTags) editTags.value = tx.tags || "";

    const editDueDate = document.getElementById("edit-due-date");
    if (editDueDate) editDueDate.value = tx.due_date || "";

    const editIsPaid = document.getElementById("edit-is-paid");
    if (editIsPaid) editIsPaid.checked = tx.is_paid !== false;

    abrirModal(document.getElementById("edit-modal"));
};

window.solicitarExclusao = function(id) {
    state.pendingDeleteTxId = id;
    abrirModal(document.getElementById("confirm-modal"));
};

// ==========================================================================
// ACESSIBILIDADE (WCAG 2.1 AA) — FOCUS TRAP & LEITOR DE TELA
// ==========================================================================

function configurarFocusTrapModais() {
    const modais = document.querySelectorAll(".modal-overlay");
    modais.forEach(modal => {
        modal.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                const focusables = modal.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
                if (!focusables.length) return;
                const first = focusables[0];
                const last = focusables[focusables.length - 1];

                if (e.shiftKey) {
                    if (document.activeElement === first) {
                        last.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === last) {
                        first.focus();
                        e.preventDefault();
                    }
                }
            }
        });
    });
}

function announceToA11y(msg) {
    const announcer = document.getElementById("a11y-announcer");
    if (announcer) {
        announcer.innerText = "";
        setTimeout(() => { announcer.innerText = msg; }, 50);
    }
}

// ==========================================================================
// MODO PRIVACIDADE (CONFIDENCIALIDADE VISUAL)
// ==========================================================================

function configurarModoPrivacidade() {
    const btnPrivacy = document.getElementById("btn-privacy-toggle");
    const privacyIcon = document.getElementById("privacy-icon");

    if (state.privacyMode) {
        document.body.classList.add("privacy-masked");
        if (privacyIcon) privacyIcon.innerText = "🙈";
        if (btnPrivacy) btnPrivacy.classList.add("active");
    }

    if (btnPrivacy) {
        btnPrivacy.addEventListener("click", () => {
            state.privacyMode = !state.privacyMode;
            localStorage.setItem("privacy_mode", state.privacyMode ? "true" : "false");

            if (state.privacyMode) {
                document.body.classList.add("privacy-masked");
                if (privacyIcon) privacyIcon.innerText = "🙈";
                btnPrivacy.classList.add("active");
                showCyberToast("Modo Privacidade Ativado (Valores Ocultos)", "info");
                announceToA11y("Modo de privacidade ativado. Os valores monetários estão ocultos.");
            } else {
                document.body.classList.remove("privacy-masked");
                if (privacyIcon) privacyIcon.innerText = "👁️";
                btnPrivacy.classList.remove("active");
                showCyberToast("Modo Privacidade Desativado (Valores Visíveis)", "info");
                announceToA11y("Modo de privacidade desativado. Os valores estão visíveis.");
            }

            // Re-renderiza componentes com formatação monetária
            if (state.summary) {
                renderizarHUD(state.summary);
                renderizarPrevisaoInteligente(state.summary.forecast);
                atualizarSimuladorCenarios();
            }
            renderizarListaTransacoes(state.transactions);
            renderizarOrcamentos(state.budgets);
            renderizarMetas(state.goals);
            if (state.bills) renderizarContasAlertas(state.bills);
            if (state.timelineData) {
                const balBadge = document.getElementById("timeline-current-balance");
                if (balBadge) balBadge.innerText = `Patrimônio: ${formatCurrency(state.timelineData.ending_balance)}`;
                renderGraficoLinhaTempo(state.timelineData.points);
            }
        });
    }
}

// ==========================================================================
// COMANDOS DE VOZ (WEB SPEECH API)
// ==========================================================================

function configurarComandosVoz() {
    const btnVoice = document.getElementById("btn-voice-command");
    if (!btnVoice) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        btnVoice.title = "Reconhecimento de voz não suportado neste navegador.";
        btnVoice.style.opacity = "0.5";
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "pt-BR";
    recognition.continuous = false;
    recognition.interimResults = false;

    let isRecording = false;

    btnVoice.addEventListener("click", () => {
        if (isRecording) {
            recognition.stop();
            return;
        }
        try {
            recognition.start();
            isRecording = true;
            btnVoice.classList.add("recording");
            showCyberToast("🎙️ Ouvindo... Fale sua movimentação (Ex: 'Gastei 50 em almoço')", "info");
            announceToA11y("Microfone ativado. Fale o tipo, valor e descrição da sua movimentação.");
        } catch (e) {
            console.warn(e);
        }
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript.toLowerCase();
        console.log("[Voz reconhecida]:", transcript);
        processarComandoVoz(transcript);
    };

    recognition.onend = () => {
        isRecording = false;
        btnVoice.classList.remove("recording");
    };

    recognition.onerror = () => {
        isRecording = false;
        btnVoice.classList.remove("recording");
        showCyberToast("Não foi possível reconhecer o áudio. Tente falar novamente.", "warning");
    };
}

function processarComandoVoz(text) {
    // 1. Identifica Tipo
    let type = "expense";
    if (/recebi|ganhei|salário|salario|depósito|deposito|renda|dividendos|freela/i.test(text)) {
        type = "income";
    }

    // 2. Extrai Valor
    const amountMatch = text.match(/(\d+(?:[,\.]\d{1,2})?)/);
    const amount = amountMatch ? parseFloat(amountMatch[1].replace(",", ".")) : null;

    // 3. Categoria Inteligente
    let category = "Outros";
    if (/almoço|almoco|jantar|comida|mercado|restaurante|café|lanche|pizza|supermercado/i.test(text)) category = "Alimentação";
    else if (/aluguel|condomínio|condominio|luz|água|agua|internet|iptu|gás|gas|casa/i.test(text)) category = "Moradia";
    else if (/uber|gasolina|combustível|combustivel|ônibus|onibus|metrô|metro|estacionamento|pedágio|carro/i.test(text)) category = "Transporte";
    else if (/curso|livro|faculdade|escola|estudo|udemy|apostila/i.test(text)) category = "Estudo";
    else if (/cinema|jogo|steam|viagem|passeio|festa|bar|balada|lazer/i.test(text)) category = "Lazer";
    else if (/farmácia|farmacia|médico|medico|remédio|remedio|hospital|dentista|exame|saúde|saude/i.test(text)) category = "Saúde";
    else if (/salário|salario|freela|freelance|bônus|cliente|trabalho/i.test(text)) category = "Trabalho";
    else if (/investimento|ações|acoes|fii|tesouro|cripto|bitcoin/i.test(text)) category = "Investimentos";

    // 4. Descrição Normalizada
    let desc = text
        .replace(/^(gastei|paguei|comprei|recebi|ganhei|coloquei)\s*/i, "")
        .replace(/(\d+(?:[,\.]\d{1,2})?)\s*(reais|euros|dólares|conto|pila)?/i, "")
        .replace(/^(em|no|na|de|com)\s*/i, "")
        .trim();

    if (!desc) desc = `${category} (Voz)`;
    desc = desc.charAt(0).toUpperCase() + desc.slice(1);

    // Preenche o formulário
    const elType = document.getElementById("type");
    const elAmount = document.getElementById("amount");
    const elDesc = document.getElementById("description");
    const elCat = document.getElementById("category");

    if (elType) elType.value = type;
    if (elAmount && amount) elAmount.value = amount;
    if (elDesc) elDesc.value = desc;
    if (elCat) elCat.value = category;

    window.focarFormulario();

    const resumo = `${type === 'income' ? 'Receita' : 'Despesa'} de ${amount ? amount : ''} em "${desc}" identificada!`;
    showCyberToast(`🎙️ ${resumo}`, "success");
    announceToA11y(resumo);
}

// ==========================================================================
// PWA & NOTIFICAÇÕES WEB PUSH
// ==========================================================================

function inicializarPWA() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js')
                .then(reg => console.log('[PWA] Service Worker registrado:', reg.scope))
                .catch(err => console.warn('[PWA] Falha ao registrar Service Worker:', err));
        });
    }
}

function configurarNotificacoesPush() {
    const btnPush = document.getElementById("btn-push-toggle");
    const btnReq = document.getElementById("btn-request-notification-perm");
    const pushIcon = document.getElementById("push-icon");

    function atualizarEstadoPush() {
        if (!("Notification" in window)) {
            if (btnPush) btnPush.style.display = "none";
            return;
        }
        if (Notification.permission === "granted") {
            if (pushIcon) pushIcon.innerText = "🔔";
            if (btnPush) btnPush.classList.add("active");
            if (btnReq) {
                btnReq.innerText = "✓ Notificações Ativas";
                btnReq.disabled = true;
            }
        } else {
            if (pushIcon) pushIcon.innerText = "🔕";
            if (btnPush) btnPush.classList.remove("active");
        }
    }

    atualizarEstadoPush();

    const solicitarPermissao = async () => {
        if (!("Notification" in window)) {
            showCyberToast("Seu navegador não suporta notificações Web Push.", "warning");
            return;
        }

        try {
            const permission = await Notification.requestPermission();
            atualizarEstadoPush();
            if (permission === "granted") {
                showCyberToast("🔔 Notificações ativadas! Você receberá lembretes de contas e vencimentos.", "success");
                announceToA11y("Notificações push ativadas com sucesso.");

                if (navigator.serviceWorker && navigator.serviceWorker.controller) {
                    navigator.serviceWorker.controller.postMessage({
                        type: 'SCHEDULE_LOCAL_NOTIFICATION',
                        title: 'FinanceTracker Ativado!',
                        body: 'Lembretes de contas a vencer e controle financeiro sincronizados.',
                        delayMs: 300
                    });
                }
            } else {
                showCyberToast("Permissão de notificação negada no navegador.", "warning");
            }
        } catch (e) {
            console.warn(e);
        }
    };

    if (btnPush) btnPush.addEventListener("click", solicitarPermissao);
    if (btnReq) btnReq.addEventListener("click", solicitarPermissao);
}

function dispararLembreteSegundoPlano(data) {
    if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return;

    if (data.today_count > 0 || data.overdue_count > 0) {
        const title = data.overdue_count > 0 ? '⚠️ Contas Atrasadas!' : '🟡 Conta Vencendo Hoje!';
        const body = `Você possui ${data.overdue_count > 0 ? `${data.overdue_count} conta(s) em atraso` : `${data.today_count} conta(s) que vencem hoje`}. Total pendente: ${formatCurrency(data.total_pending_amount)}.`;

        navigator.serviceWorker.controller.postMessage({
            type: 'SCHEDULE_LOCAL_NOTIFICATION',
            title,
            body,
            delayMs: 1500
        });
    }
}

// ==========================================================================
// MÓDULO DE ALERTAS DE VENCIMENTO & CONTAS
// ==========================================================================

async function carregarContasAlertas() {
    try {
        const res = await fetch(`${API_URL}/transactions/${state.userId}/bills`, getFetchOptions("GET"));
        if (!res.ok) return;
        const data = await res.json();
        state.bills = data.bills || [];

        // Atualiza pílulas do cabeçalho
        const pOverdue = document.getElementById("pill-overdue");
        const pToday = document.getElementById("pill-today");
        const pUpcoming = document.getElementById("pill-upcoming");
        if (pOverdue) pOverdue.innerText = `🔴 ${data.overdue_count} Atrasada${data.overdue_count === 1 ? '' : 's'}`;
        if (pToday) pToday.innerText = `🟡 ${data.today_count} Vencendo Hoje`;
        if (pUpcoming) pUpcoming.innerText = `🔵 ${data.upcoming_count} Próxima${data.upcoming_count === 1 ? '' : 's'}`;

        renderizarContasAlertas(state.bills);
    } catch (err) {
        console.error("Falha ao carregar alertas de contas:", err);
    }
}

function renderizarContasAlertas(bills) {
    const container = document.getElementById("bills-list");
    if (!container) return;

    if (!bills || bills.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🔔</span>
                <p class="empty-msg">Nenhuma conta com data de vencimento registrada. Defina uma data de vencimento ao criar despesas para ativar lembretes.</p>
            </div>
        `;
        return;
    }

    let html = "";
    bills.forEach(bill => {
        html += `
            <div class="bill-card status-${bill.status}">
                <div class="bill-header">
                    <span class="bill-title">${escapeHtml(bill.description)}</span>
                    <span class="bill-badge ${bill.status}">${escapeHtml(bill.label)}</span>
                </div>
                <div class="bill-body">
                    <span class="bill-amount privacy-value text-${bill.type}">
                        ${bill.type === 'income' ? '+' : '-'} ${formatCurrency(bill.amount)}
                    </span>
                    <span class="bill-date">📅 ${bill.due_date}</span>
                </div>
                <div class="bill-actions">
                    <span class="category-tag">${escapeHtml(bill.category)}</span>
                    <button type="button" class="btn-toggle-paid" onclick="alternarStatusConta(${bill.id})" aria-label="Marcar como ${bill.is_paid ? 'pendente' : 'pago'}">
                        ${bill.is_paid ? '↩ Marcar Pendente' : '✓ Marcar como Paga'}
                    </button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

window.alternarStatusConta = async function(id) {
    try {
        const res = await fetch(`${API_URL}/transactions/${id}/toggle-paid`, getFetchOptions("PATCH"));
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Erro ao alterar status.");

        showCyberToast(data.message, "success");
        await Promise.all([
            carregarContasAlertas(),
            buscarTransacoes(),
            buscarResumoEPrevisao()
        ]);
    } catch (err) {
        showCyberToast(err.message, "error");
    }
};

// ==========================================================================
// EVOLUÇÃO PATRIMONIAL (LINHA DO TEMPO)
// ==========================================================================

async function carregarEvolucaoPatrimonial() {
    try {
        const res = await fetch(`${API_URL}/transactions/${state.userId}/timeline?days=30`, getFetchOptions("GET"));
        if (!res.ok) return;
        const data = await res.json();
        state.timelineData = data;

        const balBadge = document.getElementById("timeline-current-balance");
        if (balBadge) {
            balBadge.innerText = `Patrimônio: ${formatCurrency(data.ending_balance)}`;
        }

        renderGraficoLinhaTempo(data.points);
    } catch (err) {
        console.error("Falha ao carregar evolução patrimonial:", err);
    }
}

function renderGraficoLinhaTempo(points) {
    const canvas = document.getElementById("timelineChart");
    if (!canvas || !window.Chart) return;

    if (state.timelineChartInstance) {
        state.timelineChartInstance.destroy();
    }

    if (!points || points.length === 0) return;

    const labels = points.map(p => p.date);
    const dataValues = points.map(p => p.cumulative_balance);

    const ctx = canvas.getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, "rgba(0, 240, 255, 0.45)");
    gradient.addColorStop(1, "rgba(0, 240, 255, 0.0)");

    state.timelineChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Saldo Acumulado',
                data: dataValues,
                borderColor: '#00f0ff',
                backgroundColor: gradient,
                borderWidth: 3,
                fill: true,
                tension: 0.35,
                pointBackgroundColor: '#bd00ff',
                pointBorderColor: '#00f0ff',
                pointRadius: 4,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Saldo Acumulado: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8', font: { size: 11 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) { return formatCurrency(value); }
                    }
                }
            }
        }
    });
}

// ==========================================================================
// MOBILE BOTTOM NAVIGATION
// ==========================================================================

function configurarNavegacaoMobile() {
    const navItems = document.querySelectorAll(".bottom-nav-item[data-nav-target]");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            navItems.forEach(n => n.classList.remove("active"));
            item.classList.add("active");
            const targetId = item.getAttribute("data-nav-target");
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    const btnNewMobile = document.getElementById("btn-mobile-new-tx");
    if (btnNewMobile) {
        btnNewMobile.addEventListener("click", () => {
            window.focarFormulario();
        });
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m];
    });
}
