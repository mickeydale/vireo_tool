"""
Vireo Audio -- AI-Assisted Ticket Categoriser
============================================
Classifies support tickets using keyword rules derived from the ticket corpus.
No external API calls required (zero cost per run).

Usage:
    python categorize.py                          # runs on tickets.csv, outputs results
    python categorize.py --validate               # runs accuracy check on labelled subset
    python categorize.py --input myfile.csv       # custom input
    python categorize.py --output out.csv         # custom output
    python categorize.py --breakdown              # print monthly charts
"""

import csv
import sys
import argparse
import datetime
from pathlib import Path
from collections import Counter, defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============================================================
# Category keyword rules
# Derived by reading a random sample of 200 tickets per category
# from the corpus, then confirmed against agent_notes vocabulary.
# ============================================================

CATEGORIES = {
    "Billing & Payments": [
        # Core payment signals
        "amount deducted", "money deducted", "payment deducted", "amount got deducted",
        "double charge", "double payment", "charged twice", "duplicate payment",
        "dup-payment", "dup payment", "extra charge", "overcharged",
        "payment failed", "payment not confirmed", "transaction failed",
        "invoice", "gst", "tax invoice", "proforma",
        "price adjustment", "price-adj",
        "wallet", "upi", "emi",
        "amount not refunded", "refund not received", "refund pending",
        "refund not credited", "where is my refund",
    ],
    "Delivery & Shipping": [
        "not delivered", "not received", "havent received", "haven't received",
        "order not delivered", "package not delivered", "parcel not delivered",
        "shipment not received", "item not received",
        "tracking not updating", "tracking not changed", "tracking shows",
        "out for delivery", "delivery delayed", "delay in delivery",
        "lost in transit", "lost-transit", "misrouted",
        "wrong address", "pin code", "pincode",
        "reshipped", "re-shipped", "re shipped", "re-ship",
        "waiting for delivery", "waiting for order",
        "delivery partner", "delhivery", "bluedart", "xpressbees", "ekart",
        "rto confirmed", "return to origin",
        "awb", "courier partner",
        "marked delivered", "showed delivered but",
        "5 days", "7 days", "10 days", "2 weeks", "a week", "nothing at my door",
        "crr partner", "carrier",
    ],
    "Returns & Refunds": [
        "want to return", "i want to return", "return the product",
        "return request", "initiate return", "return policy",
        "cancel my order", "order cancel", "cancellation",
        "cancel", "cancel order",
        "wrong item", "wrong product", "wrong colour", "wrong color",
        "different product", "not as described", "mismatch",
        "exchange", "replacement request",
        "pick up", "pickup", "reverse pickup",
        "return label", "return slip",
        "30 day", "15 day", "return window",
        "ordered by mistake", "ordered wrong",
        "don't ship", "dont ship", "dont want",
    ],
    "Warranty & Repair": [
        "warranty", "out of warranty", "in warranty", "under warranty",
        "warranty claim", "warranty repair", "warranty replacement",
        "service centre", "service center", "asc",
        "dead on arrival", "doa", "not working at all",
        "physically damaged", "cracked screen",
        "repair", "job card",
        "buyback", "wty buyback", "wty-buyback",
        "six month", "twelve month", "12 month", "6 month",
        "manufacturing defect",
    ],
    "Connectivity": [
        "not connecting", "wont connect", "won't connect", "not pairing", "pairing issue",
        "bluetooth", "bt pairing",
        "keeps disconnecting", "dropping connection", "connection drops",
        "auto disconnect", "auto-disconnect",
        "one earbud not connecting", "one side not connecting",
        "left earbud", "right earbud", "mono mode",
        "won't pair", "wont pair",
        "device not found", "pairing list",
        "wifi", "wi-fi",
    ],
    "Charging & Battery": [
        "not charging", "wont charge", "won't charge", "charging issue",
        "battery drain", "battery draining", "battery life", "battery dies",
        "charge twice a day", "low battery",
        "case not charging", "charging case",
        "charger not working", "gan charger", "65w", "65 w",
        "usb c", "usb-c", "cable",
        "charging port", "port issue",
        "no power", "won't turn on", "wont turn on",
        "died quickly", "drains fast",
    ],
    "App & Firmware": [
        "firmware", "firmware update",
        "vireo app", "vireo application",
        "app crash", "app not opening", "app not working",
        "equaliser", "equalizer", "eq settings",
        "touch control", "touch gesture", "tap gesture",
        "factory reset", "hard reset",
        "anc settings", "noise cancellation settings",
        "software update", "over the air",
        "companion app",
        "app store", "play store",
    ],
    "Audio Quality": [
        "sound quality", "audio quality", "poor sound", "bad sound",
        "low volume", "no sound", "one side no sound", "one earbud no sound",
        "crackling", "static", "distortion", "distorted",
        "muffled", "bass", "treble",
        "microphone", "mic not working", "mic issue", "mic quality",
        "echo", "feedback noise",
        "noise cancellation not working", "anc not working",
        "no audio", "audio cutting", "sound cutting",
    ],
    "Account & Login": [
        "login issue", "log in issue", "cant login", "can't login", "unable to login",
        "password reset", "forgot password", "reset password",
        "account locked", "account issue", "my account",
        "otp not received", "otp issue", "verification failed",
        "sign in problem", "sign up issue",
        "cannot login", "login failed",
        "registered number", "registered email",
    ],
    "Product Enquiry": [
        "which product", "suggest me", "recommendation",
        "difference between", "compare",
        "specifications", "specs",
        "in stock", "available",
        "how to use", "how do i", "how to pair",
        "compatible", "compatibility",
        "before buying", "planning to buy", "want to buy",
        "which one is better", "should i buy",
    ],
}

