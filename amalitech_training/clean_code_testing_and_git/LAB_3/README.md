# LAB_3 — User Authentication Service

A reusable Python library that handles user registration and login.
This is not a web app — it is a standalone module you wire into
whatever application needs authentication.

---

## What it does

- Registers a new user with a name, username, email or phone, and password
- Hashes passwords with bcrypt before storing them
- Verifies credentials on login
- Raises specific exceptions for each failure case
- Logs every significant auth event

---

## Folder structure
```
LAB_3/
├── exceptions.py      custom exception classes
├── interfaces.py      abstract base classes (UserRepository, PasswordHasher)
├── models.py          User dataclass
├── password_hasher.py bcrypt implementation
├── repositories.py    in-memory user store
├── user_service.py    register() and login() logic
└── test_lab3.py       full test suite
```

## Design

The service depends on two interfaces rather than concrete classes.
You inject a repository and a hasher when creating UserService,
which means you can swap either one without touching the service itself.
Tests use a plain-text hasher instead of bcrypt so they run fast.
```
UserService
    depends on -> UserRepository (interface)
                  implemented by -> InMemoryUserRepository

    depends on -> PasswordHasher (interface)
                  implemented by -> BcryptPasswordHasher
```

This is the Dependency Inversion principle from SOLID.

---

## How to use it
```python
from amalitech_training.clean_code_testing_and_git.LAB_3.repositories import (
    InMemoryUserRepository,
)
from amalitech_training.clean_code_testing_and_git.LAB_3.password_hasher import (
    BcryptPasswordHasher,
)
from amalitech_training.clean_code_testing_and_git.LAB_3.user_service import UserService

service = UserService(
    repository=InMemoryUserRepository(),
    hasher=BcryptPasswordHasher(),
)

# Register
user = service.register(
    name="Joshua Alana",
    username="joshua_a",
    email="joshua@example.com",
    password="secure123",
    confirm_password="secure123",
)

# Login
logged_in = service.login(username="joshua_a", password="secure123")
```

---

## Running the tests
```bash
poetry run pytest amalitech_training/clean_code_testing_and_git/LAB_3/test_lab3.py -v
```

With coverage:
```bash
poetry run pytest \
  amalitech_training/clean_code_testing_and_git/LAB_3/test_lab3.py \
  --cov=amalitech_training/clean_code_testing_and_git/LAB_3 \
  --cov-report=term-missing \
  --cov-branch -v
```

Current coverage: 100%

---

## Error handling

| Exception | When it is raised |
|---|---|
| `UserAlreadyExistsError` | username or email already registered |
| `UserNotFoundError` | login with unknown username |
| `InvalidPasswordError` | passwords don't match, too short, or wrong on login |