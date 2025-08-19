```markdown
# ICD Chatbot (Streamlit + Flask)

This project is an ICD (International Classification of Diseases) related chatbot built with Streamlit (frontend) and Flask (backend).  
The chatbot helps users query information from ICD documents interactively.

```
## 📂 Project Structure

.
├── backend.py        # Flask backend server
├── frontend.py       # Streamlit chatbot UI
├── context.py        # Context/session management
├── requirements.txt  # Python dependencies
├── .env              # Environment variables
├── .gitignore
└── venv/             # Virtual environment

## ⚙️ Installation & Setup
### 1️⃣ Clone the repository
````

```bash
git clone https://github.com/your-username/icd-chatbot.git
cd icd-chatbot
````

### 2️⃣ Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate    # For Linux/Mac
venv\Scripts\activate       # For Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure environment variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_openai_api_key
```

---

## ▶️ Running the Project

### Run Flask backend

```bash
python backend.py
```

By default, backend runs on `http://127.0.0.1:5000`.

### Run Streamlit frontend

```bash
streamlit run frontend.py
```

By default, frontend runs on `http://localhost:8501`.

---

## 🖥️ Usage

* Open `http://localhost:8501` in your browser.
* Ask ICD-related queries in the chat.
* The Flask backend handles responses and returns AI answers to the Streamlit frontend.

---

