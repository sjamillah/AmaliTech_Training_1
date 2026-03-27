from amalitech_training.clean_code_testing_and_git.LAB_3.repositories import InMemoryUserRepository
from amalitech_training.clean_code_testing_and_git.LAB_3.password_hasher import BcryptPasswordHasher
from amalitech_training.clean_code_testing_and_git.LAB_3.user_service import UserService

service = UserService(
    repository=InMemoryUserRepository(),
    hasher=BcryptPasswordHasher(),
)

# Register
user = service.register('John Doe', 'john_d', 'john@example.com', 'passh123', 'passh123')
print(f'Registered: {user}')

# Login
logged_in = service.login('john_d', 'passh123')
print(f'Logged in: {logged_in}')
