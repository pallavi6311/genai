"""Custom Streamlit styling for the Image-to-Speech GenAI app."""

css_code = """
<style>
.stApp {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    color: #f1f5f9;
}

h1, h2, h3 {
    font-family: 'Trebuchet MS', sans-serif;
}

.stButton>button {
    background-color: #6366f1;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 0.5rem 1.2rem;
    font-weight: 600;
}

.stButton>button:hover {
    background-color: #4f46e5;
    color: white;
}

section[data-testid="stSidebar"] {
    background-color: #111827;
}

.stAlert {
    border-radius: 10px;
}
</style>
"""
