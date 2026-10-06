
def calculate_severity(title, description=""):
    text = (title + " " + description).lower()
    high_keywords = [
        "fraud", "fraudulent", "scam", "unauthorized", "unauthorised",
        "unrecognized", "unrecognised", "compromised", "hacked", "phishing",
        "otp fraud", "otp shared", "someone used my", "someone is using my",
        "suspicious transaction", "suspicious activity",
        "card stolen", "stolen card", "card lost", "lost card",
        "card retained", "card swallowed", "atm retained", "atm swallowed",
        "card blocked", "card compromised",
        "cash not dispensed", "did not dispense", "cash not received",
        "did not receive cash", "cash was not received",
        "atm did not give", "atm not give", "no cash came",
        "amount debited", "amount was debited", "account debited",
        "debited but", "deducted but", "money deducted",
        "money was deducted", "balance deducted",
        "account blocked", "account frozen", "account suspended",
        "account locked", "account hacked", "account compromised",
        "unable to access", "cannot access account",
        "not received", "transfer failed", "neft failed", "rtgs failed",
        "imps failed", "upi failed", "payment failed",
        "double debit", "double charge", "duplicate charge",
        "duplicate debit", "charged twice", "debited twice",
        "emi bounced", "loan account blocked", "foreclosure",
        "account deactivated", "kyc pending", "kyc freeze",
    ]
    medium_keywords = [
        "not working", "issue", "problem", "error", "failed",
        "unable", "cannot", "delay", "pending", "refund",
        "statement", "passbook", "cheque", "interest", "charge",
        "fee", "update", "change", "request", "query",
    ]
    for kw in high_keywords:
        if kw in text:
            return "High", kw
    for kw in medium_keywords:
        if kw in text:
            return "Medium", kw
    return "Low", "none"


tests = [
    ("ATM did not dispense cash but amount was debited",
     "I tried to withdraw Rs 5000 from SBI ATM. Machine showed Transaction Successful but no cash came out. My account shows a debit of Rs 5000."),
    ("ATM card swallowed by machine",
     "My debit card got stuck and was retained by the ATM machine. Screen went blank."),
    ("Unauthorized transaction on my credit card",
     "I received an SMS alert showing a transaction of Rs 12500 at an online merchant which I did not make. Please block the card."),
    ("Duplicate charge from Swiggy on my account",
     "My bank account was debited twice Rs 450 at 7:30 PM and again Rs 450 at 7:31 PM on the same order."),
    ("UPI payment failed but money was deducted",
     "I sent Rs 2000 via Google Pay but the app shows Payment Failed. However Rs 2000 has been debited from my savings account."),
    ("NEFT transfer not received by beneficiary",
     "I transferred Rs 50000 via NEFT to my vendor. Beneficiary says amount has not been credited."),
    ("Someone made transactions using my account without my knowledge",
     "I received multiple OTPs I did not request and got SMS alerts of 3 transactions totalling Rs 28000. I suspect my account has been compromised."),
    ("Account frozen due to KYC non-compliance",
     "My savings account has been frozen and I cannot make any transactions. KYC documents are pending."),
    ("What are the interest rates for FD",
     "I want to know the current fixed deposit interest rates for senior citizens."),
]

print("=" * 80)
print(f"{'TITLE':<52} {'SEV':<8} {'MATCHED KEYWORD'}")
print("=" * 80)
for title, desc in tests:
    sev, kw = calculate_severity(title, desc)
    pri = "P1" if sev == "High" else ("P2" if sev == "Medium" else "P3")
    marker = ">>HIGH<<" if sev == "High" else ("  med  " if sev == "Medium" else "  low  ")
    print(f"{marker}  {title[:50]:<50}  {pri}  [{kw}]")
print("=" * 80)
