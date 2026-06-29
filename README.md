# Clinic Manager

Sistema desktop profissional de gerenciamento de clínicas, desenvolvido
100% em Python, com arquitetura limpa, preparado para empacotamento
Windows (PyInstaller/Nuitka) e para futuras integrações com IA.

---

## Stack tecnológica e justificativa

| Camada | Tecnologia | Por quê |
|---|---|---|
| Interface | **PySide6 (Qt)** | Maior controle de estilização (QSS) para a estética Notion/Linear pedida, melhor desempenho em listas/tabelas densas, décadas de maturidade em software desktop comercial, empacotamento previsível via PyInstaller/Nuitka. |
| Banco de dados | **SQLite + SQLAlchemy** | Persistência local sem servidor, ORM maduro com suporte a migrations simples, type hints e Repository Pattern. |
| Validação | **Pydantic** | Validação declarativa de dados de entrada (DTOs), separada dos modelos de persistência. |
| Parsing | **pypdf + python-docx** | Bibliotecas padrão de mercado para extração de texto/tabelas de PDF e DOCX. |
| Padrão arquitetural | **MVVM** | Bindings via Signals/Slots do Qt se encaixam naturalmente no padrão; ViewModels testáveis sem dependência de widgets. |
| Estrutura de formulários dinâmicos | **JSON** (não EAV) | Performance superior para reconstrução de formulários complexos (sem N joins), flexibilidade total de estrutura por tipo de ficha, versionamento simples. Ver docstring completa em `database/models.py`. |

---

## Arquitetura

```
clinic_manager/
├── main.py                 # Ponto de entrada (mínimo, sem lógica de negócio)
├── app.py                  # MainWindow: navegação entre telas
├── config.py               # Configuração centralizada (caminhos, constantes)
│
├── database/
│   ├── database.py         # Engine SQLAlchemy, sessões
│   ├── models.py            # Modelos ORM (Paciente, Consulta, Pasta, Formulario, RespostaFormulario)
│   ├── migrations.py        # Sistema leve de migrations versionadas
│   └── repositories/         # Repository Pattern (uma classe por agregado)
│
├── services/                # Service Layer: TODA regra de negócio vive aqui
│   ├── patient_service.py
│   ├── appointment_service.py
│   ├── folder_service.py
│   └── dynamic_form_service.py
│
├── viewmodels/               # Camada MVVM: prepara dados para a UI, expõe Signals Qt
├── views/                    # Apresentação pura (Qt Widgets), sem lógica de negócio
│   ├── home/, calendar/, patients/, dynamic_forms/, settings/
│   └── components/            # Componentes reutilizáveis (Card, Sidebar, Modal, etc.)
│
├── forms/                    # Schemas Pydantic (validação) + contrato FieldDefinition
│
├── parsers/                  # Engine de parsing de documentos (Extração → Classificação)
│   ├── pdf_parser.py / docx_parser.py    # Fase 1: Extração
│   ├── field_detector.py                  # Fase 2a: Classificação de campos
│   ├── table_detector.py                  # Fase 2b: Classificação de tabelas
│   ├── score_detector.py                  # Fase 2c: Classificação de scores clínicos
│   └── parser_engine.py                   # Orquestrador do pipeline completo
│
├── ai/                       # Camada de IA — desacoplada, com Null Object Pattern por padrão
│   ├── llm_adapter.py         # Interface abstrata (Dependency Inversion)
│   ├── prompt_builder.py
│   └── extraction.py
│
├── styles/                   # Design tokens + builder do QSS global
├── tests/                     # Suíte pytest (45 testes cobrindo regras de negócio críticas)
└── scripts/                   # Scripts de build/setup para Windows
```

### Fluxo da engine de parsing (módulo de Fichas Dinâmicas)

```
PDF/DOCX
   │
   ▼
[Extração]   PDFParser / DOCXParser  →  RawDocument (texto + tabelas brutas)
   │
   ▼
[Classificação]  FieldDetector + TableDetector + ScoreDetector  →  list[FieldDefinition]
   │
   ▼
[Construção]   DynamicFormBuilder (Qt)  →  formulário renderizado e interativo
   │
   ▼
[Persistência]  Formulario.estrutura_json  /  RespostaFormulario.dados_json
```

A camada de **IA** (`ai/`) nunca importa Qt nem é importada pelas
`views/` — ela existe como um ponto de extensão futuro, totalmente
opcional e desligado por padrão (`NullLLMAdapter`).

---

## Regras de negócio críticas implementadas

- **Idade nunca é armazenada** — sempre calculada em tempo real a
  partir de `data_nascimento` (`utils/age_calculator.py`,
  `Paciente.idade` property).
- **Botão WhatsApp** ao lado do telefone, gerando
  `https://wa.me/55DDDNUMERO` (`utils/phone_utils.py`).
- **Scores clínicos** (CHA2DS2-VASc, Wells, etc.) reconhecidos
  automaticamente pelo nome ou por heurística genérica, com cálculo de
  pontuação e classificação de risco em tempo real.
- **Tabelas dinâmicas** (bioimpedância, evolução de peso/IMC) com
  histórico editável e suporte a comparação temporal.
- **Versionamento de formulários**: reimportar um formulário com o
  mesmo nome cria uma nova versão, preservando respostas antigas.

---

## Executando em desenvolvimento

```bash
python -m venv venv
venv\Scripts\activate.bat        # Windows
pip install -r requirements.txt
python main.py
```

## Rodando os testes

```bash
pip install pytest
pytest tests/ -v
```

## Gerando o executável Windows

Ver **`PACKAGING_GUIDE.md`** para o guia completo (PyInstaller e Nuitka).

Resumo rápido:

```bat
pip install pyinstaller
pyinstaller build_config.spec --clean --noconfirm
REM -> dist\ClinicManager.exe
```
