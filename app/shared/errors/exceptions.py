class AppException(Exception):
    """
    Excepción personalizada para errores operacionales (esperados).
    """
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_operational = True


