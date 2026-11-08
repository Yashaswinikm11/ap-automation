# Accounts Payable Automation System

A full-stack Accounts Payable automation tool with OCR data extraction, built with **ReactJS**, **Django**, and **PostgreSQL**.

## Features
- **Invoice Capture**: Upload PDF/Images via React UI.
- **OCR Extraction**: Uses Tesseract to automatically extract Invoice Numbers, Amounts, and GSTIN.
- **Validation Engine**: Duplicate checks and mandatory field validation.
- **Dashboard**: Real-time stats on processed invoices.
- **Vendor & PO Management**: Complete database models for 2-way/3-way matching.

## Tech Stack
- Frontend: React (Vite), Axios, React Router
- Backend: Django, Django REST Framework
- Database: PostgreSQL
- OCR: Tesseract OCR

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

# Challenges and Solutions

### 1. Handling OCR File Paths in Windows
**Challenge:** Tesseract and Poppler were installed on the D: drive (`D:\Program Files\Tesseract-OCR`), but Python's `pytesseract` library defaults to looking in the system PATH, causing `FileNotFoundError`.
**Solution:** I explicitly configured the engine path within `invoices/ocr_service.py` using `pytesseract.pytesseract.tesseract_cmd` and set the `TESSDATA_PREFIX` environment variable. For PDF handling, I configured `pdf2image` to explicitly use the Poppler binary path on the D drive.

### 2. Abstracting OCR Logic between Admin and API
**Challenge:** Initially, the OCR logic was placed in the `InvoiceViewSet` (React API). This meant that if an invoice was uploaded via the Django Admin panel, OCR wouldn't run. 
**Solution:** I moved the OCR trigger into a `post_save` signal inside `models.py`. This ensures that regardless of where the invoice is created (React UI, Django Admin, or a shell script), the OCR extraction automatically fires and updates the database.

### 3. CORS and Authentication Errors
**Challenge:** When connecting the React frontend (port 5173) to Django (port 8000), file uploads were failing with `403 Forbidden` and `ValueError: Cannot assign AnonymousUser`.
**Solution:** I configured `django-cors-headers` to allow the React origin and adjusted the DRF `DEFAULT_PERMISSION_CLASSES` to `AllowAny` for the demo. I also updated the `perform_create` method in the viewset to safely check `if self.request.user.is_authenticated` before assigning the `uploaded_by` field.

