"""
Quota and access-control helpers.

Whitelist: three owner emails that bypass all limits (for testing).
Personal email detection: blocks personal Gmail/Yahoo/etc. from founder sign-up.
"""

from __future__ import annotations

USAGE_WHITELIST: frozenset[str] = frozenset({
    "sharshal499@gmail.com",
    "shindeharshal338@gmail.com",
    "kkrharsh16@gmail.com",
})

PERSONAL_EMAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.in", "yahoo.co.in", "yahoo.co.uk",
    "hotmail.com", "hotmail.in", "hotmail.co.uk",
    "outlook.com", "outlook.in",
    "live.com", "live.in",
    "aol.com",
    "protonmail.com", "proton.me",
    "icloud.com", "me.com", "mac.com",
    "ymail.com",
    "rediffmail.com",
    "zohomail.com",
    "mail.com",
    "inbox.com",
    "gmx.com", "gmx.net",
})

# Signal key written to CandidateSignal when the candidate receives recommendations
CANDIDATE_QUOTA_SIGNAL = "_chat_quota_used"

# Job signal key written when a founder completes onboarding
FOUNDER_QUOTA_SIGNAL = "_onboarding_quota_used"


def is_whitelisted(email: str) -> bool:
    """Return True if this email bypasses all usage limits."""
    return email.strip().lower() in USAGE_WHITELIST


def is_personal_email(email: str) -> bool:
    """Return True if the email uses a known personal/free provider domain."""
    if not email or "@" not in email:
        return False
    domain = email.strip().lower().split("@", 1)[1]
    return domain in PERSONAL_EMAIL_DOMAINS
