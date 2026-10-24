/**
 * MÓDULO DE COMANDOS DE VOZ (WEB SPEECH API) — FINANCETRACKER 3.0
 * Permite ditar frases naturais como:
 * - "Gastei 45 reais em almoço"
 * - "Recebi 3500 de salário"
 * - "Paguei 120,90 conta de internet"
 * Preenche automaticamente valor, tipo, categoria sugerida e descrição.
 */

window.VoiceInput = (function () {
    const CATEGORY_KEYWORDS = {
        Alimentação: ["almoço", "almoco", "jantar", "lanche", "mercado", "supermercado", "ifd", "ifood", "padaria", "restaurante", "café", "cafe", "pizza"],
        Transporte: ["uber", "99", "gasolina", "combustível", "combustivel", "ônibus", "onibus", "metrô", "metro", "estacionamento", "pedágio", "pedagio"],
        Moradia: ["aluguel", "condomínio", "condominio", "luz", "energia", "água", "agua", "internet", "fibra", "gás", "gas", "iptu"],
        Saúde: ["farmácia", "farmacia", "remédio", "remedio", "consulta", "médico", "medico", "exame", "academia", "dentista"],
        Lazer: ["cinema", "show", "viagem", "netflix", "spotify", "jogo", "game", "bar", "festa", "passeio"],
        Educação: ["curso", "livro", "faculdade", "escola", "mensalidade", "aula", "certificação"],
        Trabalho: ["salário", "salario", "freela", "freelance", "projeto", "consultoria", "bônus", "bonus", "comissão"],
        Investimentos: ["dividendo", "dividendos", "rendimento", "tesouro", "ações", "acoes", "cdb", "fii", "cripto"],
    };

    function parseSpokenTransaction(transcript) {
        const raw = (transcript || "").trim();
        const lower = raw.toLowerCase();

        // 1. Determina o tipo (receita ou despesa)
        const isIncome = /\b(recebi|ganhei|salário|salario|depósito|deposito|entrada|rendimento|freela|reembolso|pix recebido)\b/i.test(lower);
        const type = isIncome ? "income" : "expense";

        // 2. Extrai o valor numérico (ex: "25,50", "120 reais", "1.500,00")
        let amount = null;
        const numberMatch = lower.match(/(\d+(?:[.,]\d{1,2})?)/);
        if (numberMatch) {
            const normalized = numberMatch[1].replace(",", ".");
            const parsed = parseFloat(normalized);
            if (!isNaN(parsed) && parsed > 0) {
                amount = parsed.toFixed(2);
            }
        }

        // 3. Infere categoria por palavras-chave
        let matchedCategory = isIncome ? "Trabalho" : "Outros";
        for (const [category, words] of Object.entries(CATEGORY_KEYWORDS)) {
            if (words.some((w) => lower.includes(w))) {
                matchedCategory = category;
                break;
            }
        }

        // 4. Limpa a descrição para ficar legível
        let description = raw
            .replace(/^(gastei|paguei|comprei|recebi|ganhei|adicione|adicionar|lançar|lancar)\s+/i, "")
            .replace(/\b(\d+(?:[.,]\d{1,2})?)\s*(reais|real|euros|euro|dólares|dolares|r\$|\$)?\s*(em|de|no|na|com|para|por)?\s*/i, "")
            .trim();

        if (!description) {
            description = raw.charAt(0).toUpperCase() + raw.slice(1);
        } else {
            description = description.charAt(0).toUpperCase() + description.slice(1);
        }

        return {
            type,
            amount,
            category: matchedCategory,
            description: description.slice(0, 120),
            raw,
        };
    }

    function init({ buttonId = "btn-voice-input", statusId = "voice-status-banner", onParsed, onToast } = {}) {
        const btn = document.getElementById(buttonId);
        const banner = document.getElementById(statusId);
        if (!btn) return;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            btn.addEventListener("click", () => {
                if (typeof onToast === "function") {
                    onToast("O seu navegador não suporta reconhecimento de voz nativo (teste no Chrome ou Edge).", "warning");
                }
            });
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = "pt-BR";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        let isListening = false;

        btn.addEventListener("click", () => {
            if (isListening) {
                recognition.stop();
                return;
            }
            try {
                recognition.start();
            } catch (err) {
                console.warn("Reconhecimento já iniciado:", err);
            }
        });

        recognition.addEventListener("start", () => {
            isListening = true;
            btn.classList.add("listening");
            btn.setAttribute("aria-pressed", "true");
            if (banner) banner.classList.remove("hidden");
            if (window.A11y) window.A11y.announce("Microfone ativado. Fale a sua transação agora.");
        });

        recognition.addEventListener("end", () => {
            isListening = false;
            btn.classList.remove("listening");
            btn.setAttribute("aria-pressed", "false");
            if (banner) banner.classList.add("hidden");
        });

        recognition.addEventListener("result", (event) => {
            const transcript = event.results[0][0].transcript;
            const parsed = parseSpokenTransaction(transcript);
            if (typeof onParsed === "function") {
                onParsed(parsed);
            }
        });

        recognition.addEventListener("error", (event) => {
            isListening = false;
            btn.classList.remove("listening");
            btn.setAttribute("aria-pressed", "false");
            if (banner) banner.classList.add("hidden");
            if (typeof onToast === "function") {
                onToast(`Não foi possível captar a voz (${event.error}). Tente novamente.`, "warning");
            }
        });
    }

    return {
        init,
        parseSpokenTransaction,
    };
})();
