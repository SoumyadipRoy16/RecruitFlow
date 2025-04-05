# RecruitFlow

![Project Banner](https://th.bing.com/th/id/OIP.wuRo9CXpFJpDDh3KJ4Gb-AHaHa?rs=1&pid=ImgDetMain)

## 🔍 Overview
**RecruitFlow** is an automated job screening system that uses multi-agent AI to:
- Parse job descriptions
- Analyze candidate CVs
- Match applicants to roles
- Schedule interviews

## ✨ Features
- **JD Analysis** - Extract skills/requirements from job postings
- **CV Processing** - Convert resumes to structured data
- **AI Matching** - Score candidates (skills 50%, exp 30%, quals 20%)
- **Bias Reduction** - Demographic-blind evaluation
- **Auto-Scheduling** - Calendar invites + email automation

## 🛠️ Tech Stack
```plaintext
Frontend: Streamlit
AI Engine: Groq LLM (llama3-70b-8192)
Database: SQLite
Email: SMTP + icalendar
```

## 🚀 Quick Start

### Prerequisites
* Python 3.10+
* Groq API Key
* SMTP credentials

### Installation
```bash
git clone https://github.com/SoumyadipRoy16/RecruitFlow.git
cd RecruitFlow
pip install -r requirements.txt
```

### Configuration
Create `.env` file:
```ini
GROQ_API_KEY=your_key
SMTP_SERVER=smtp.gmail.com
EMAIL_ADDRESS=your@email.com
```

### Launch
```bash
streamlit run app.py
```

## 📂 Project Structure
```
.
├── app.py                # Main application
├── utils/
│   ├── agents.py         # AI agents
│   ├── database.py       # DB operations
│   └── email_sender.py   # Email handler
├── data/                 # Sample JDs/CVs
└── database/             # SQLite storage
```

## 🤖 System Workflow
1. Upload job descriptions
2. Add candidate CVs
3. AI generates match scores
4. Schedule interviews
5. Send automated invites

## 📜 License
MIT © 2024 [Soumyadip Roy]

## 📧 Contact
**Email**: soumyadiproy894@gmail.com  
**GitHub**: github.com/SoumyadipRoy16
