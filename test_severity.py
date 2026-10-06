from app import calculate_severity, calculate_priority

tests = [
    ("ATM did not dispense cash but amount was debited",
     "I tried to withdraw Rs 5000 from SBI ATM. Machine showed Transaction Successful but no cash came out. My account shows a debit of Rs 5000."),
    ("ATM card swallowed by machine",
     "My debit card got stuck and was retained by the ATM machine. The screen went blank and the card did not come back."),
    ("Unauthorized transaction on my credit card",
     "I received an SMS alert showing a transaction of Rs 12500 at an online merchant which I did not make. Please block the card and initiate a dispute."),
    ("Duplicate charge from Swiggy on my account",
     "My bank account was debited twice Rs 450 at 7:30 PM and again Rs 450 at 7:31 PM on the same order. I need a refund for the duplicate charge."),
    ("UPI payment failed but money was deducted",
     "I sent Rs 2000 via Google Pay but the app shows Payment Failed. However Rs 2000 has been debited from my savings account."),
    ("NEFT transfer not received by beneficiary",
     "I transferred Rs 50000 via NEFT to my vendor. Today is Wednesday and the beneficiary says the amount has not been credited."),
    ("Someone made transactions using my account without my knowledge",
     "I received multiple OTPs I did not request and got SMS alerts of 3 transactions totalling Rs 28000. I suspect my account has been compromised."),
    ("Account frozen due to KYC non-compliance",
     "My savings account has been frozen and I cannot make any transactions. KYC documents are pending. I need my account unblocked urgently."),
    ("General query about interest rates",
     "I want to know the current FD interest rates for senior citizens."),
]

print("=" * 72)
print(f"  {'TITLE':<50} {'SEV':<8} PRI")
print("=" * 72)
all_pass = True
for title, desc in tests:
    sev = calculate_severity(title, desc)
    pri = calculate_priority(sev)
    flag = "OK" if sev in ("High", "Medium") else "LOW"
    print(f"  {title[:50]:<50} {sev:<8} {pri}  [{flag}]")
print("=" * 72)
print("Done.")
