"""
Locators for LoginPage.
Update selectors using: framework inspect-dom --url <login_url>
or MCP tool: inspect_current_dom(url, selector="form")
"""


class LoginLocators:
    """CSS selectors for the Login page. All values are intentionally conservative
    (prefer stable attributes: id, name, role, data-testid over fragile class chains)."""

    # Form fields
    EMAIL_FIELD: str = "#email, input[name='email'], input[type='email']"
    PASSWORD_FIELD: str = "#password, input[name='password'], input[type='password']"

    # Submit
    SUBMIT_BUTTON: str = "button[type='submit'], input[type='submit'], #login-btn"

    # Feedback
    ERROR_MESSAGE: str = (
        "[role='alert'], .error-message, .alert-danger, "
        "#error-container, [data-testid='login-error']"
    )
    SUCCESS_FLASH: str = ".alert-success, [role='alert'].success, [data-testid='login-success']"

    # Page indicators
    PAGE_HEADING: str = "h1, [data-testid='page-heading']"
    PAGE_INDICATOR: str = "form[id], form[action*='login'], #login-form"

    # Navigation
    FORGOT_PASSWORD_LINK: str = "a[href*='forgot'], a[href*='reset'], [data-testid='forgot-password']"
    REGISTER_LINK: str = "a[href*='register'], a[href*='signup'], [data-testid='register-link']"
