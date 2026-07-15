# Prontu

<p align="center">
  <img src="ui/assets/prontu_logo.png" alt="Prontu logo" width="120">
</p>

<p align="center">
  <strong>Intelligent clinic management for desktop.</strong><br>
  A focused workspace for patient care, appointments, clinical records, payments, and professional documents.
</p>

---

## Overview

Prontu is a desktop application designed to simplify the daily workflow of a healthcare practice. It keeps the most important information in one place: patients, clinical records, agenda, financial follow-up, documents, and encrypted backups.

The product is built as a desktop-first experience and is intended to be delivered through a Windows installer in production, without asking the end user to configure Python or a database.

## Highlights

- **Patient management** — organized profiles, specialty folders, clinical history, and quick search.
- **Clinical records** — fill, edit, save, review, and export patient records from reusable templates.
- **Template builder** — create custom record models with sections and input fields, with a live preview.
- **Smart agenda** — schedule appointments, avoid time conflicts, update appointment status, and open a record directly from an appointment.
- **Financial follow-up** — appointments appear automatically in the payment panel; track received, pending, and overdue payments with clear visual status.
- **Professional exports** — generate Word and PDF documents with patient and appointment information.
- **Encrypted local backup** — configure a destination folder, backup retention, metadata inclusion, and a recovery password.
- **Multi-clinic isolation** — clinic data is separated by `consultorio_id`, so each activated clinic works only with its own data.

## Screenshots

### Appointment scheduling

![Prontu appointment scheduling](docs/screenshots/appointment-scheduling.png)

### Financial tracking

![Prontu financial tracking](docs/screenshots/financial-tracking.png)

## Technology stack

| Area | Technologies |
| --- | --- |
| Desktop application | Python 3.11, PySide6 (Qt for Python) |
| Cloud data | Supabase, PostgreSQL, Row Level Security |
| Secure activation | Supabase Edge Functions, TypeScript / Deno |
| Documents | python-docx, PySide6 Qt Print Support, pypdf |
| Local security | cryptography, keyring |
| Connectivity and configuration | httpx, python-dotenv |
| Windows distribution | PyInstaller-ready desktop application, designed for installer delivery |

## Architecture

```text
Prontu
├── main.py                 Application entry point
├── database/               Supabase access, session and secure local storage
├── ui/
│   ├── main_window.py      Navigation shell and shared application behavior
│   ├── screens/            Dashboard, patients, agenda, records, finance and settings
│   └── assets/             Product branding and visual assets
├── supabase/
│   ├── migrations/         PostgreSQL schema, policies and database evolution
│   └── functions/          Secure device-activation API
└── tests/                  Automated regression checks
```

The desktop interface communicates with Supabase through a small Python data layer. Database migrations define the PostgreSQL structure and data policies, while the Edge Function handles sensitive device activation without exposing privileged database credentials in the app.

## Data and security

- Every clinic operates within its own data scope.
- Supabase policies reinforce clinic-level access control.
- Device activation validates the application key before opening the workspace.
- Session data and local secrets are stored securely on the device.
- Local backups are encrypted and can be protected with a recovery password.

## Product direction

Prontu is evolving toward a polished Windows product for small healthcare practices, with installer-based delivery, richer clinical workflows, reliable cloud synchronization, and clear financial visibility.

## Author

**Arthur Florencio Afonso**
[GitHub](https://github.com/arthurflorencio) · [LinkedIn](https://www.linkedin.com/in/arthur-florencio-afonso/)
