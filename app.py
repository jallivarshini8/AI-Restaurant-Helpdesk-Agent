import streamlit as st
import sqlite3
import os
from io import BytesIO
from datetime import datetime
from pypdf import PdfReader
from litellm import completion

# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Restaurant AI Helpdesk",
    page_icon="🍽️",
    layout="wide"
)

DB_NAME = "helpdesk.db"
MODEL_NAME = "ollama/qwen3:4b"
DEFAULT_PDF_PATH = "restaurant_menu.pdf"


# ==========================================
# 2. DATABASE INITIALIZATION
# ==========================================

def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            order_id TEXT,
            category TEXT,
            issue TEXT,
            priority TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


initialize_database()


# ==========================================
# 3. PDF TEXT EXTRACTION
# ==========================================

def extract_pdf_text(pdf_bytes):
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        extracted_text = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text.append(page_text)

        return "\n".join(extracted_text)

    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""


def load_default_pdf():
    if os.path.exists(DEFAULT_PDF_PATH):
        with open(DEFAULT_PDF_PATH, "rb") as file:
            return extract_pdf_text(file.read())

    return ""


# ==========================================
# 4. COMPLAINT CLASSIFICATION
# ==========================================

def classify_query(query):
    query_lower = query.lower()

    complaint_keywords = [
        "complaint", "bad service", "wrong order", "damaged",
        "cold food", "refund", "not received", "missing item",
        "poor service", "unhappy", "problem", "issue",
        "delayed", "late delivery", "cancel my order",
        "incorrect order", "food poisoning", "allergy"
    ]

    order_keywords = [
        "order status", "track my order", "where is my order",
        "delivery status", "order delayed", "order number"
    ]

    if any(word in query_lower for word in complaint_keywords):
        return "Complaint"

    if any(word in query_lower for word in order_keywords):
        return "Order Support"

    return "General Query"


# ==========================================
# 5. AI RESPONSE GENERATION
# ==========================================

def generate_response(user_query, restaurant_context):
    system_prompt = f"""
You are an intelligent Restaurant AI Helpdesk Assistant.

Your responsibilities:
1. Answer customer questions about restaurant menu items.
2. Provide food details and prices only when available
   in the supplied restaurant document.
3. Help customers with general restaurant FAQs.
4. Understand complaints and respond politely.
5. Help customers with order-related issues.
6. Never invent order status, prices, menu items,
   restaurant policies or refund approvals.
7. If information is missing, explain that you cannot verify it
   and suggest contacting human support.
8. Never claim a support ticket has been created unless
   the application confirms its creation.

RESTAURANT KNOWLEDGE BASE:
{restaurant_context}

Use the restaurant document as the source of truth.
If an item is unavailable, say:
"Sorry, this item is not available in our menu."

Be polite, clear and professional.
"""

    try:
        response = completion(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.3,
            api_base="http://localhost:11434"
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI service error: {str(e)}"


# ==========================================
# 6. ESCALATION DETECTION
# ==========================================

def requires_escalation(query, ai_response):
    query_lower = query.lower()
    response_lower = ai_response.lower()

    escalation_keywords = [
        "human support", "contact support", "cannot verify",
        "cannot access", "unable to check", "don't have access",
        "do not have access", "not able to verify", "please contact"
    ]

    serious_issue_keywords = [
        "refund", "wrong order", "missing item", "damaged",
        "food poisoning", "allergy", "safety issue"
    ]

    if any(word in query_lower for word in serious_issue_keywords):
        return True

    if any(word in response_lower for word in escalation_keywords):
        return True

    return False


# ==========================================
# 7. CREATE SUPPORT TICKET
# ==========================================

def create_ticket(customer_name, order_id, category, issue, priority):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO tickets (
            customer_name, order_id, category, issue,
            priority, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_name,
        order_id,
        category,
        issue,
        priority,
        "Open",
        created_at
    ))

    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return ticket_id


# ==========================================
# 8. FETCH ALL SUPPORT TICKETS
# ==========================================

def fetch_tickets():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM tickets
        ORDER BY ticket_id DESC
    """)

    tickets = cursor.fetchall()
    conn.close()

    return tickets


# ==========================================
# 9. UPDATE TICKET STATUS
# ==========================================

def update_ticket_status(ticket_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET status = ?
        WHERE ticket_id = ?
    """, (status, ticket_id))

    conn.commit()
    conn.close()


# ==========================================
# 10. SESSION STATE
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_ticket" not in st.session_state:
    st.session_state.pending_ticket = None

if "restaurant_context" not in st.session_state:
    st.session_state.restaurant_context = load_default_pdf()


# ==========================================
# 11. SIDEBAR
# ==========================================

st.sidebar.title("🍽️ Restaurant Helpdesk")
st.sidebar.write("AI-powered customer support system")

uploaded_file = st.sidebar.file_uploader(
    "Upload Restaurant Knowledge PDF",
    type=["pdf"]
)

