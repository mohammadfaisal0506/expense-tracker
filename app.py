import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta, datetime
import plotly.express as px
from typing import Optional, Dict, Any

# API Base URL
API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Expense Tracker ", page_icon="📈", layout="wide")


st.markdown(
    """
    <style>
    .stApp {
        background-color: #121212; /* Dark, charcoal background */
        color: #e0e0e0; /* Light gray text for contrast */
    }
    .main-header {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
        color: #ffffff; /* White header text */
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px #000000;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: 2px solid #4CAF50;
    }
    .stButton>button:hover {
        background-color: #45a049;
        border: 2px solid #45a049;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background-color: #2e2e2e; /* Darker input background */
        color: #f0f0f0; /* Light text in inputs */
        border-radius: 8px;
        border: 1px solid #444444;
    }
    .stAlert {
        border-radius: 8px;
        background-color: #333333;
        color: #ffffff;
    }
    .css-1d37e6v { /* Sidebar */
        background-color: #1e1e1e; /* Slightly lighter dark for sidebar */
        padding: 20px;
        border-right: 1px solid #333333;
    }
    .metric-container {
        padding: 20px;
        border-radius: 12px;
        background-color: #1e1e1e;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4CAF50; /* Green for key metrics */
    }
    .metric-label {
        font-size: 1rem;
        color: #a0a0a0; /* Gray for labels */
    }
    /* Expander styling for a cleaner look */
    .st-expander {
        border: 1px solid #444444;
        border-radius: 8px;
    }
    .st-expander-header {
        background-color: #2e2e2e;
        color: #ffffff;
    }
    /* Dataframe styling for better dark mode visibility */
    .stDataFrame {
        color: #e0e0e0;
    }
    .st-dg {
        background-color: #1e1e1e !important;
    }
    .st-dg-table-row {
        background-color: #1e1e1e !important;
    }
    .st-dg-table-row:hover {
        background-color: #2e2e2e !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Helpers
# -----------------------------
def get_auth_headers():
    """Returns the authorization headers for API requests."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def call_api(method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None):
    """A generic function to handle all API calls with centralized error handling."""
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}/{endpoint}",
            json=json_data,
            data=data,
            headers=get_auth_headers()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Session expired or unauthorized. Please log in again. 🔄")
            st.session_state.clear()
            st.rerun()
        st.error(f"API Error: {e.response.json().get('detail', 'An unknown error occurred')} 🚫")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Please ensure the backend server is running. ⚠️")
        return None


# Login / Register

def login(role_check=None):
    """Handles user login and role-based access control."""
    st.markdown("<h1 class='main-header'> Welcome to Expense Tracker App </h1>", unsafe_allow_html=True)
    st.subheader("Please Login")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login")

        if submitted:
            response = call_api("post", "login", data={"username": username, "password": password})
            if response:
                st.session_state.token = response["access_token"]
                
                user_data = call_api("get", "users/me")
                if user_data:
                    if role_check and user_data["role"] != role_check:
                        st.error(f"This account is not a {role_check} account. Please use the correct login. ❌")
                        st.session_state.clear()
                        st.rerun()
                    else:
                        st.session_state.user = user_data
                        st.success("Login successful! ")
                        st.balloons()
                        st.rerun()

def register():
    """Handles new user registration."""
    st.markdown("<h1 class='main-header'> Join Expence Tracker</h1>", unsafe_allow_html=True)
    st.subheader("Create a New Account")
    with st.form("register_form", clear_on_submit=True):
        full_name = st.text_input("Full Name", placeholder="Your full name")
        email = st.text_input("Email", placeholder="Your email address")
        username = st.text_input("New Username", placeholder="Choose a username")
        password = st.text_input("New Password", type="password", placeholder="Create a strong password")
        submitted = st.form_submit_button("Register")
        
        if submitted:
            response = call_api(
                "post", 
                "register", 
                json_data={
                    "full_name": full_name,
                    "email": email,
                    "username": username,
                    "password": password
                }
            )
            if response:
                st.success("Registration successful! You can now log in. ")


# Budget Management (User only)

