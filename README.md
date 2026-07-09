# 🧬 Prontu — Prontuário Médico Inteligente

O **Prontu** é um sistema desktop moderno e intuitivo para prontuário eletrónico e gestão de clínicas médicas. Desenvolvido em Python com a biblioteca profissional **PySide6 (Qt for Python)**, o software conta com uma interface limpa seguindo os padrões visuais modernos (estilo Tailwind/Slate), permitindo o controlo completo de pacientes, agendas, fichas clínicas e configurações personalizadas.

---

## 📁 Estrutura do Projeto

```text
Prontu/
├── database/
│   └── __init__.py         # Resolução de escopo e caminhos do banco de dados
├── ui/
│   ├── main_window.py      # Janela principal (Sidebar, navegação segura e caminhos SQLite)
│   └── screens/
│       ├── home.py         # Tela inicial / Dashboard
│       ├── pacientes.py    # Tela de listagem e cadastro de pacientes
│       ├── agenda.py       # Tela da agenda médica com timeline de horários
│       ├── fichas.py       # Tela de fichas clínicas e evolução
│       └── configuracoes.py# Tela de configurações de perfil do profissional
├── main.py                 # Arquivo limpo de inicialização do ecossistema Qt
├── consultorio.db          # Banco de dados SQLite (Gerado automaticamente)
└── README.md               # Documentação do projeto
