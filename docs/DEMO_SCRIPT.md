# PlastiTrack: 3-minute demo video script

Target: 2:50 so there is buffer. About 130 spoken words per minute. **[Screen]** is what's on screen;
the rest is the voice-over. Pre-load everything before recording: SSH tunnel open, container running,
Granite tips already generated once (the tips are cached, so the button returns instantly on camera).

---

### 0:00–0:25 · Problem + supporting data
**[Screen]** Title card "PlastiTrack", then the EDA chart *Plastic level by category* (`reports/figures/eda_level_by_category.png`).

> Every online order arrives wrapped in plastic, but nobody can see how much. We analyzed 200,000 products from
> Open Food Facts and its sister databases on IBM LinuxONE. Two out of three products with known packaging
> contain plastic, and the worst categories are personal care, meat, dairy and household goods, exactly the
> things we re-order online every week.

### 0:25–0:50 · Solution
**[Screen]** Architecture diagram from the README.

> PlastiTrack reads your order-confirmation emails, strips out your personal details, and keeps only the line items.
> A machine-learning model predicts each item's plastic level and plastic type from its product title. We convert
> that into grams, find the plastic-heavy items you keep buying, and a generative model suggests a personalized
> lower-plastic swap. And your shopping data never touches a third-party AI API.

### 0:50–1:25 · IBM Z / LinuxONE tech stack
**[Screen]** Quick cuts: terminal `check_env.py` (s390x, big-endian) → `train.log` metrics → confusion matrix →
`container.sh status` (s390x, read-only, cap-drop ALL) → `llama_print_system_info` line.

> Everything runs on IBM LinuxONE, on the s390x big-endian architecture. We processed the 1.3 GB dataset in
> 90 seconds and trained scikit-learn and XGBoost models right on the machine. Logistic regression won with
> 61% accuracy on four plastic levels. The generative part is IBM Granite 4.0, a big-endian GGUF model running
> through llama.cpp on the LinuxONE CPU. The app ships as a hardened Docker container: non-root, read-only
> filesystem, all Linux capabilities dropped, and reachable only through an encrypted SSH tunnel.

### 1:25–2:30 · Live demo
**[Screen]** Browser at `http://localhost:8501`.

1. Click **Load 20 demo order emails**. *"Twenty order emails from three stores, analyzed in a fraction of a second on LinuxONE."*
2. Point to KPIs. *"About 8 kilograms of plastic in three months, 2.7 kg a month, and 214 personal details removed before anything was kept."*
3. Hover the **monthly chart** and **category** bars. *"Household and beverages dominate; here's the split by store and plastic type."*
4. **Alerts & swaps** tab. *"Bottled water, bought six times: almost 3 kg of PET. Granite, running locally, suggests a filter pitcher and a reusable bottle, saving about 2.7 kg."* Show one ✨ tip and its "Generated on LinuxONE" tag.
5. **Line items** tab. *"Every prediction shows its confidence and where it came from: the ML model or an explicit packaging word in the title."*
6. **Privacy view**, expand one email. *"This is all the system ever saw: names, addresses, phone numbers, order and card numbers are already redacted."*

### 2:30–2:50 · Impact
**[Screen]** Alerts summary line ("Switching could avoid about X kg") and then the title card.

> If one household follows these swaps, it avoids several kilograms of plastic a year. Retailers could offer
> it as a privacy-safe feature, and because it runs on LinuxONE, the AI and the data stay on secure, efficient
> infrastructure the customer can trust. PlastiTrack: see your plastic, cut your plastic, keep your privacy.

---

**Recording tips:** 1440×900 browser window, 110% zoom; hide bookmarks; close other tabs. Record the terminal
segments first and the live demo second, then join them.
