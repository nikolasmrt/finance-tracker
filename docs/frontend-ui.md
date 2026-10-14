# 🎨 Design System & UI Guide — Cyberpunk Neon Glass

O front-end do **FinanceTracker** rompe com as interfaces tradicionais de painéis financeiros, adotando uma estética futurista imersiva:

## 1. Diretrizes Visuais
- **Glassmorphism:** Superfícies translúcidas com efeito de desfoque de fundo (`backdrop-filter: blur(12px)`), conferindo profundidade e elegância.
- **Identidade Neon:** Utilização de cores de destaque vibrantes com sombras difusas (`box-shadow`):
  - **Azul Ciano (`#00f0ff`):** Indicadores de saldo geral, bordas ativas e elementos principais.
  - **Roxo Cibernético (`#bd00ff`):** Gradientes em títulos, botões de submissão e logotipos vetoriais SVG.
  - **Verde Sucesso (`#00ff66`):** Entradas/depósitos financeiros e barras positivas.
  - **Vermelho Perigo (`#ff3366`):** Saídas/gastos, alertas e botões de exclusão.

## 2. Componentes Dinâmicos e Reativos
- **HUD Financeiro:** Cartões de resumo que recalculam receitas, despesas e saldo líquido instantaneamente a cada alteração.
- **Gráfico de Colunas Analítico:** Renderizado dinamicamente com base nas categorias das transações cadastradas, calculando alturas proporcionais de forma reativa e exibindo tooltips informativos.
- **Gestão de Sessão Local:** O ID do utilizador autenticado é gerido via `localStorage`, garantindo isolamento de dados entre contas e redirecionamento automático para o fluxo de autenticação (`login.html` / `register.html`).