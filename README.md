# AI-Powered Restaurant Helpdesk Agent

A local AI-powered restaurant customer-support demo built with Python,
Streamlit, PyPDF, LiteLLM, Ollama, Qwen3, and SQLite.

## Features

- Upload a restaurant PDF and extract text from all pages.
- Ask menu and restaurant questions through a Streamlit chatbot.
- Classify queries as general questions, complaints, or order support.
- Create support tickets and store them in SQLite.
- View tickets and update their status in the dashboard.
- Run the language model locally using Ollama.

## Project files

```text
Restaurant_Helpdesk_Agent/
├── app.py
├── requirements.txt
├── restaurant_menu.pdf   # Add your own restaurant PDF
├── helpdesk.db           # Created automatically
└── README.md
```

## Requirements

- Python 3.9 or later
- Ollama installed and running
- Qwen3 4B model downloaded

## Setup

1. Open a terminal in this project folder.
2. Create and activate a virtual environment (recommended):

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Download the Ollama model:

   ```bash
   ollama pull qwen3:4b
   ```

5. Start Ollama. If it is not already running, open another terminal and run:

   ```bash
   ollama serve
   ```

6. Add your restaurant PDF:
   - Rename your existing `8_restaurent.pdf` to `restaurant_menu.pdf`
     and place it beside `app.py`, OR
   - Start the app and upload the PDF using the sidebar.

7. Run the app:

   ```bash
   streamlit run app.py
   ```

8. Open the local URL shown in the terminal, usually:

   `http://localhost:8501`

## Notes

- The SQLite database `helpdesk.db` is created automatically when the app starts.
- This is a demonstration application. Order status is not connected to a
  real ordering system; order-related questions can be escalated as tickets.
- Ticket creation requires a customer name.
- The model must be available through Ollama at `http://localhost:11434`.
- The app sends the extracted PDF text to the local Ollama model through LiteLLM.
- Scanned/image-only PDFs may require OCR before their text can be extracted.

## Example demo queries

- What food items are available?
- What is the price of biryani?
- Do you have sushi?
- My order is delayed. I haven't received it.
- I received the wrong food. I want a refund.
- My order number is ORD123. Where is my order?
