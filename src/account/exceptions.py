class DomainError(Exception):
    status_code: int = 500

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UserAlreadyExistsError(DomainError):
    status_code = 409


class InvalidCredentialsError(DomainError):
    status_code = 401


class OldPasswordMismatchError(DomainError):
    status_code = 400


class UserNotFoundError(DomainError):
    status_code = 404


class InvalidOrExpiredTokenError(DomainError):
    status_code = 400


class RefreshTokenMissingError(DomainError):
    status_code = 401