# Priority order (first match wins ties)
CATEGORY_PRIORITY = [
    "Billing & Payments",
    "Delivery & Shipping",
    "Returns & Refunds",
    "Warranty & Repair",
    "Connectivity",
    "Charging & Battery",
    "App & Firmware",
    "Audio Quality",
    "Account & Login",
    "Product Enquiry",
]

CATEGORY_TO_TEAM = {
    "Billing & Payments": "Billing",
    "Delivery & Shipping": "Logistics",
    "Returns & Refunds": "Returns Desk",
    "Warranty & Repair": "Escalations & Warranty",
    "Connectivity": "Chat Frontline",
    "Charging & Battery": "Chat Frontline",
    "App & Firmware": "Chat Frontline",
    "Audio Quality": "Chat Frontline",
    "Account & Login": "Chat Frontline",
    "Product Enquiry": "Chat Frontline",
    "Other": "Chat Frontline",
}


def score_text(text: str, keywords: list) -> int:
    """Count how many keywords appear in the text (case insensitive)."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def classify(customer_message: str, agent_notes: str) -> str:
    """
    Classify a ticket based on customer message and agent notes.
    Returns one of the 10 categories or 'Other'.
    """
    combined = (customer_message + " " + agent_notes).lower()

    scores = {cat: score_text(combined, kws) for cat, kws in CATEGORIES.items()}
    max_score = max(scores.values())

    if max_score == 0:
        return "Other"

    # Tie-break: use priority order
    for cat in CATEGORY_PRIORITY:
        if scores.get(cat, 0) == max_score:
            return cat

    return max(scores, key=scores.get)


def run_categorize(input_path: str, output_path: str) -> dict:
    """Read tickets CSV, add predicted_category column, write output CSV."""
    tickets = []
    fieldnames = None
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) + ['predicted_category', 'predicted_team']
        for row in reader:
            pred_cat = classify(row.get('customer_message', ''), row.get('agent_notes', ''))
            pred_team = CATEGORY_TO_TEAM.get(pred_cat, 'Chat Frontline')
            row['predicted_category'] = pred_cat
            row['predicted_team'] = pred_team
            tickets.append(row)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tickets)

    pred_cats = Counter(t['predicted_category'] for t in tickets)
    orig_cats = Counter(t['category'] for t in tickets)

    labelled = [t for t in tickets if t['category'] not in ('Other', '')]
    agreed = sum(1 for t in labelled if t['predicted_category'] == t['category'])
    agreement_rate = agreed / len(labelled) if labelled else 0

    reclassified = [t for t in tickets
                    if t['category'] == 'Other' and t['predicted_category'] != 'Other']

    return {
        'total_tickets': len(tickets),
        'predicted_category_counts': dict(pred_cats),
        'original_category_counts': dict(orig_cats),
        'agreement_rate': agreement_rate,
        'labelled_tickets': len(labelled),
        'reclassified_other': len(reclassified),
    }


def run_validation(input_path: str) -> dict:
    """Validate classifier against non-Other labelled tickets."""
    tickets = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickets.append(row)

    labelled = [t for t in tickets if t['category'] not in ('Other', '')]

    correct = 0
    errors_by_cat = defaultdict(list)
    confusion = defaultdict(Counter)

    for t in labelled:
        pred = classify(t.get('customer_message', ''), t.get('agent_notes', ''))
        actual = t['category']
        confusion[actual][pred] += 1
        if pred == actual:
            correct += 1
        else:
            errors_by_cat[actual].append({
                'ticket_id': t['ticket_id'],
                'predicted': pred,
                'message_snippet': t['customer_message'][:80]
            })

    accuracy = correct / len(labelled) if labelled else 0

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Sample size:      {len(labelled):,} tickets (all non-Other labelled tickets)")
    print(f"Correct:          {correct:,}")
    print(f"Incorrect:        {len(labelled) - correct:,}")
    print(f"Overall accuracy: {accuracy*100:.1f}%")
    print(f"Error rate:       {(1-accuracy)*100:.1f}%")

    print("\n" + "-" * 60)
    print("Per-category accuracy:")
    print(f"{'Category':<28} {'Count':>6} {'Correct':>8} {'Accuracy':>9}")
    print("-" * 60)

    for cat in CATEGORY_PRIORITY:
        if cat in confusion:
            cat_total = sum(confusion[cat].values())
            cat_correct = confusion[cat].get(cat, 0)
            cat_acc = cat_correct / cat_total if cat_total else 0
            flag = " <-- needs work" if cat_acc < 0.7 else ""
            print(f"{cat:<28} {cat_total:>6} {cat_correct:>8} {cat_acc*100:>8.1f}%{flag}")

    print("\n" + "-" * 60)
    print("Top misclassifications by category:")
    for cat in CATEGORY_PRIORITY:
        errs = errors_by_cat.get(cat, [])
        if errs:
            # Show most common confusion
            pred_counter = Counter(e['predicted'] for e in errs)
            top_confusion = pred_counter.most_common(2)
            print(f"  {cat}: {len(errs)} errors -> most confused with {top_confusion}")

    return {
        'accuracy': accuracy,
        'sample_size': len(labelled),
        'correct': correct,
        'per_category': {cat: {'total': sum(confusion[cat].values()),
                               'correct': confusion[cat].get(cat, 0)}
                         for cat in confusion}
    }


def run_monthly_breakdown(input_path: str) -> None:
    """Print monthly breakdown by category and by team."""
    tickets = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickets.append(row)

    months = sorted(set(t['created_at'][:7] for t in tickets if t['created_at']))
    months = [m for m in months if m >= '2025-01']

    all_cats = list(CATEGORY_PRIORITY) + ['Other']
    all_teams = ['Chat Frontline', 'Email Frontline', 'Voice Frontline',
                 'Billing', 'Logistics', 'Returns Desk', 'Escalations & Warranty']

    cat_key = 'predicted_category' if 'predicted_category' in tickets[0] else 'category'
    team_key = 'predicted_team' if 'predicted_team' in tickets[0] else 'assigned_team'

    monthly_cat = defaultdict(Counter)
    monthly_team = defaultdict(Counter)
    for t in tickets:
        m = t['created_at'][:7]
        if m >= '2025-01':
            monthly_cat[m][t[cat_key]] += 1
            monthly_team[m][t[team_key]] += 1

    print("\n" + "=" * 60)
    print("MONTHLY BREAKDOWN BY CATEGORY (Jan 2025 to Jun 2026)")
    print("=" * 60)
    # Abbrev headers
    abbrev = {
        'Billing & Payments': 'Billing',
        'Delivery & Shipping': 'Delivery',
        'Returns & Refunds': 'Returns',
        'Warranty & Repair': 'Warranty',
        'Connectivity': 'Connect',
        'Charging & Battery': 'Charg',
        'App & Firmware': 'App/FW',
        'Audio Quality': 'Audio',
        'Account & Login': 'Account',
        'Product Enquiry': 'Enquiry',
        'Other': 'Other',
    }
    print(f"{'Month':<9}" + "".join(f"{abbrev.get(c,c[:7]):>9}" for c in all_cats))
    for m in months:
        row = f"{m:<9}" + "".join(f"{monthly_cat[m].get(c,0):>9}" for c in all_cats)
        print(row)

    print("\n" + "=" * 60)
    print("MONTHLY BREAKDOWN BY TEAM")
    print("=" * 60)
    t_abbrev = {
        'Chat Frontline': 'Chat FL',
        'Email Frontline': 'Email FL',
        'Voice Frontline': 'Voice FL',
        'Billing': 'Billing',
        'Logistics': 'Logistics',
        'Returns Desk': 'Returns',
        'Escalations & Warranty': 'Esc&War',
    }
    print(f"{'Month':<9}" + "".join(f"{t_abbrev.get(t,t[:8]):>10}" for t in all_teams))
    for m in months:
        row = f"{m:<9}" + "".join(f"{monthly_team[m].get(t,0):>10}" for t in all_teams)
        print(row)

    team_totals = Counter()
    for mc in monthly_team.values():
        for team, cnt in mc.items():
            team_totals[team] += cnt

    top_team = team_totals.most_common(1)[0]
    print("\n" + "=" * 60)
    print("HEADCOUNT RECOMMENDATION")
    print(f"Highest volume team: {top_team[0]} ({top_team[1]:,} tickets Jan 2025-Jun 2026)")
    print(f"  --> The next 2 hires should go to: {top_team[0]}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Vireo Audio Ticket Categoriser')
    parser.add_argument('--input',
                        default=r'd:\Vireo_Audio_Support_Ticket_SetE\tickets.csv')
    parser.add_argument('--output',
                        default=r'd:\Vireo_Audio_Support_Ticket_SetE\vireo_tool\tickets_categorised.csv')
    parser.add_argument('--validate', action='store_true',
                        help='Run accuracy check against labelled tickets')
    parser.add_argument('--breakdown', action='store_true',
                        help='Print monthly category/team breakdown')
    args = parser.parse_args()

    print("Vireo Audio Ticket Categoriser")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print(f"Time:   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.validate:
        run_validation(args.input)
        return

    if args.breakdown:
        run_monthly_breakdown(args.input)
        return

    print("\nCategorising tickets...")
    stats = run_categorize(args.input, args.output)

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total tickets processed:      {stats['total_tickets']:,}")
    print(f"Agreement with existing tags: {stats['agreement_rate']*100:.1f}%"
          f"  (on {stats['labelled_tickets']:,} non-Other labelled tickets)")
    print(f"'Other' tickets re-classified: {stats['reclassified_other']:,}")

    print("\nPredicted category distribution:")
    for cat, count in sorted(stats['predicted_category_counts'].items(), key=lambda x: -x[1]):
        pct = count / stats['total_tickets'] * 100
        print(f"  {cat:<28} {count:>5}  ({pct:.1f}%)")

    run_monthly_breakdown(args.output)
    print(f"\nOutput written to: {args.output}")


if __name__ == '__main__':
    main()
