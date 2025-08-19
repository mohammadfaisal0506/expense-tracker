📈 Expense Tracker: Project Summary
This project is a full-stack expense tracking application featuring a FastAPI backend and a Streamlit frontend. The system enables users to manage their personal finances by tracking expenses against a budget, while also providing administrators with a powerful control panel.

💻 Backend: FastAPI & MongoDB
The backend is built with FastAPI, providing a secure, role-based API for all application data.

Authentication: Uses JWT and OAuth2.0 for secure user sessions, with bcrypt for password hashing.

Roles: Supports two distinct roles: user and admin.

User Management: Endpoints for user registration, login, and profile retrieval.

Expense & Funds: Users can add, view, update, and delete expenses. The system tracks a balance for each user, deducting expenses and allowing users to add funds.

Categories: A separate collection for expense categories.

Admin Privileges: Administrators have exclusive access to manage all users, expenses, and categories within the system.

🖼️ Frontend: Streamlit
The frontend is a single-page, multi-purpose dashboard built with Streamlit. It provides a clean, responsive user interface that adapts based on the user's role.

User Interface: A dark-themed UI with clear navigation and interactive components.

Data Visualization: Uses Pandas for data manipulation and Plotly to create interactive charts (bar charts and pie charts) that visualize spending habits.

User Dashboard:

Budget Management: Displays current balance and an option to add funds.

Expense Tracking: A table view with filters and inline forms to edit or delete individual expenses.

Reports: Displays weekly and monthly expense summaries.

Admin Panel:

User Management: A simple interface to view, promote, or delete users.

Category Management: Allows admins to add, update, or remove expense categories.

The application is a complete and functional system for personal finance management, demonstrating robust API design, secure authentication, and a user-friendly interface.
