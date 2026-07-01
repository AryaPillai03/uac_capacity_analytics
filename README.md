# System Capacity & Care Load Analytics for Unaccompanied Children

An interactive data science pipeline and executive dashboard built to monitor and analyze the capacity strain, intake pressure, and operational bottlenecks within the Unaccompanied Alien Children (UAC) care framework (2023–2025).

## 🚀 Key Project Features
*   **Automated Data Cleaning Pipeline:** Handles type casting, sanitization of numeric string fields (e.g., handling embedded commas), and chronological alignment.
*   **Operational Anomaly Detection:** Programmatically identifies reporting lag anomalies across agency handoffs (e.g., identifying 86 distinct instances where CBP transfers exceeded stated active custody snapshots).
*   **Interactive Web Application:** Built via Streamlit implementing dual-axes trend analysis, dynamic rolling average toggles (Daily vs. Weekly), and high-level executive KPI metrics.
*   **Formal Research Paper:** Full analytical breakdown included directly inside the project documentation.

## 🛠️ Setup & Installation Instructions

To run this project locally on your machine, follow these steps:

1. **Clone or download this repository** to your local machine.
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   