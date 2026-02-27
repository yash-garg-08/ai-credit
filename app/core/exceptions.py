class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InsufficientCreditsError(AppError):
    def __init__(self, balance: int, required: int):
        super().__init__(
            f"Insufficient credits: balance={balance}, required={required}",
            status_code=402,
        )
        self.balance = balance
        self.required = required


class SpendLimitExceededError(AppError):
    def __init__(self, message: str = "Spend limit exceeded"):
        super().__init__(message, status_code=429)


class NotFoundError(AppError):
    def __init__(self, entity: str, id: str):
        super().__init__(f"{entity} not found: {id}", status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)
