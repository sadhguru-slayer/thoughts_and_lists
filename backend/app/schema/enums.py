from enum import Enum

class OTPPurpose(str, Enum):
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"