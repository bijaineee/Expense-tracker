
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Expense Manager",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# 2. LOAD CUSTOM CSS SAFELY
# --------------------------------------------------

try:
    with open("style.css", "r", encoding="utf-8") as css_file:
        st.markdown(
            f"<style>{css_file.read()}</style>",
            unsafe_allow_html=True,
        )
except FileNotFoundError:
    st.warning(
        "style.css was not found. The application will use "
        "Streamlit's default styling."
    )


# --------------------------------------------------
# 3. DATABASE CONFIGURATION
# --------------------------------------------------

DB_NAME = "expense.db"


def get_connection():
    """Create a new SQLite connection."""
    connection = sqlite3.connect(
        DB_NAME,
        timeout=10,
    )
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create the expenses table if it does not exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expense (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                date TEXT NOT NULL
            )
            """
        )


# --------------------------------------------------
# 4. DATABASE CRUD FUNCTIONS
# --------------------------------------------------

def add_expense(category, amount, expense_date):
    """Insert a new expense."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expense (category, amount, date)
            VALUES (?, ?, ?)
            """,
            (category, float(amount), expense_date.isoformat()),
        )
        return cursor.lastrowid


def view_expenses():
    """Return all expenses as a DataFrame."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, category, amount, date
            FROM expense
            ORDER BY date DESC, id DESC
            """
        ).fetchall()

    df = pd.DataFrame(
        [dict(row) for row in rows],
        columns=["id", "category", "amount", "date"],
    )

    if not df.empty:
        df["date"] = pd.to_datetime(
            df["date"], errors="coerce"
        ).dt.date

    return df


def get_expense(expense_id):
    """Fetch one expense by ID."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, category, amount, date
            FROM expense
            WHERE id = ?
            """,
            (int(expense_id),),
        ).fetchone()

    return dict(row) if row else None


def update_expense(expense_id, category, amount, expense_date):
    """Update an existing expense."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE expense
            SET category = ?, amount = ?, date = ?
            WHERE id = ?
            """,
            (
                category,
                float(amount),
                expense_date.isoformat(),
                int(expense_id),
            ),
        )
        return cursor.rowcount > 0


def delete_expense(expense_id):
    """Delete an expense by ID."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM expense WHERE id = ?",
            (int(expense_id),),
        )
        return cursor.rowcount > 0


# --------------------------------------------------
# 5. VALIDATION AND DISPLAY HELPERS
# --------------------------------------------------

def validate_expense(category, amount):
    """Validate expense details before saving."""
    if not category or not category.strip():
        return "Please enter an expense category."

    if amount <= 0:
        return "Amount must be greater than ₹0."

    return None


