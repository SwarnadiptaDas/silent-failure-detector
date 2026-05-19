# 🚨 AI Silent Failure Detector

An AI-powered system that predicts potential software project failures **before they happen** by analyzing GitHub activity, developer engagement, task delays, and communication patterns. The platform provides real-time risk scores, identifies hidden bottlenecks, and generates actionable AI-driven insights to help teams prevent project breakdowns early.

---

# 🌟 Features

* 📊 **Project Risk Analysis**

  * Calculates project failure probability based on activity patterns

* 🔗 **GitHub Repository Monitoring**

  * Tracks commits, contributor activity, and repository engagement

* 🧠 **AI-Generated Insights**

  * Uses Groq LLM to explain risks and suggest preventive actions

* 😊 **Sentiment Analysis**

  * Detects negative or disengaged communication patterns

* ⚠️ **Risk Alerts**

  * Highlights inactive contributors, overdue tasks, and declining productivity

* 📈 **Interactive Dashboard**

  * Streamlit-powered real-time visualization of project health

* 🛡️ **Fallback Demo Mode**

  * Uses sample data when APIs are unavailable

---

# 🏗️ Project Architecture

```text
User Input (GitHub Repo)
            ↓
GitHub API Integration
            ↓
Activity & Behavioral Analysis
            ↓
Risk Scoring Engine
            ↓
AI Insight Generation (Groq)
            ↓
Streamlit Dashboard
```

---

# 📁 Project Structure

```text
silent-failure-detector/
│
├── data/
│   └── sample_data.json
│
├── services/
│   ├── __init__.py
│   ├── github_api.py
│   ├── sentiment.py
│   ├── risk_model.py
│   └── ai_insights.py
│
├── utils/
│   ├── __init__.py
│   └── helpers.py
│
├── app.py
├── requirements.txt
└── README.md
```

---

# ⚙️ Tech Stack

## Frontend

* Streamlit

## Backend

* Python

## AI/ML

* Groq API (LLaMA Models)
* HuggingFace Transformers

## APIs

* GitHub REST API

## Data Processing

* Pandas

## Visualization

* Matplotlib

---

# 🚀 Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/SwarnadiptaDas/silent-failure-detector.git
cd silent-failure-detector
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

### Windows

```bash
venv\Scripts\activate
```

### Mac/Linux

```bash
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
GITHUB_TOKEN=your_github_token
GROQ_API_KEY=your_groq_api_key
```

---

# ▶️ Run the Application

```bash
streamlit run app.py
```

---

# 🧠 How It Works

The system collects repository activity data from GitHub and analyzes:

* commit frequency
* contributor engagement
* communication sentiment
* task delay patterns

Using these signals, the AI model generates:

* project risk scores
* hidden bottleneck detection
* actionable recommendations

---

# 🎯 Future Enhancements

* Slack/Discord integration
* Jira/Trello task monitoring
* Advanced ML-based prediction models
* Team burnout prediction
* Real-time notifications & alerts
* Historical trend forecasting

---

# 🏆 Use Cases

* Software development teams
* Startup engineering teams
* Agile project management
* Remote collaboration monitoring
* Engineering productivity analytics

---

# 🤝 Contributing

Contributions, issues, and feature requests are welcome!

---

# 📜 License

This project is licensed under the MIT License.

---

# 👩‍💻 Author

**Swarnadipta Das**
B.Tech CSE | AI & ML Enthusiast 
