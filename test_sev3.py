from classifier import classify_ticket
from app import calculate_severity, calculate_priority

tests = [
    # Expected High
    ("ATM did not dispense cash but amount was debited",
     "I tried to withdraw Rs 5000 from SBI ATM. Machine showed Transaction Successful but no cash came out. My account shows a debit of Rs 5000."),
    ("ATM card swallowed by machine",
     "My debit card got stuck and was retained by the ATM machine. The screen went blank."),
    ("Unauthorized transaction on my credit card",
     "I received an SMS alert showing a transaction of Rs 12500 at an online merchant which I did not make. Please block the card."),
    ("Duplicate charge from Swiggy on my account",
     "My bank account was debited twice Rs 450 at 7:30 PM and again Rs 450 at 7:31 PM on the same order."),
    ("UPI payment failed but money was deducted",
     "I sent Rs 2000 via Google Pay but the app shows Payment Failed. However Rs 2000 has been debited from my savings account."),
    ("NEFT transfer not received by beneficiary",
     "I transferred Rs 50000 via NEFT. Today is Wednesday and the beneficiary says the amount has not been credited."),
    ("Someone made transactions using my account without my knowledge",
     "I received multiple OTPs I did not request. I suspect my account has been compromised. Please block everything."),
    ("Lost my debit card and need it blocked immediately",
     "I lost my wallet along with my debit card. Please block the card immediately before someone misuses it."),
    # Expected Medium
    ("Card not working at POS terminal",
     "My Visa debit card is being declined at shops but works at ATMs. This started today."),
    ("Refund not showing in my account",
     "I returned a product to Amazon 10 days ago. They confirmed refund initiated but it has not shown in my account."),
    ("Pending transfer not credited yet",
     "I made a bank transfer 2 days ago. The amount is still showing as pending and has not been credited."),
    ("Need to change my ATM PIN",
     "I want to change my ATM PIN. I forgot the current one and need help resetting it."),
    ("Card delivery not received",
     "I applied for a new debit card 2 weeks ago but have not received it yet. Please check the delivery status."),
    # Expected Low
    ("What are the FD interest rates for senior citizens",
     "I want to know the current fixed deposit interest rates available for senior citizens at your bank."),
    ("How to link my card to Google Pay",
     "I want to add my debit card to Google Pay. Please guide me through the process."),
    ("What currencies does the card support",
     "I am travelling abroad and want to know which foreign currencies my Visa card supports."),
]

EXPECTED = ["High"]*8 + ["Medium"]*5 + ["Low"]*3

print("=" * 85)
print(f"  {'TITLE':<48} {'CAT (predicted)':<30} SEV  PRI  OK?")
print("=" * 85)
correct = 0
for i, (title, desc) in enumerate(tests):
    cat, conf = classify_ticket(title + " " + desc)
    sev = calculate_severity(title, desc)
    pri = calculate_priority(sev)
    exp = EXPECTED[i]
    ok  = "✓" if sev == exp else f"✗ (exp {exp})"
    if sev == exp:
        correct += 1
    print(f"  {title[:48]:<48} {cat[:28]:<30} {sev:<6} {pri:<5} {ok}")

print("=" * 85)
print(f"Accuracy: {correct}/{len(tests)} ({round(correct/len(tests)*100)}%)")
