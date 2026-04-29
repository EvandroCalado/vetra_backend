# Vetra Backend API

Vetra Backend is a robust and scalable RESTful API built with modern Python technologies. It provides a solid foundation for user management, authentication, and database operations, serving as the core backend infrastructure for the Vetra project.

## 🚀 Technologies & Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) - High performance, easy to learn, fast to code, ready for production.
- **Database ORM:** [SQLAlchemy](https://www.sqlalchemy.org/) 2.0 with Asyncio support.
- **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/).
- **Database Engine:** MySQL (via `aiomysql` and Docker).
- **Authentication:** JWT (JSON Web Tokens) with HTTP-only cookies via `python-jose` and `passlib` (Argon2 for secure password hashing).
- **Environment Management:** `pydantic-settings` for robust environment variable validation.
- **Linting & Formatting:** [Ruff](https://beta.ruff.rs/docs/) - An extremely fast Python linter and code formatter.
- **Task Runner:** [Taskipy](https://github.com/illBeRoy/taskipy) for easy command execution.
- **Package Manager:** [uv](https://github.com/astral-sh/uv) - Extremely fast Python package installer and resolver.

## 📁 Project Structure

```text
vetra_backend/
├── src/
│   ├── account/          # User authentication and management module
│   │   ├── routers.py    # API endpoints (/register, /login, /me)
│   │   ├── services.py   # Business logic for accounts
│   │   ├── schemas.py    # Pydantic models for request/response validation
│   │   ├── models.py     # SQLAlchemy models (User)
│   │   ├── deps.py       # FastAPI dependencies (auth guards, DB session)
│   │   └── utils.py      # Utility functions (JWT token generation, hashing)
│   ├── db/               # Database configuration and connection setup
│   └── main.py           # FastAPI application entry point
├── migrations/           # Alembic database migration scripts
├── docker-compose.yml    # Docker configuration for MySQL database
├── pyproject.toml        # Project dependencies and tool configurations
├── alembic.ini           # Alembic configuration file
└── .env                  # Environment variables
```

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your machine:

- **Python 3.12+**
- **Docker & Docker Compose** (for running the MySQL database)
- **uv** (recommended for dependency management)

## ⚙️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/EvandroCalado/vetra_backend.git
cd vetra_backend
```

### 2. Environment Variables

Rename file `.env.example` to `.env` in the root directory and configure your environment variables.

```env
# Database Settings
DB_USER=
DB_PASSWORD=
DB_NAME=
DB_PORT=
DB_HOST=

# Security Settings
JWT_SECRET_KEY=your_super_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_TIME_MIN=
JWT_REFRESH_TOKEN_TIME_DAY=

# Email Settings
EMAIL_VERIFICATION_TOKEN_TIME_HOURS=
EMAIL_PASSWORD_RESET_TOKEN_TIME_HOUR=
```

### 3. Start the Database

The project uses Docker to run a MySQL instance in development.

```bash
docker-compose up -d
```

_This will start a MySQL container mapped to port 3306 with the credentials defined in the `docker-compose.yml` file._

### 4. Install Dependencies

Using `uv`:

```bash
uv sync
```

### 5. Run Database Migrations

Apply the existing Alembic migrations to create the necessary tables in your MySQL database:

```bash
alembic upgrade head
```

### 6. Run the Application

You can start the development server using `taskipy`:

```bash
task dev
```

The API will be available at: **http://localhost:8000**

Interactive API Documentation (Swagger UI) is automatically available at: **http://localhost:8000/docs**

## 🔐 Authentication & Security

The authentication system is built with security best practices:

- Passwords are securely hashed using **Argon2**.
- Uses **JWT (JSON Web Tokens)** for stateless authentication, with support for **Access and Refresh Tokens**.
- Tokens are automatically securely stored in **HTTP-only, Secure, SameSite=Lax cookies** to mitigate XSS attacks.
- **Email Verification** system to ensure users own their provided email addresses.
- **Password Reset** functionality using secure expiring tokens.
- **Role-Based Access Control (RBAC)** support (e.g., Admin user roles).
- Token revocation support for secure **Logout**.

### Available Endpoints

- `POST /account/register/` - Register a new user.
- `POST /account/login/` - Authenticate user and set HTTP-only cookies with JWT tokens.
- `POST /account/refresh/` - Refresh the JWT access token using the refresh token cookie.
- `POST /account/send-email-verification/` - Send an email verification link to the user.
- `POST /account/change-password/` - Change the password for the currently authenticated user.
- `POST /account/send-password-reset-email/` - Send a password reset link to the user's email.
- `POST /account/reset-password/` - Reset the user's password using a token.
- `POST /account/logout/` - Revoke tokens and clear HTTP-only cookies.
- `GET /account/me/` - Retrieve details of the currently authenticated user (Protected endpoint).
- `GET /account/verify-email/` - Verify the user's email address using a token.
- `GET /account/admin/` - Retrieve admin-only data (Requires admin privileges).

## 📜 Available Scripts (Taskipy)

We use `taskipy` to simplify running common tasks. Run these commands from the project root:

- **`task dev`**: Starts the FastAPI development server with hot-reload.
- **`task format`**: Formats the code using `ruff format`.
- **`task pre_format`**: Fixes auto-fixable linting errors using `ruff check --fix`.
- **`task lint`**: Runs the linter to check for code issues using `ruff check`.
