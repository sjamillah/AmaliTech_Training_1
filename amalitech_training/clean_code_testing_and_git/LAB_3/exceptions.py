"""
Custom exceptions for the User Authentication Service Module
"""
class UserAlreadyExistsError(Exception):
    """
    Raised when registration uses a username or email that is in the system

    Triggered by the UserService.register() before the password setting
    """


class UserNotFoundError(Exception):
    """
    Raised when a user isn't registered

    Triggered by the UserService.login() as the first. If user ain't found password ain't checked.
    """


class InvalidPasswordError(Exception):
    """
    Raised when a password ain't valid

    Triggered during:
        Registration: password != confirm_password or password is shorter than minimal length
        Login: the username exists but the password does not match the stored hash
    """
    