if uploaded_file is not None:
    if st.sidebar.button("Load Knowledge Base"):
        pdf_text = extract_pdf_text(uploaded_file.getvalue())

        if len(pdf_text.strip()) > 0:
            st.session_state.restaurant_context = pdf_text
            st.sidebar.success("Knowledge base loaded successfully!")
        else:
            st.sidebar.error("No readable text found in PDF.")

if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.pending_ticket = None
    st.rerun()


# ==========================================
# 12. MAIN DASHBOARD
# ==========================================

st.title("🍽️ AI-Powered Restaurant Helpdesk")
st.caption(
    "Intelligent customer support using PDF knowledge "
    "and local Large Language Models"
)

tab1, tab2 = st.tabs([
    "💬 Customer Chat",
    "🎫 Support Ticket Dashboard"
])


# ==========================================
# 13. CUSTOMER CHAT INTERFACE
# ==========================================

with tab1:
    st.subheader("Chat with Restaurant Assistant")

    if not st.session_state.restaurant_context.strip():
        st.warning(
            "Upload a restaurant PDF or place "
            "restaurant_menu.pdf in the project folder."
        )
    else:
        st.success("Restaurant knowledge base is ready.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input(
        "Ask about menu, orders or complaints..."
    )

    if user_query:
        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })

        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("AI is analyzing your query..."):
                category = classify_query(user_query)

                if not st.session_state.restaurant_context.strip():
                    ai_response = (
                        "Please upload the restaurant PDF knowledge base "
                        "using the sidebar before asking menu questions."
                    )
                else:
                    ai_response = generate_response(
                        user_query,
                        st.session_state.restaurant_context
                    )

                st.markdown(ai_response)

                escalation = requires_escalation(
                    user_query,
                    ai_response
                )

                if escalation:
                    st.warning(
                        "This issue may require human support. "
                        "You can create a support ticket below."
                    )
                elif category == "Complaint":
                    st.info(
                        "Your complaint can be registered "
                        "with our support team."
                    )

        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_response
        })

        if escalation or category in ["Complaint", "Order Support"]:
            st.session_state.pending_ticket = {
                "issue": user_query,
                "category": category
            }
        else:
            st.session_state.pending_ticket = None

        st.rerun()

    # ======================================
    # 14. TICKET CREATION FORM
    # ======================================

    if st.session_state.pending_ticket is not None:
        st.divider()
        st.subheader("🎫 Create Support Ticket")

        pending = st.session_state.pending_ticket

        st.write(f"Detected issue: **{pending['category']}**")

        with st.form("ticket_form"):
            customer_name = st.text_input("Customer Name")
            order_id = st.text_input("Order ID (if applicable)")
            priority = st.selectbox(
                "Priority",
                ["Low", "Medium", "High", "Urgent"]
            )

            submitted = st.form_submit_button("Create Support Ticket")

            if submitted:
                if not customer_name.strip():
                    st.error("Please enter your name.")
                else:
                    ticket_id = create_ticket(
                        customer_name,
                        order_id,
                        pending["category"],
                        pending["issue"],
                        priority
                    )

                    st.success(
                        f"Support ticket created successfully! "
                        f"Ticket ID: #{ticket_id}"
                    )

                    st.session_state.pending_ticket = None


# ==========================================
# 15. SUPPORT TICKET DASHBOARD
# ==========================================

with tab2:
    st.subheader("🎫 Customer Support Management")

    tickets = fetch_tickets()
    total_tickets = len(tickets)

    open_tickets = sum(
        1 for ticket in tickets if ticket[6] == "Open"
    )

    resolved_tickets = sum(
        1 for ticket in tickets if ticket[6] == "Resolved"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Tickets", total_tickets)
    col2.metric("Open Tickets", open_tickets)
    col3.metric("Resolved Tickets", resolved_tickets)

    st.divider()

    if tickets:
        for ticket in tickets:
            (
                ticket_id,
                customer_name,
                order_id,
                category,
                issue,
                priority,
                status,
                created_at
            ) = ticket

            with st.expander(
                f"Ticket #{ticket_id} - {category} - {status}"
            ):
                st.write(f"**Customer:** {customer_name}")
                st.write(f"**Order ID:** {order_id or 'Not provided'}")
                st.write(f"**Category:** {category}")
                st.write(f"**Issue:** {issue}")
                st.write(f"**Priority:** {priority}")
                st.write(f"**Created:** {created_at}")
                st.write(f"**Current Status:** {status}")

                statuses = [
                    "Open", "In Progress", "Resolved", "Closed"
                ]

                new_status = st.selectbox(
                    "Update Ticket Status",
                    statuses,
                    index=statuses.index(status),
                    key=f"status_{ticket_id}"
                )

                if st.button(
                    "Update Status",
                    key=f"update_{ticket_id}"
                ):
                    update_ticket_status(ticket_id, new_status)
                    st.success("Ticket status updated!")
                    st.rerun()
    else:
        st.info("No support tickets have been created yet.")


# ==========================================
# 16. FOOTER
# ==========================================

st.divider()

st.caption(
    "AI-Powered Restaurant Helpdesk | "
    "Python | Streamlit | LiteLLM | Ollama | SQLite"
)
