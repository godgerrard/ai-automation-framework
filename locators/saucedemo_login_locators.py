"""Locators for the SauceDemo login page (saucedemo.com)."""


class SauceDemoLoginLocators:
    USERNAME_FIELD: str = "[data-test='username']"
    PASSWORD_FIELD: str = "[data-test='password']"
    LOGIN_BUTTON: str = "[data-test='login-button']"
    ERROR_MESSAGE: str = "[data-test='error']"
    ERROR_DISMISS: str = ".error-button"
    LOGIN_LOGO: str = ".login_logo"
    LOGIN_WRAPPER: str = ".login_wrapper"
    LOGIN_FORM: str = "#login_button_container"
