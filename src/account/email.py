from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    async def send_verification_email(self, to: str, link: str) -> None:
        """Send email verification link to user."""
        ...

    @abstractmethod
    async def send_password_reset_email(self, to: str, link: str) -> None:
        """Send password reset link to user."""
        ...


class ConsoleEmailProvider(EmailProvider):
    async def send_verification_email(self, to: str, link: str) -> None:
        print(f'[DEV] Verification link for {to}: {link}')

    async def send_password_reset_email(self, to: str, link: str) -> None:
        print(f'[DEV] Password reset link for {to}: {link}')


class SMTPEmailProvider(EmailProvider):
    """Email provider for SMTP integration (future implementation)."""

    def __init__(self, host: str = 'localhost', port: int = 587):
        self.host = host
        self.port = port

    async def send_verification_email(self, to: str, link: str) -> None:
        raise NotImplementedError('SMTP integration not implemented yet')

    async def send_password_reset_email(self, to: str, link: str) -> None:
        raise NotImplementedError('SMTP integration not implemented yet')
