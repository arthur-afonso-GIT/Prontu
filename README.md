<img width="1913" height="1004" alt="63dfd3c3-2e2f-460c-9ac4-1d606d83b584" src="https://github.com/user-attachments/assets/872cbe7d-f266-4aec-ba91-9120a36ef21a" /><img width="1917" height="1005" alt="a87edb14-2a67-4360-b567-ee9d1549b76e" src="https://github.com/user-attachments/assets/ddad6e9a-6545-44b8-b7a3-c8a09559b6b2" /># Prontu

<p align="center">
  <img src="ui/assets/prontu_logo.png" alt="Prontu logo" width="120">
</p>

<p align="center">
  <strong>Intelligent clinic management for desktop.</strong><br>
  A focused workspace for patient care, appointments, clinical records, payments, and team collaboration.
</p>

---

## Overview

Prontu is a desktop-first clinic management application built for the daily routine of small healthcare practices. It brings patient information, clinical records, appointments, financial follow-up, document exports, encrypted backups, and shared team access into one clear workspace.

The product is designed to be delivered as a Windows application. End users should work with the installed product, not configure Python, databases, or cloud infrastructure.

## Core capabilities

- **Patient management** — searchable profiles, specialty folders, recent-patient shortcuts, clinical history, and follow-up scheduling.
- **Patient import** — preview and import CSV or Excel files, with options to ignore or update existing records and normalized CPF matching.
- **Clinical records** — create, fill, edit, review, archive, and export records linked to each patient.
- **Assisted record digitization** — read printed forms from photos or scanned PDFs locally, review the detected fields and answers, keep the original as an attachment, and export the revised record.
- **Template builder** — create custom record models with sections, text fields, dates, numbers, checkboxes, and multiple-choice inputs.
- **Smart agenda** — daily and weekly calendar views, conflict prevention, custom procedures, status tracking, rescheduling, and direct access to the patient record.
- **Financial follow-up** — appointments feed the payment panel automatically; received, pending, and overdue amounts are clearly identified.
- **Returns and follow-ups** — schedule expected patient returns and keep the next action visible in the patient workflow.
- **Professional exports** — generate Word and PDF documents from patient and clinical-record data.
- **WhatsApp-assisted communication** — open a patient conversation or appointment reminder with a clinic-configured message ready for review and manual sending.
- **Encrypted local backup** — configure a secure destination, retention policy, optional attachment metadata, and a recovery password.

## Team workspace

Prontu supports individual accounts for a shared clinic database. Each person signs in with their own email and password, while all approved members work within the same clinic scope.

| Role | Access |
| --- | --- |
| **Owner** | Full operational access, team invitations, access revocation, role changes, and audit history. |
| **Professional** | Full operational access to patients, clinical records, agenda, returns, finance, exports, and settings. |
| **Secretary** | Basic patient registration and appointment management, without access to clinical records, attachments, finance, settings, or team administration. |

Owners can create invitations, select the invited role, regenerate invitation codes, revoke access, and manage the number of active seats allowed by the clinic plan.

## User documentation

The product documentation is written in Brazilian Portuguese for clinic owners, professionals, and administrative staff:

- [Windows installation guide](output/pdf/Guia_de_Instalacao_Prontu.pdf) — installation, Windows SmartScreen guidance, updates, and first access.
- [User manual and feature guide](output/pdf/Manual_de_Uso_e_Funcionalidades_Prontu.pdf) — patients, folders, imports, appointments, clinical records, returns, finance, team access, settings, backups, and daily routines.

These guides are designed for end users and do not require knowledge of Python, Supabase, or database administration.

## Screenshots

### Dashboard

![Prontu dashboard]<img width="1424" height="752" alt="Gemini_Generated_Image_qyiuu6qyiuu6qyiu" src="https://github.com/user-attachments/assets/3cb600c5-d659-4c42-845e-6969b52e29b3" />


### Patient management

