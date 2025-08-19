📈 Expense Tracker: Full-Stack Application Documentation
This document provides a detailed overview of the Expense Tracker application, a full-stack project built with a FastAPI backend and a Streamlit frontend. The application allows users to track their expenses, manage a personal budget, and provides administrators with tools for user and category management.

🚀 Application Stack
Backend: FastAPI with MongoDB for data persistence.

Frontend: Streamlit for the user interface.

Authentication: JWT (JSON Web Tokens) with OAuth2.0 for secure access.

Password Hashing: bcrypt via passlib for secure password storage.

💻 Backend API Documentation (FastAPI)
The backend provides a RESTful API to handle all data operations. All endpoints are protected and require a valid JWT token in the Authorization header, unless explicitly noted.

User & Authentication Endpoints
POST /register

Description: Creates a new user account.

Request Body: {"username": str, "password": str, "full_name": str, "email": str}

Response: {"id": str, "username": str, "full_name": str, "email": str, "role": str, "balance": float}

POST /login

Description: Authenticates a user and returns an access token.

Request Body: {"username": str, "password": str} (Form data)

Response: {"access_token": str, "token_type": "bearer"}

GET /users/me

Description: Retrieves the details of the currently authenticated user.

Authentication: Required.

Response: {"user_id": str, "username": str, "full_name": str, "email": str, "role": str, "balance": float}

Expense Endpoints (User Role)
POST /expenses

Description: Records a new expense for the authenticated user. Automatically deducts the amount from the user's balance.

Authentication: Required (User role).

Request Body: {"amount": float, "category": str, "date": str, "description": str}

Response: {"message": str, "expense_id": str}

GET /expenses

Description: Fetches a list of expenses for the authenticated user. Supports filtering by category and date range.

Authentication: Required (User role).

Query Parameters: category: Optional[str], start: Optional[str], end: Optional[str]

Response: [{"_id": str, "amount": float, "category": str, "date": str, ...}]

GET /expenses/{expense_id}

Description: Retrieves a single expense by its ID.

Authentication: Required (User role).

PUT /expenses/{expense_id}

Description: Updates an existing expense. Adjusts the user's balance accordingly.

Authentication: Required (User role).

Request Body: {"amount": Optional[float], "category": Optional[str], "date": Optional[str], "description": Optional[str]}

DELETE /expenses/{expense_id}

Description: Deletes an expense. Adds the expense amount back to the user's balance.

Authentication: Required (User role).

Funds & Category Endpoints
POST /funds

Description: Adds funds to the authenticated user's balance.

Authentication: Required (User role).

Request Body: {"amount": float}

GET /categories

Description: Lists all available expense categories.

Authentication: Required.

POST /categories

Description: Creates a new expense category.

Authentication: Required (Admin role).

PUT /categories/{category_id}

Description: Updates an existing category's name.

Authentication: Required (Admin role).

DELETE /categories/{category_id}

Description: Deletes a category.

Authentication: Required (Admin role).

Admin Endpoints (Admin Role)
GET /admin/users

Description: Lists all registered users.

Authentication: Required (Admin role).

POST /admin/promote

Description: Changes a user's role.

Authentication: Required (Admin role).

Request Body: {"username": str, "new_role": str}

DELETE /admin/users/{username}

Description: Deletes a user and all their associated expenses.

Authentication: Required (Admin role).

GET /admin/expenses

Description: Retrieves a list of all expenses from all users. Supports filtering.

Authentication: Required (Admin role).

🖼️ Frontend Application Documentation (Streamlit)
The Streamlit frontend is a single-page application that interacts with the backend API to provide a dynamic user experience. The interface is adaptive, with the navigation menu and available pages changing based on the user's role.

Core Features
Login & Registration: Separate forms for new user registration and existing user login. The login page also supports an "Admin Login" option for role-specific access.

Session Management: The application uses st.session_state to maintain user login status and store the authentication token and user data, ensuring a persistent session across interactions.

User Interface (User Role)
Authenticated users are presented with a sidebar menu to navigate through their personal expense tracker.

Manage Budget: Displays the user's current balance and allows them to add funds to their account.

Add Expense: A form to log new expenses. A check is performed on the frontend to ensure the user has sufficient funds before submitting the request.

View Expenses: A dynamic table of all expenses. Users can filter this list by date range and category. A collapsible expander for each expense allows for in-line updates and deletions.

Reports:

Weekly & Monthly Summaries: Displays expenses in tabular form for selected weeks and months.

Visualizations: Interactive bar charts and pie charts using plotly show top spending categories and the overall distribution of expenses.

Admin Interface (Admin Role)
Administrators have access to a different set of tools from the sidebar.

Category Management: A dedicated page to create, update, and delete expense categories. This ensures data consistency across the application.

Admin Panel: Provides an overview of all users in the system. Admins can view user details, change a user's role (e.g., promote a user to admin), or delete a user and all of their associated data.

How to Run the Application
Backend Setup:

Ensure you have Python 3.8+ and MongoDB installed and running.

Install the required Python packages: pip install fastapi "uvicorn[standard]" python-jose[cryptography] "passlib[bcrypt]" pymongo.

Set your environment variables: export SECRET_KEY="your-secret-key" and export MONGODB_URI="mongodb://localhost:27017".

Start the backend server: uvicorn main:app --reload.

Frontend Setup:

Install the required Python packages: pip install streamlit requests pandas plotly.

Set the API_BASE_URL in main.py if your backend is running on a different address.

Run the Streamlit app: streamlit run main.py.