def display_expenses(df):
    """Display expenses with readable column names."""
    if df.empty:
        st.info("No expenses found. Add your first expense!")
        return

    display_df = df.rename(
        columns={
            "id": "ID",
            "category": "Category",
            "amount": "Amount (₹)",
            "date": "Date",
        }
    )

    display_df["Amount (₹)"] = display_df["Amount (₹)"].map(
        lambda amount: f"₹{amount:,.2f}"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# 6. MAIN APPLICATION
# --------------------------------------------------

def expense_app():

    try:
        initialize_database()
        df = view_expenses()

        st.title("💸 Expense Tracker")
        st.caption(
            "Manage your daily expenses and keep track of your spending."
        )

        # Sidebar navigation
        page = st.sidebar.radio(
            "Navigation",
            [
                "🏠 Dashboard",
                "➕ Add Expense",
                "📋 View Expenses",
                "✏️ Update Expense",
                "🗑️ Delete Expense",
            ],
        )

        st.sidebar.divider()
        st.sidebar.caption("Expense Manager | Python + SQLite")

        # ---------------- DASHBOARD ----------------

        if page == "🏠 Dashboard":

            st.subheader("📊 Financial Overview")

            total = float(df["amount"].sum()) if not df.empty else 0.0
            count = len(df)
            average = total / count if count else 0.0

            col1, col2, col3 = st.columns(3)

            col1.metric("💰 Total Expenses", f"₹{total:,.2f}")
            col2.metric("🧾 Total Records", count)
            col3.metric("📈 Average Expense", f"₹{average:,.2f}")

            st.divider()
            st.subheader("🕒 Recent Expenses")

            display_expenses(df.head(5))

            if not df.empty:
                st.subheader("📂 Spending by Category")

                category_totals = (
                    df.groupby("category")["amount"]
                    .sum()
                    .sort_values(ascending=False)
                )

                st.bar_chart(category_totals)

        # ---------------- ADD EXPENSE ----------------

        elif page == "➕ Add Expense":

            st.subheader("➕ Add a New Expense")

            with st.form("add_expense_form", clear_on_submit=True):

                category = st.text_input(
                    "Expense Category",
                    placeholder="e.g. Food, Travel, Shopping",
                )

                amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=10.0,
                    format="%.2f",
                )

                expense_date = st.date_input(
                    "Expense Date",
                    value=date.today(),
                )

                submitted = st.form_submit_button(
                    "💾 Save Expense",
                    use_container_width=True,
                )

                if submitted:
                    error = validate_expense(category, amount)

                    if error:
                        st.error(error)
                    else:
                        new_id = add_expense(
                            category.strip(),
                            amount,
                            expense_date,
                        )
                        st.success(
                            f"Expense saved successfully! ID: {new_id}"
                        )
                        st.rerun()

        # ---------------- VIEW EXPENSES ----------------

        elif page == "📋 View Expenses":

            st.subheader("📋 All Expenses")

            if df.empty:
                st.info("No expenses available yet.")
            else:
                search = st.text_input(
                    "🔎 Search by category",
                    placeholder="Type a category name...",
                )

                filtered_df = df.copy()

                if search.strip():
                    filtered_df = filtered_df[
                        filtered_df["category"].str.contains(
                            search.strip(),
                            case=False,
                            na=False,
                        )
                    ]

                display_expenses(filtered_df)

                filtered_total = float(filtered_df["amount"].sum())
                st.metric(
                    "Total of Displayed Expenses",
                    f"₹{filtered_total:,.2f}",
                )

        # ---------------- UPDATE EXPENSE ----------------

        elif page == "✏️ Update Expense":

            st.subheader("✏️ Update an Expense")

            if df.empty:
                st.info("There are no expenses to update.")
            else:
                display_expenses(df)

                expense_ids = df["id"].astype(int).tolist()

                selected_id = st.selectbox(
                    "Select Expense ID",
                    options=expense_ids,
                    format_func=lambda item: (
                        f"ID {item} — "
                        f"{get_expense(item)['category']} "
                        f"(₹{get_expense(item)['amount']:,.2f})"
                    ),
                )

                selected = get_expense(selected_id)

                if selected:
                    with st.form("update_expense_form"):

                        updated_category = st.text_input(
                            "Category",
                            value=selected["category"],
                        )

                        updated_amount = st.number_input(
                            "Amount (₹)",
                            min_value=0.0,
                            value=float(selected["amount"]),
                            step=10.0,
                            format="%.2f",
                        )

                        updated_date = st.date_input(
                            "Date",
                            value=date.fromisoformat(selected["date"]),
                        )

                        submitted = st.form_submit_button(
                            "💾 Update Expense",
                            use_container_width=True,
                        )

                        if submitted:
                            error = validate_expense(
                                updated_category,
                                updated_amount,
                            )

                            if error:
                                st.error(error)
                            else:
                                success = update_expense(
                                    selected_id,
                                    updated_category.strip(),
                                    updated_amount,
                                    updated_date,
                                )

                                if success:
                                    st.success(
                                        "Expense updated successfully!"
                                    )
                                    st.rerun()
                                else:
                                    st.error(
                                        "Expense not found. Please refresh."
                                    )

        # ---------------- DELETE EXPENSE ----------------

        elif page == "🗑️ Delete Expense":

            st.subheader("🗑️ Delete an Expense")

            if df.empty:
                st.info("There are no expenses to delete.")
            else:
                display_expenses(df)

                expense_ids = df["id"].astype(int).tolist()

                selected_id = st.selectbox(
                    "Select Expense ID to Delete",
                    options=expense_ids,
                    format_func=lambda item: (
                        f"ID {item} — "
                        f"{get_expense(item)['category']} "
                        f"(₹{get_expense(item)['amount']:,.2f})"
                    ),
                )

                selected = get_expense(selected_id)

                if selected:
                    st.warning(
                        f"You are about to delete "
                        f"'{selected['category']}' "
                        f"— ₹{selected['amount']:,.2f}."
                    )

                    confirmed = st.checkbox(
                        "I confirm that I want to delete this expense.",
                        key="confirm_delete",
                    )

                    if st.button(
                        "🗑️ Delete Selected Expense",
                        type="primary",
                        disabled=not confirmed,
                        use_container_width=True,
                    ):
                        success = delete_expense(selected_id)

                        if success:
                            st.success("Expense deleted successfully!")
                            st.rerun()
                        else:
                            st.error(
                                "Expense not found. Please refresh."
                            )

    except sqlite3.Error:
        st.error(
            "A database error occurred. Please check the database "
            "file and ensure it is accessible."
        )

    except (ValueError, TypeError) as error:
        st.error(f"Please check the entered data. Details: {error}")


# --------------------------------------------------
# 7. RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    expense_app()
