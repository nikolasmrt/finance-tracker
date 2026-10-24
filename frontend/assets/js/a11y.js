/**
 * MÓDULO DE ACESSIBILIDADE (WCAG 2.1 AA) — FINANCETRACKER 3.0
 * Inclui:
 * - Anunciador ARIA Live (`announceToScreenReader`)
 * - Focus Trap cíclico em todos os modais (`.modal-overlay`)
 * - Atalhos globais de teclado (`N` Nova Transação, `ESC` Fechar Modal, `/` Buscar)
 */

window.A11y = (function () {
    let lastFocusedElement = null;

    function announceToScreenReader(message) {
        const announcer = document.getElementById("a11y-announcer");
        if (!announcer) return;
        announcer.textContent = "";
        setTimeout(() => {
            announcer.textContent = message;
        }, 60);
    }

    function getFocusableElements(container) {
        if (!container) return [];
        return Array.from(
            container.querySelectorAll(
                'button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
            )
        ).filter((el) => el.offsetParent !== null);
    }

    function trapModalFocus(modal) {
        lastFocusedElement = document.activeElement;
        const focusable = getFocusableElements(modal);
        if (focusable.length > 0) {
            setTimeout(() => focusable[0].focus(), 50);
        }
    }

    function releaseModalFocus() {
        if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
            setTimeout(() => lastFocusedElement.focus(), 40);
            lastFocusedElement = null;
        }
    }

    function initFocusTrap() {
        document.addEventListener("keydown", (e) => {
            const activeModal = document.querySelector(".modal-overlay:not(.hidden)");
            if (!activeModal) return;

            if (e.key === "Escape") {
                e.preventDefault();
                activeModal.classList.add("hidden");
                releaseModalFocus();
                announceToScreenReader("Janela modal fechada.");
                return;
            }

            if (e.key !== "Tab") return;

            const focusable = getFocusableElements(activeModal);
            if (focusable.length === 0) return;

            const firstEl = focusable[0];
            const lastEl = focusable[focusable.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === firstEl || !activeModal.contains(document.activeElement)) {
                    e.preventDefault();
                    lastEl.focus();
                }
            } else {
                if (document.activeElement === lastEl || !activeModal.contains(document.activeElement)) {
                    e.preventDefault();
                    firstEl.focus();
                }
            }
        });

        // Observa abertura de modais para capturar o foco automaticamente
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((m) => {
                if (m.type === "attributes" && m.attributeName === "class") {
                    const target = m.target;
                    if (target.classList.contains("modal-overlay")) {
                        if (!target.classList.contains("hidden")) {
                            trapModalFocus(target);
                        } else {
                            releaseModalFocus();
                        }
                    }
                }
            });
        });

        document.querySelectorAll(".modal-overlay").forEach((modal) => {
            observer.observe(modal, { attributes: true, attributeFilter: ["class"] });
        });
    }

    function initKeyboardShortcuts({ onNewTransaction, onFocusSearch } = {}) {
        document.addEventListener("keydown", (e) => {
            const tag = (e.target.tagName || "").toUpperCase();
            const isTyping =
                tag === "INPUT" ||
                tag === "TEXTAREA" ||
                tag === "SELECT" ||
                e.target.isContentEditable;

            if (isTyping || e.ctrlKey || e.metaKey || e.altKey) return;

            const activeModal = document.querySelector(".modal-overlay:not(.hidden)");
            if (activeModal) return;

            if (e.key === "n" || e.key === "N") {
                e.preventDefault();
                if (typeof onNewTransaction === "function") {
                    onNewTransaction();
                }
                announceToScreenReader("Formulário de nova transação focado.");
            } else if (e.key === "/") {
                e.preventDefault();
                if (typeof onFocusSearch === "function") {
                    onFocusSearch();
                }
                announceToScreenReader("Campo de busca focado.");
            }
        });
    }

    return {
        announce: announceToScreenReader,
        initFocusTrap,
        initKeyboardShortcuts,
        trapModalFocus,
        releaseModalFocus,
    };
})();
