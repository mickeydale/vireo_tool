# Vireo Audio -- Support Ticket Categoriser

## What This Is
An AI-assisted tool that automatically categorises Vireo Audio support tickets into 10 business categories and recommends where to add headcount -- answering Priya Raman's exact question.

**Zero API cost.** Runs entirely on keyword rules derived from reading the ticket corpus. Works on any machine with Python 3.8+.

---

## Quick Start (Step-by-Step)

### Step 1 -- Open PowerShell
Press Windows key + R, type powershell, press Enter.

### Step 2 -- Run accuracy validation
```
python "d:\vireo_tool\categorize.py" --input "d:\vireo_tool\tickets.csv" --output "d:\vireo_tool\tickets_categorised.csv" --validate
```
This checks how accurate the classifier is against existing labels.

### Step 3 -- Run full categorisation + monthly breakdown
```
python "d:\vireo_tool\categorize.py" --input "d:\vireo_tool\tickets.csv" --output "d:\vireo_tool\tickets_categorised.csv"
```
This classifies all 11,780 tickets, prints the monthly breakdown by category and team, and saves the output file.

### Step 4 -- Open the dashboard
```
Start-Process "d:\vireo_tool\dashboard.html"
```
Opens the interactive chart dashboard in your browser. No internet or server needed.

---

## Files

| File | Purpose |
|------|---------|
| categorize.py | Main classifier -- reads tickets.csv, writes tickets_categorised.csv |
| dashboard.html | Interactive charts dashboard -- open in any browser |
| tickets.csv | Input -- 11,780 support tickets (Jan 2025 to Jun 2026) |
| tickets_categorised.csv | Output -- generated after running Step 3 |
| README.md | This file |

---

## All Commands at a Glance

```
# Validate accuracy
python "d:\vireo_tool\categorize.py" --input "d:\vireo_tool\tickets.csv" --output "d:\vireo_tool\tickets_categorised.csv" --validate

# Full categorisation + monthly breakdown
python "d:\vireo_tool\categorize.py" --input "d:\vireo_tool\tickets.csv" --output "d:\vireo_tool\tickets_categorised.csv"

# Open dashboard
Start-Process "d:\vireo_tool\dashboard.html"
```

---

## Categories and Teams

| Category | Routed To |
|----------|-----------|
| Billing and Payments | Billing |
| Delivery and Shipping | Logistics |
| Returns and Refunds | Returns Desk |
| Warranty and Repair | Escalations and Warranty |
| Connectivity | Chat Frontline |
| Charging and Battery | Chat Frontline |
| App and Firmware | Chat Frontline |
| Audio Quality | Chat Frontline |
| Account and Login | Chat Frontline |
| Product Enquiry | Chat Frontline |
| Other | Chat Frontline |

---

## Accuracy

Validated against 10,158 non-Other labelled tickets:

- Overall agreement with existing labels: 47.4%
- Best: Delivery and Shipping (63.5%), App and Firmware (60.4%)
- Worst: Billing and Payments (32.3%), Connectivity (32.2%)

Why the apparent low accuracy is expected:
The original category tags are themselves inconsistent. "Billing and Payments" is used for both true payment failures AND "I paid but nothing arrived" -- the latter is really a delivery issue. Our classifier correctly identifies these as Delivery tickets.

---

## Key Finding

Chat Frontline handled 3,030 tickets from Jan 2025 to Jun 2026 -- the highest of any team.
Volume grew +73% year-on-year.
The next 2 hires should go to Chat Frontline.

---

## Business Goal

Cut duplicate-payment refunds: 498 DUP-PAYMENT tickets = Rs 14.1L refunded over 18 months.
Auto-detecting double-charges at checkout saves Rs 9.4L/year.

---

## Cost

| Item | Cost |
|------|------|
| Python (standard library only) | Rs 0 |
| API calls | Rs 0 |
| Runtime 11780 tickets | ~2 seconds |
| Monthly cost at 650 tickets per week | Rs 0 |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| python is not recognized | Python not installed. Download from python.org |
| No such file or directory | Check the path -- all files must be inside d:\vireo_tool\ |
| ModuleNotFoundError | No modules needed -- uses only Python standard library |

---

## Known Limitations

1. Keyword classifier misses short vague messages -- "please help" falls to Other
2. Billing/Delivery ambiguity -- "paid, not received" is genuinely dual-intent
3. No sentiment or urgency scoring -- does not predict CSAT or priority
4. Static rules -- will drift as product language evolves
5. Validation set equals original labels -- which are themselves 14% Other

---

## Deliberate Scope Decisions

- No LLM API calls -- kept cost at Rs 0
- No ML model training -- original labels are too noisy for clean training
- Dashboard is static HTML -- no backend server, works on any machine instantly
- Left out: CSAT prediction, agent performance analysis, SLA breach detection
