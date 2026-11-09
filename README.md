# Accounts Payable Automation System

A full-stack Accounts Payable automation tool with OCR data extraction, built with **ReactJS**, **Django**, and **PostgreSQL**.

## Features
- **Invoice Capture**: Upload PDF/Images via React UI.
- **OCR Extraction**: Uses local Tesseract OCR and rule-based parsing to extract invoice numbers, dates, totals, tax, and GSTIN.
- **Validation Engine**: Checks required invoice fields, duplicate invoices, amounts, GSTIN format, and vendor status.
- **Dashboard**: Real-time stats on processed invoices.
- **Vendor & PO Management**: Complete database models for 2-way/3-way matching.
- **Approval Workflow**: Role-checked sequential approvals and unanimous parallel approvals for active users in the configured role.
- **Reports & Audit**: Live AP aging, invoice status, exception, GST, and audit-log reports with CSV export.
- **Outlook Ingestion**: Optional Microsoft Graph polling for supported invoice attachments.

## Tech Stack
- Frontend: React (Vite), Axios, React Router
- Backend: Django, Django REST Framework
- Database: PostgreSQL
- OCR: Tesseract OCR

## Invoice OCR and Validation

When an invoice is uploaded, the backend attempts OCR automatically. On the invoice detail page, **Run OCR** can be used to retry extraction for invoices in the uploaded or extracted state. OCR saves the raw text and any fields it recognizes, including the invoice number, invoice date, total, tax, and GSTIN.

If the OCR result does not include required information, open **Edit Fields** to correct the invoice number, date, total, and vendor selection, then save and run validation again. The required validation fields are invoice number, vendor record, invoice date, and total amount. A vendor is linked automatically only when the extracted GSTIN matches exactly one vendor record; otherwise, select the correct vendor manually. OCR is heuristic and may need review, especially for low-quality scans or unfamiliar invoice layouts.

## Setup Instructions
1. **Database**: Create a PostgreSQL DB named `ap_automation`. Run `psql -U <user> -d ap_automation -f database/schema.sql`.
2. **Backend**: 
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver

3. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Outlook Graph Invoice Ingestion

The importer reads unread messages with attachments from the configured mailbox, imports PDF/JPG/PNG/TIFF attachments, records each message for idempotency, and marks handled messages as read. Configure an Entra ID application with Microsoft Graph **Mail.ReadWrite application permission** and admin consent, then provide the settings as environment variables (do not put credentials in source control):

```powershell
Set-Location .\backend
$env:OUTLOOK_GRAPH_TENANT_ID = "<tenant-id>"
$env:OUTLOOK_GRAPH_CLIENT_ID = "<application-client-id>"
$env:OUTLOOK_GRAPH_CLIENT_SECRET = "<secret-from-your-secret-store>"
$env:OUTLOOK_GRAPH_MAILBOX = "ap@example.com"
$env:OUTLOOK_GRAPH_FOLDER = "inbox" # optional
python manage.py migrate
python manage.py ingest_outlook_invoices --max-messages 25
```

Run the command periodically with your deployment scheduler. The importer requires network access to Microsoft identity and Graph endpoints. It does not configure or store credentials itself.

## Current Integration Boundaries

- OCR uses local Tesseract and rule-based extraction; no cloud AI service is configured.
- GSTIN validation checks format/state-code rules only; it does not query a government registry.
- Payment status can be recorded with a real transaction reference, but no bank connection or automatic transfer is configured.
- ERP/accounting connectors, reminder notifications, and automatic approval escalation still require provider and deployment configuration. `escalate_after_days` is currently displayed as an attention threshold, not an outbound notification.
- Parallel approval requires every active account with the step's configured role to approve. Approval-matrix editing is restricted to administrators through the backend/API.

# Challenges and Solutions

### 1. Handling OCR File Paths in Windows
**Challenge:** Tesseract and Poppler were installed on the D: drive (`D:\Program Files\Tesseract-OCR`), but Python's `pytesseract` library defaults to looking in the system PATH, causing `FileNotFoundError`.
**Solution:** I explicitly configured the engine path within `invoices/ocr_service.py` using `pytesseract.pytesseract.tesseract_cmd` and set the `TESSDATA_PREFIX` environment variable. For PDF handling, I configured `pdf2image` to explicitly use the Poppler binary path on the D drive.

### 2. Abstracting OCR Logic between Admin and API
**Challenge:** Initially, the OCR logic was placed in the `InvoiceViewSet` (React API). This meant that if an invoice was uploaded via the Django Admin panel, OCR wouldn't run. 
**Solution:** I moved the OCR trigger into a `post_save` signal inside `models.py`. This ensures that regardless of where the invoice is created (React UI, Django Admin, or a shell script), the OCR extraction automatically fires and updates the database.

### 3. CORS and Authentication Errors
**Challenge:** When connecting the React frontend (port 5173) to Django (port 8000), file uploads were failing with `403 Forbidden` and `ValueError: Cannot assign AnonymousUser`.
**Solution:** The API uses session authentication and authenticated-by-default permissions. Login/logout remain public; invoice, vendor, payment, approval, dashboard, and report data require an authenticated user, with additional role checks for workflow actions.