def manage_budget_page():
    """Page for users to add funds and manage their budget."""
    if st.session_state["user"]["role"] != "user":
        st.error("This feature is for users only. ")
        return

    st.header("My Budget")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Current Balance")
        balance = st.session_state["user"].get("balance", 0.0)
        st.markdown(
            f"<div class='metric-container'>"
            f"<div class='metric-label'>Available Funds</div>"
            f"<div class='metric-value'>{balance:,.2f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    with col2:
        st.subheader(" Add Funds")
        with st.form("add_funds_form"):
            amount_to_add = st.number_input("Amount to add", min_value=0.01, format="%.2f")
            submitted = st.form_submit_button("Add Funds")
            
            if submitted:
                response = call_api("post", "funds", json_data={"amount": amount_to_add})
                if response:
                    st.success(f"Successfully added {amount_to_add:,.2f} to your account!")
                    st.session_state["user"]["balance"] = response["new_balance"]
                    st.rerun()

# -----------------------------
# Add Expense (User only)
# -----------------------------
def add_expense_page():
    """Page for users to add new expenses."""
    if st.session_state["user"]["role"] != "user":
        st.error("This feature is for users only. ")
        return

    st.header(" Add a New Expense")
    
    balance = st.session_state['user'].get('balance', 0.0)
    st.info(f"Your current balance is: {balance:,.2f}")

    categories_data = call_api("get", "categories")
    categories = [c["name"] for c in categories_data] if categories_data else []

    with st.form("add_expense"):
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        category = st.selectbox("Category", categories) if categories else st.text_input("Category (No categories available)")
        exp_date = st.date_input("Date", value=date.today())
        description = st.text_area("Description", placeholder="e.g., Coffee with friends, grocery shopping")
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            if amount > balance:
                st.error("Insufficient funds! Please add more funds before recording this expense. ")
            else:
                response = call_api(
                    "post",
                    "expenses",
                    json_data={
                        "amount": amount,
                        "category": category,
                        "date": str(exp_date),
                        "description": description,
                    },
                )
                if response:
                    st.success("Expense added successfully! ✅")
                    st.session_state["user"]["balance"] -= amount
                    st.rerun()


# View / Manage Expenses (User only)

def view_expenses_page():
    """Page for users to view, filter, and manage their expenses."""
    if st.session_state["user"]["role"] != "user":
        st.error("This feature is for users only. ")
        return

    st.header("My Expenses")
    
    expenses = call_api("get", "expenses")
    if not expenses:
        st.info("No expenses found. Time to start tracking! ")
        return

    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])

    st.subheader("Filter Expenses")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=df["date"].min().date() if not df.empty else date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=df["date"].max().date() if not df.empty else date.today())

    categories = df["category"].unique().tolist()
    selected_category = st.selectbox("Filter by Category", ["All"] + categories)

    filtered_df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]
    if selected_category != "All":
        filtered_df = filtered_df[filtered_df["category"] == selected_category]

    st.markdown("---")

    if not filtered_df.empty:
        st.subheader("Expense List")
        st.dataframe(filtered_df[["date", "category", "amount", "description", "id"]].sort_values(by='date', ascending=False))
        st.markdown(f"**Total for Selected Period:** <span style='font-size: 1.25rem; font-weight: bold; color: #333;'>${filtered_df['amount'].sum():,.2f}</span>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(" Manage Individual Expenses")
        for _, exp in filtered_df.iterrows():
            with st.expander(f"Edit/Delete: {exp['category']} on {exp['date'].date()} for ${exp['amount']:.2f}"):
                with st.form(f"update_form_{exp['id']}"):
                    new_amount = st.number_input("New Amount", value=float(exp['amount']), format="%.2f")
                    new_desc = st.text_input("New Description", value=exp['description'])
                    
                    update_col, delete_col = st.columns(2)
                    with update_col:
                        if st.form_submit_button("Update Expense"):
                            amount_change = new_amount - float(exp['amount'])
                            if amount_change > st.session_state["user"].get("balance", 0.0):
                                st.error("Insufficient funds to update expense to this amount. ")
                            else:
                                response = call_api(
                                    "put",
                                    f"expenses/{exp['id']}",
                                    json_data={"amount": new_amount, "description": new_desc}
                                )
                                if response:
                                    st.success("Expense updated successfully! ")
                                    st.session_state["user"]["balance"] -= amount_change
                                    st.rerun()
                    with delete_col:
                        if st.form_submit_button(" Delete Expense"):
                            response = call_api("delete", f"expenses/{exp['id']}")
                            if response:
                                st.success("Expense deleted successfully! ")
                                st.session_state["user"]["balance"] += float(exp["amount"])
                                st.rerun()

    else:
        st.info("No expenses found for the selected filters. Try adjusting your dates or category. ")


# Weekly / Monthly Reports (User only)

def reports_page():
    """Reports page with weekly and monthly expense tables and charts with date selectors."""
    if st.session_state["user"]["role"] != "user":
        st.error("This feature is for users only. ")
        return

    st.header(" Expense Reports & Analytics")
    expenses = call_api("get", "expenses")
    
    st.subheader("Current Budget Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Allotted Funds", f"{st.session_state['user'].get('balance', 0.0):,.2f}")
    
    if not expenses:
        with col2:
            st.metric("Total Spending", "0.00")
        st.info("No expenses found. Add some to see your reports! ")
        return

    df = pd.DataFrame(expenses)
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values(by="date", ascending=False, inplace=True)
    
    total_spending = df['amount'].sum()
    with col2:
        st.metric("Total Spending", f"{total_spending:,.2f}")

    st.markdown("---")
    st.subheader("🗓 Weekly Expenses")
    week_start_date = st.date_input("Select a date to view its week's expenses:", value=date.today())
    
    weekly_df = df[
        (df["date"].dt.date >= week_start_date - timedelta(days=week_start_date.weekday())) &
        (df["date"].dt.date < week_start_date - timedelta(days=week_start_date.weekday()) + timedelta(days=7))
    ].copy()
    
    if not weekly_df.empty:
        st.dataframe(weekly_df[["date", "category", "amount", "description"]])
        st.markdown(f"**Weekly Total:** <span style='font-weight: bold;'>{weekly_df['amount'].sum():,.2f}</span>", unsafe_allow_html=True)
    else:
        st.info("No expenses found for the selected week. ")

    st.markdown("---")
    st.subheader(" Monthly Expenses")
    month_date = st.date_input("Select a date to view its month's expenses:", value=date.today(), key="month_date_input")
    monthly_df = df[
        (df["date"].dt.year == month_date.year) &
        (df["date"].dt.month == month_date.month)
    ].copy()
    
    if not monthly_df.empty:
        st.dataframe(monthly_df[["date", "category", "amount", "description"]])
        st.markdown(f"**Monthly Total:** <span style='font-weight: bold;'>{monthly_df['amount'].sum():,.2f}</span>", unsafe_allow_html=True)
    else:
        st.info("No expenses found for the selected month. ")
    
    st.markdown("---")
    st.subheader(" Top Categories by Expense")
    unique_categories = df['category'].unique()
    if len(unique_categories) > 0:
        top_n = st.slider(
            "Number of Top Categories",
            min_value=1,
            max_value=len(unique_categories),
            value=min(3, len(unique_categories))
        )
        category_totals = df.groupby("category")["amount"].sum().nlargest(top_n)
        if not category_totals.empty:
            fig_bar = px.bar(
                category_totals,
                x=category_totals.index,
                y=category_totals.values,
                title="Top Expenses by Category",
                labels={"x": "Category", "y": "Total Amount"},
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Pie Chart Breakdown")
        category_amounts = df.groupby("category")["amount"].sum().reset_index()
        fig_pie = px.pie(
            category_amounts,
            values="amount",
            names="category",
            title="Expense Distribution by Category",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.G10
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No expenses to rank or visualize. ")


# Category Management (Admin only)

def categories_page():
    """Page for admins to manage expense categories."""
    st.header("Category Management")
    if st.session_state["user"]["role"] != "admin":
        st.error("Admin access required. ")
        return

    with st.form("add_category"):
        st.subheader("Add a New Category")
        name = st.text_input("Category Name", placeholder="e.g., Groceries, Transport")
        submitted = st.form_submit_button("Add Category")
        if submitted:
            response = call_api("post", "categories", json_data={"name": name})
            if response:
                st.success("Category created successfully! ")
                st.rerun()

    st.markdown("---")
    st.subheader("Manage Existing Categories")
    categories = call_api("get", "categories")
    if not categories:
        st.info("No categories found. Add some above!")
        return

    for cat in categories:
        with st.expander(f"Edit/Delete: {cat['name']}"):
            with st.form(f"cat_form_{cat['id']}"):
                new_name = st.text_input("New Name", value=cat['name'])
                update_col, delete_col = st.columns(2)
                with update_col:
                    if st.form_submit_button(" Update"):
                        response = call_api(
                            "put", 
                            f"categories/{cat['id']}", 
                            json_data={"name": new_name}
                        )
                        if response:
                            st.success("Category updated successfully!")
                            st.rerun()
                with delete_col:
                    if st.form_submit_button(" Delete"):
                        response = call_api("delete", f"categories/{cat['id']}")
                        if response:
                            st.success("Category deleted successfully! ")
                            st.rerun()


# Admin Panel (Admin only)

def admin_panel():
    """Page for admins to manage users."""
    st.header(" Admin Panel")
    if st.session_state["user"]["role"] != "admin":
        st.error("Admin access required. ")
        return

    users = call_api("get", "admin/users")
    if not users:
        st.info("No users found.")
        return

    st.subheader("Manage Users")
    for user in users:
        with st.expander(f"{user['username']} ({user['role']})"):
            st.write(f"**Full Name:** {user.get('full_name', 'N/A')}")
            st.write(f"**Email:** {user.get('email', 'N/A')}")
            
            if user['role'] == 'user':
                balance = user.get('balance')
                if balance is None:
                    balance = 0.0
                st.write(f"**Balance:** ${balance:,.2f}")

            with st.form(f"user_form_{user['username']}"):
                new_role = st.selectbox("New Role", ["user", "admin"], index=(0 if user['role'] == "user" else 1))
                update_col, delete_col = st.columns(2)
                with update_col:
                    if st.form_submit_button("Update Role"):
                        response = call_api(
                            "post",
                            "admin/promote",
                            json_data={"username": user['username'], "new_role": new_role}
                        )
                        if response:
                            st.success(response["message"], icon="✅")
                            st.rerun()
                with delete_col:
                    if st.form_submit_button("🗑 Delete User"):
                        response = call_api("delete", f"admin/users/{user['username']}")
                        if response:
                            st.success(response["message"], icon="✅")
                            st.rerun()


# Main App Logic

def main():
    """Main application loop to handle page routing."""
    if "token" not in st.session_state:
        choice = st.sidebar.radio("Navigation", ["User Login", "Admin Login", "Register"])
        if choice == "User Login":
            login(role_check="user")
        elif choice == "Admin Login":
            login(role_check="admin")
        else:
            register()
    else:
        user = st.session_state['user']
        st.sidebar.markdown(f"** Welcome, {user.get('full_name', user['username'])}**")
        st.sidebar.markdown(f"Role: **{user.get('role')}**")
        st.sidebar.markdown("---")
        
        if user["role"] == "user":
            options = ["Manage Budget", "Add Expense", "View Expenses", "Reports", "Logout"]
        else:
            options = ["Categories", "Admin Panel", "Logout"]

        choice = st.sidebar.radio("Menu", options)

        if choice == "Manage Budget":
            manage_budget_page()
        elif choice == "Add Expense":
            add_expense_page()
        elif choice == "View Expenses":
            view_expenses_page()
        elif choice == "Reports":
            reports_page()
        elif choice == "Categories":
            categories_page()
        elif choice == "Admin Panel":
            admin_panel()
        elif choice == "Logout":
            st.session_state.clear()
            st.info("You have been logged out. ")
            st.rerun()

if __name__ == "__main__":
    main()