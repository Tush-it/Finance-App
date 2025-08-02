import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import os

# -------------------------------------
# Database Functions
# -------------------------------------
DB = 'finance_app.db'

def connect_db():
    return sqlite3.connect(DB)

def init_db():
    conn = connect_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        username TEXT,
        date TEXT,
        category TEXT,
        amount REAL,
        description TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS budget (
        username TEXT,
        category TEXT,
        monthly_limit REAL,
        PRIMARY KEY(username, category)
    )''')
    conn.commit()
    conn.close()

# -------------------------------------
# User Functions
# -------------------------------------
def login_user(username):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
    conn.commit()
    conn.close()

# -------------------------------------
# Expense Functions
# -------------------------------------
def add_expense(username, date, category, amount, description):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO expenses (username, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
              (username, date, category, amount, description))
    conn.commit()
    conn.close()

def get_expenses(username):
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM expenses WHERE username = ?", conn, params=(username,))
    conn.close()
    return df

def delete_expense(expense_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

# -------------------------------------
# Budget Functions
# -------------------------------------
def set_budget(username, category, limit):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO budget (username, category, monthly_limit) VALUES (?, ?, ?)",
              (username, category, limit))
    conn.commit()
    conn.close()

def get_budget(username):
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM budget WHERE username = ?", conn, params=(username,))
    conn.close()
    return df

# -------------------------------------
# App UI
# -------------------------------------
def main():
    st.set_page_config(page_title="💰 Finance App", layout="wide")
    st.title("💰 Personal Finance Manager")

    init_db()

    username = st.sidebar.text_input("👤 Enter your name to continue", value="guest")
    login_user(username)

    menu = st.sidebar.radio("📋 Menu", ["Dashboard", "Add Expense", "Budget", "Reports", "Import/Export"])

    if menu == "Dashboard":
        st.subheader("📊 Dashboard")

        expenses = get_expenses(username)
        if expenses.empty:
            st.info("No data yet. Add some expenses!")
        else:
            expenses["date"] = pd.to_datetime(expenses["date"])
            this_month = datetime.now().strftime('%Y-%m')
            month_expenses = expenses[expenses['date'].dt.strftime('%Y-%m') == this_month]
            total = month_expenses['amount'].sum()
            daily_avg = month_expenses.groupby(month_expenses['date'].dt.date)['amount'].sum().mean()
            st.metric("📅 Total This Month", f"₹{total:.2f}")
            st.metric("📈 Daily Avg", f"₹{daily_avg:.2f}")
            budget_df = get_budget(username)
            if not budget_df.empty:
                spent_by_cat = month_expenses.groupby('category')['amount'].sum().reset_index()
                merged = pd.merge(budget_df, spent_by_cat, on='category', how='left').fillna(0)
                merged['status'] = merged['amount'] / merged['monthly_limit']
                for _, row in merged.iterrows():
                    if row['status'] > 1:
                        st.warning(f"🚨 Over budget in {row['category']}: ₹{row['amount']:.0f} / ₹{row['monthly_limit']:.0f}")
                    elif row['status'] > 0.8:
                        st.info(f"⚠️ Almost at limit for {row['category']}: ₹{row['amount']:.0f} / ₹{row['monthly_limit']:.0f}")

    elif menu == "Add Expense":
        st.subheader("🧾 Add New Expense")
        date = st.date_input("Date", datetime.today())
        category = st.selectbox("Category", ["Food", "Transport", "Health", "Entertainment", "Other"])
        amount = st.number_input("Amount (₹)", min_value=0.01, format="%.2f")
        desc = st.text_input("Description", "")
        if st.button("➕ Add Expense"):
            add_expense(username, date.strftime('%Y-%m-%d'), category, amount, desc)
            st.success("Expense added!")

    elif menu == "Budget":
        st.subheader("💸 Set Monthly Budgets")
        category = st.selectbox("Budget Category", ["Food", "Transport", "Health", "Entertainment", "Other"])
        limit = st.number_input("Monthly Limit (₹)", min_value=0.01, format="%.2f")
        if st.button("💾 Save Budget"):
            set_budget(username, category, limit)
            st.success("Budget saved!")

    elif menu == "Reports":
        st.subheader("📈 Expense Reports")
        df = get_expenses(username)
        if df.empty:
            st.warning("No data to show.")
        else:
            df['date'] = pd.to_datetime(df['date'])
            with st.expander("🗂 View Table"):
                st.dataframe(df.sort_values('date', ascending=False))
            chart = px.pie(df, values='amount', names='category', title='Spending by Category')
            st.plotly_chart(chart)
            bar = px.bar(df, x='date', y='amount', color='category', title='Daily Spending')
            st.plotly_chart(bar)

    elif menu == "Import/Export":
        st.subheader("📤 Export / 📥 Import")
        df = get_expenses(username)
        if not df.empty:
            csv = df.to_csv(index=False).encode()
            st.download_button("Download Expenses as CSV", data=csv, file_name=f"{username}_expenses.csv", mime='text/csv')

        uploaded = st.file_uploader("Upload Expenses CSV", type='csv')
        if uploaded:
            new_df = pd.read_csv(uploaded)
            for _, row in new_df.iterrows():
                add_expense(username, row['date'], row['category'], row['amount'], row['description'])
            st.success("Expenses imported successfully!")

if __name__ == "__main__":
    main()
