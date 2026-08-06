# 🏛️ Mini Civic Helpdesk Bot

An interactive web application built with Streamlit designed to streamline civic grievance reporting, ticket logging, and automated helpdesk responses.

---

## ✨ Features

* **Ticket Logging:** Allows citizens to submit civic complaints with automated ticket ID generation and category tagging.
* **Automated & Translated Replies:** Provides instant automated response handling with multi-language support, powered by the **Sarvam AI API** for highly accurate Indian language translations.
* **Interactive UI:** Built with a custom styled Streamlit interface (`config.toml` & background styling).
* **Database Tracking:** Logs complaints and statuses locally for administrative tracking.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **Frontend/UI:** [Streamlit](https://streamlit.io/)
* **AI Integration:** [Sarvam AI API](https://www.sarvam.ai/) (via the `sarvamai` package) for translation
* **Database:** SQLite (`complaints.db`)
* **Version Control & Hosting:** Git, GitHub, Streamlit Community Cloud

---

## 📁 Project Structure

```text
mini_civic_helpdesk_bot/
│
├── .streamlit/
│   └── config.toml        # Streamlit theme & UI configuration
├── bot.py                 # Main Streamlit application script
├── requirements.txt       # Python dependencies (including sarvamai)
├── background.png         # UI background asset
├── .gitignore             # Ignored files (secrets, virtual environments)
└── README.md              # Project documentation
