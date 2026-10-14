# Projeto de Interface — FinanceTracker

O projeto de interface do **FinanceTracker** foi desenhado com foco na experiência do usuário (*UX/UI*), priorizando a simplicidade, agilidade no registro de movimentações diárias e clareza visual através de um painel analítico (*Dashboard*) em modo escuro (*Dark Mode*).

## 1. Fluxo de Usuário (User Flow)

O diagrama abaixo ilustra a jornada do usuário dentro da aplicação:

1. **Tela de Autenticação (Login / Registro):** O usuário acessa o sistema. Se não possuir cadastro, realiza o registro informando nome, e-mail e senha. Caso contrário, efetua o login.
2. **Dashboard Principal (HUD Financeiro):** Após a autenticação bem-sucedida, o usuário é direcionado ao painel principal, onde visualiza:
   - Cards de Resumo (Total de Depósitos, Total de Gastos e Saldo em Conta).
   - Seção de Previsão Inteligente (30 dias).
   - Formulário rápido de **Nova Movimentação** (para inserção de receitas ou despesas).
   - Histórico Recente de transações ordenadas cronologicamente.
   - Gráfico de Despesas por Categoria.
3. **Encerramento de Sessão (Logout):** O usuário pode encerrar sua sessão a qualquer momento clicando no botão "Sair" localizado no canto superior direito.

## 2. Wireframes e Protótipo de Telas

O protótipo visual da aplicação foi concebido utilizando padrões modernos de design de interfaces web (estilo *glassmorphism* e paleta de cores escuras para redução de fadiga visual):

- **Tela Inicial / Dashboard:** Contém o cabeçalho com a logo e botão de saída, seguido pelos blocos de indicadores financeiros no topo, o formulário de cadastro de movimentações na lateral esquerda e o histórico/gráficos dispostos à direita.