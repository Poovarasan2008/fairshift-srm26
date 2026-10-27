# 🛡️ FairShift — Decent Work Platform
> **UN SDG 8: Decent Work & Economic Growth**  
> Built for Prompt Wars 2026 × ACM SRMIST

[![Tests](https://img.shields.io/badge/pytest-11%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Platform](https://img.shields.io/badge/deployed%20on-Google%20Cloud%20Run-4285F4.svg)]()

---

## 1. Problem Statement & Motivation
Across critical labor-intensive sectors—such as **Construction Sites**, **Colleges/Schools**, **Hospitals**, and **Factories**—millions of shift workers are managed through informal paper registers, spreadsheets, and WhatsApp groups.

This causes critical problems:
* **Opaque Pay & Stolen Overtime**: Workers are unsure how their pay is calculated and whether overtime is recorded accurately.
* **Fear of Retaliation**: Hesitation to raise safety complaints or speak up about poor working conditions.
* **Ignored Workplace Hazards**: Safety issues (e.g., loose scaffolding, wet slippery corridors, exposed wiring) remain unaddressed until severe accidents occur.
* **Employer Blind Spots**: Supervisors have zero visibility into chronic worker fatigue, excessive back-to-back shifts, or rising attrition risks.
* **Accessibility Gaps**: Frontline workers speak regional languages (such as Tamil), may have limited literacy, and use low-end smartphones.

---

## 2. Solution: FairShift
**FairShift** bridges this gap with a dual-interface web platform designed to make work **fairer, safer, and more transparent**:
* **Mobile-First Worker UI**: High-contrast, touch-friendly buttons, regional language support (English + Tamil), and voice-to-text safety reporting.
* **Employer / Admin Oversight Dashboard**: Real-time cross-sector visibility, overtime verification, safety hazard lifecycle tracking, and automated fatigue risk detection.

---

## 3. Core Working Features

### 1. Shift Check-in / Check-out with Automatic Overtime
* Single-tap clock in and clock out with live shift timer.
* **Overtime Rule**: Any shift duration exceeding **8.0 hours** is automatically split into standard hours and overtime hours, earning **1.5× regular pay**.

### 2. Transparent Payslip Breakdown
* Big numbers and visual breakdown showing:
  $$\text{Total Pay} = (\text{Regular Hours} \times \text{Base Rate}) + (\text{Overtime Hours} \times 1.5 \times \text{Base Rate})$$
* **Zero mystery deductions**: Workers see exactly what they earned with zero hidden cuts.

### 3. Voice & Text Safety Hazard Reporting (With Lifecycle Tracking)
* Workers report workplace hazards using text or **browser voice recognition (Web Speech API)** in English or Tamil.
* Each report receives a unique tracking ticket (e.g., `FS-HAZ-101`).
* **Strict Lifecycle**: `Reported` ➔ `In Review` ➔ `Fixed`. Workers can track progress and read supervisor action notes in real time.

### 4. Worker Fatigue & Burnout Alert Center (Employer UI)
* Proactive risk engine that flags workers who:
  - Work an excessive single shift (>10 hours).
  - Work excessive weekly hours (>48 hours).
  - Work back-to-back shifts with insufficient rest (<10 hours between shifts).

### 5. 100% Anonymous Workforce Feedback Box
* Workers submit feedback on safety gear, facilities, or supervisors with satisfaction ratings (1–5 stars).
* **Guaranteed Anonymity**: No worker identity or ID is linked or saved in the feedback schema.

---

## 4. Cross-Industry Use Cases

FairShift comes pre-configured with two distinct sectors:

| Sector | Worker Persona | Common Hazards & Real-World Use Case |
| :--- | :--- | :--- |
| **🏗️ Construction Site** | Ramu Kumar / Murugan Velu | Tracks physical shift hours on active building sites, flags loose scaffolding planks, damaged winches, and monitors heavy labor fatigue. |
| **🎓 College Campus** | Priya Selvam | Tracks facilities and campus sanitation staff, manages slip hazards in corridors/libraries, broken fire exit glass, and ventilation in labs. |

*The Employer Dashboard features an instant sector filter (`All Sectors`, `Construction Site`, `College`) to isolate metrics and reports by industry.*

---

## 5. Inclusivity & Accessibility
* **Bilingual Language Toggle**: One-click switch between **English** and **தமிழ் (Tamil)** with dictionary architecture for easy expansion to Hindi or Telugu.
* **Voice-to-Text**: Built with native browser Speech Recognition (`webkitSpeechRecognition`) requiring zero external API keys or heavy dependencies.
* **High Contrast & Touch Targets**: WCAG AA compliant contrast ratios, 48px+ touch targets for one-thumb mobile usage on low-end smartphones.
* **Ultra-Lightweight (<200 KB total)**: Pure HTML/CSS/JS with zero heavy frameworks, ensuring instant loading on 2G/3G connections.

---

## 6. Demo Accounts

| Role | Username | Password | Sector / Scope | Focus Scenario |
| :--- | :--- | :--- | :--- | :--- |
| **Supervisor / Admin** | `admin` | `admin123` | All Sectors | Full dashboard, fatigue alerts, hazard triage |
| **Construction Worker** | `ramu` | `worker123` | Construction Site | Active shift, overtime payslip, hazard tracking |
| **College Staff** | `priya` | `worker123` | College | Campus sanitation, safety reports, feedback |
| **Fatigued Worker** | `murugan` | `worker123` | Construction Site | Demonstrates >10h shift & back-to-back fatigue |

---

## 7. How to Run Locally

### Prerequisites
* Python 3.9+ installed
* pip package manager

### Steps
```bash
# 1. Clone repository
git clone https://github.com/your-username/fairshift.git
cd fairshift

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables (optional for local dev)
cp .env.example .env

# 4. Start the application
python app.py
```
Open your browser and navigate to: **`http://localhost:8080`** (or `http://localhost:5000`).

---

## 8. How to Run Unit Tests

FairShift includes 11 automated unit tests verifying overtime formulas, payslip math, hazard lifecycles, fatigue rules, and database seeding:

```bash
pytest
```
*Expected Output:*
```text
tests/test_fairshift.py ...........                                      [100%]
============================= 11 passed in 0.28s ==============================
```

---

## 9. Deployment to Google Cloud Run

FairShift is packaged with a production-ready `Dockerfile` and configured to run on Google Cloud Run using `gunicorn`:

```bash
# 1. Authenticate with Google Cloud
gcloud auth login

# 2. Set your Google Cloud Project ID
gcloud config set project YOUR_PROJECT_ID

# 3. Deploy directly to Cloud Run from source
gcloud run deploy fairshift \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars SECRET_KEY="your-production-secret-key"
```

Once the command completes, Cloud Run will print your **Live Service URL**:
`https://fairshift-xxxxxx-uc.a.run.app`

---

## 10. Repository Size & Submission Check
* Total repository size: **< 1 MB** (Well below the strict 10 MB hackathon ceiling).
* Single branch only (`main`).
* Zero hardcoded credentials; all secrets loaded from environment variables.
* Fully tested with pytest.