![Prontu patient management]<img width="768" height="403" alt="08acfbf8-0346-47e2-ad0d-60167af0631e" src="https://github.com/user-attachments/assets/2700d124-c202-453d-93b0-5ee1885bf021" />


### Appointment scheduling

![Prontu appointment scheduling]<img width="1917" height="1005" alt="a87edb14-2a67-4360-b567-ee9d1549b76e" src="https://github.com/user-attachments/assets/b5709149-28a2-4791-9944-bd90ad60c6f1" />


### Financial tracking

![Prontu financial tracking]<img width="1913" height="1004" alt="63dfd3c3-2e2f-460c-9ac4-1d606d83b584" src="https://github.com/user-attachments/assets/cbcf6d61-08b0-43b9-b9c9-ecb5a7a38d98" />

### Clinical Records

<img width="1913" height="1004" alt="935c2e81-df68-435b-b02d-10e726050d64" src="https://github.com/user-attachments/assets/132cb7e1-5900-4cfd-918d-e9d78e5c93a6" />


### Config

<img width="1424" height="747" alt="Gemini_Generated_Image_whh283whh283whh2" src="https://github.com/user-attachments/assets/4bf855ac-913d-4538-9aa9-10c6e5dc11d8" />


### Team management

<img width="1424" height="747" alt="Gemini_Generated_Image_whh283whh283whh2" src="https://github.com/user-attachments/assets/9616c76d-c98c-4b07-aee4-b9d7c4192b46" />




## Technology stack

| Area | Technologies |
| --- | --- |
| Desktop application | Python 3.11, PySide6 (Qt for Python) |
| Cloud data | Supabase, PostgreSQL, Row Level Security |
| Authentication and team operations | Supabase Auth, Supabase Edge Functions, TypeScript / Deno |
| Documents and local OCR | python-docx, reportlab, pypdf, PyMuPDF, RapidOCR, ONNX Runtime |
| Local security | cryptography, keyring |
| Connectivity and configuration | httpx, python-dotenv |
| Windows distribution | PyInstaller application bundle, Inno Setup installer, and optional Authenticode signing workflow |

## Architecture

```text
Prontu
├── main.py                  Single application entry point
├── database/                Supabase access, session management and secure local storage
├── ui/
│   ├── qml/                 Complete responsive user interface
│   ├── qml_*_controller.py  Python controllers exposed to QML
│   └── assets/              Product branding and visual assets
├── services/                Business rules, backup and background services
├── installer/               PyInstaller and Inno Setup distribution definitions
├── scripts/                 Build, packaging and release support scripts
├── output/pdf/              End-user product documentation
├── supabase/
│   ├── migrations/          PostgreSQL schema, Row Level Security policies and database evolution
│   └── functions/           Activation, login, password reset, team and messaging APIs
└── tests/                   Automated regression checks
```

The desktop interface communicates with Supabase through a small Python data layer. PostgreSQL migrations define data structure and policies; Edge Functions handle sensitive operations such as activation, account creation, invitations, role changes, and password recovery without exposing privileged credentials in the desktop application.

## Data and security

- Every clinic operates in its own data scope through `consultorio_id`.
- Supabase Row Level Security reinforces clinic and role boundaries at database level.
- Each team member has an individual account and can be revoked by the clinic owner.
- Audit history records operational events without exposing clinical content in the audit interface.
- Device activation and session handling keep privileged database credentials out of the desktop application.
- Local backup files are encrypted and can be protected with a recovery password.
- Production builds can require executable and installer signatures when a trusted code-signing certificate is available.

Prontu provides technical safeguards for a small-practice workflow. Legal compliance, privacy policies, retention rules, and operational procedures must be defined by each clinic before production use.

## Product direction

Prontu is evolving into a polished Windows product for small healthcare practices: simple enough for a local clinic, structured enough for a collaborative team, and ready to grow through plan-based features and installer-based distribution.

## Author

**Arthur Florencio Afonso**
[GitHub](https://github.com/arthurflorencio) · [LinkedIn](https://www.linkedin.com/in/arthur-florencio-afonso/)
