# PlastiTrack: 3-minute demo video script

Target: 2:50 so there is buffer. About 130 spoken words per minute. **[Screen]** is what's on screen;
the rest is the voice-over.

**Before recording:** SSH tunnel open, container running with HTTPS, open `https://localhost:8501` once and
accept the self-signed certificate. Click "Personalize tips" once beforehand: tips are cached, so on camera they
appear instantly. Load "+ 1 free-text email" once beforehand too (its result appears in ~20 s).

---

### 0:00–0:20 · Problem + supporting data
**[Screen]** Title card "PlastiTrack", then `reports/figures/eda_level_by_category.png`.

> Every online order arrives wrapped in plastic, but nobody can see how much. We analyzed 200,000 products from
> Open Food Facts and its sister databases on IBM LinuxONE. Two out of three contain plastic, and the worst
> categories, personal care, meat, dairy, household, are exactly what we re-order online every week.

### 0:20–0:40 · Solution
**[Screen]** Architecture diagram (README).

> PlastiTrack reads your order emails, strips your personal details first, and keeps only line items. A
> machine-learning model predicts each item's plastic level and type, we convert that to grams, and IBM Granite,
> running locally, suggests personalized swaps. Your shopping data never touches a third-party AI API.

### 0:40–1:15 · IBM Z / LinuxONE tech stack
**[Screen]** Quick cuts: `check_env.py` (s390x, big-endian) → `train.log` metrics + confusion matrix →
`benchmark.py` output → `crypto_benchmark.sh` table → `container.sh status`.

> Everything runs on IBM LinuxONE, big-endian s390x. We trained scikit-learn and XGBoost models on the machine;
> logistic regression won with 61% accuracy on four plastic levels. It scores over 7,000 items per second, about
> 2 milliseconds each. For generative AI we converted IBM's Granite 4.0 instruct model to big-endian and run it
> with llama.cpp. Security uses the hardware: HTTPS with TLS 1.3, where AES-GCM runs on the IBM Z CPACF crypto
> unit, 108 times faster than software. And the app ships as a hardened container: non-root, read-only,
> all capabilities dropped.

### 1:15–2:30 · Live demo
**[Screen]** Browser at `https://localhost:8501`. Point at the 🔐 TLS badge.

1. **Load 20 demo order emails.** *"Twenty orders from three stores, analyzed in a fraction of a second."* KPIs: about 8 kg in three months, 214 personal details removed.
2. **Dashboard:** hover the monthly chart and category bars.
3. **Alerts & swaps:** *"Bottled water, six orders, almost 3 kilograms of PET."* Show the ✨ Granite tip and its "number-checked" tag. Untick/tick swaps in the **impact panel**: *"Adopting five swaps cuts this household's plastic by 59%, about 2,000 bottles a year, and 196 tonnes if 10,000 households did it."*
4. **Line items:** *"Every prediction is explained. Milk is medium plastic because of 'whole milk' and 'gal'."*
5. **+ 1 free-text email:** *"This email has no item list at all. The rules fail, so Granite reads the redacted text and extracts the items as JSON, checked against the email so it can't hallucinate."* Show the ✨ rows.
6. **Privacy view:** *"This is all the system ever saw, with names, addresses, phone and card numbers already redacted."*

### 2:30–2:50 · Impact
**[Screen]** Impact panel, then the title card.

> One household can avoid kilograms of plastic a year just by seeing it. Retailers could offer this as a
> privacy-safe feature, and on LinuxONE the AI and the data stay on secure, efficient infrastructure.
> PlastiTrack: see your plastic, cut your plastic, keep your privacy.

---

**Recording tips:** 1440×900 browser window, 110% zoom; hide bookmarks; close other tabs. Record the terminal
segments first and the live demo second, then join them.
