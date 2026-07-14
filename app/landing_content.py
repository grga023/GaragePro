"""Marketing copy for the public landing page (Serbian + English).

Kept out of the route so the template stays clean and the two languages live
side by side for easy editing.  ``LANDING["sr"]`` / ``LANDING["en"]`` share the
exact same keys, so the template is language-agnostic.
"""

LANDING = {
    "sr": {
        "lang_code": "sr",
        "dir": "ltr",
        "meta_title": "GaragePro — Softver za auto servise | vozila, servisi, profit",
        "meta_description": (
            "GaragePro je jednostavan softver za vođenje auto servisa: evidencija "
            "vozila i servisa, delovi i profit, automatski izveštaji na e-mail. "
            "Radi na telefonu, tabletu i računaru."
        ),
        "meta_keywords": (
            "softver za auto servis, program za auto servis, vođenje servisa, "
            "evidencija vozila, auto mehaničar, vulkanizer, profit servisa, GaragePro"
        ),
        "og_title": "GaragePro — softver za moderne auto servise",
        "og_description": "Vozila, servisi, delovi i profit na jednom mestu. Radi na svakom uređaju.",
        "switch_label": "EN",
        "switch_href": "/en",
        "nav": {
            "features": "Mogućnosti",
            "how": "Kako radi",
            "faq": "Pitanja",
            "demo": "Zatraži demo",
            "login": "Prijava",
        },
        "hero": {
            "badge": "Napravljeno za auto servise",
            "title_1": "Vodite svoj auto servis —",
            "title_2": "bez papira i haosa",
            "subtitle": (
                "GaragePro objedinjuje vozila, servise, delove, radnike i profit "
                "na jednom mestu. Radi na telefonu, tabletu i računaru, a izveštaji "
                "stižu automatski na e-mail."
            ),
            "cta_primary": "Zatraži besplatan demo",
            "cta_secondary": "Prijava",
        },
        "stats": [
            {"value": "5 min", "label": "do prvog servisa"},
            {"value": "0", "label": "sveska i papira"},
            {"value": "24/7", "label": "sa bilo kog uređaja"},
            {"value": "100%", "label": "vaši podaci, vaš server"},
        ],
        "features_title": "Sve što servisu zaista treba",
        "features_subtitle": "Od prijema vozila do profita na kraju meseca.",
        "features": [
            {"icon": "🚗", "title": "Vozila i klijenti",
             "desc": "Kompletna istorija svakog vozila — kilometraža, delovi, radovi i troškovi na jednom mestu."},
            {"icon": "🔧", "title": "Servisi i radovi",
             "desc": "Popravke, vulkanizerski radovi i mali servis. Brzo dodavanje delova i cene rada."},
            {"icon": "💰", "title": "Profit u realnom vremenu",
             "desc": "Nabavna i prodajna cena delova, marža i zarada — po servisu, radniku i periodu."},
            {"icon": "📊", "title": "Izveštaji i žurnali",
             "desc": "Dnevni, nedeljni i mesečni izveštaji automatski na e-mail. Bez ručnog računanja."},
            {"icon": "🧾", "title": "Skeniranje faktura",
             "desc": "Slikajte fakturu — GaragePro prepozna delove i cene i ubaci ih u servis (OCR)."},
            {"icon": "👥", "title": "Više radnika i radnji",
             "desc": "Uloge za vlasnika i radnike, više servisa pod jednim nalogom, potpuna kontrola."},
            {"icon": "📱", "title": "Radi kao aplikacija",
             "desc": "Instalirajte na telefon (PWA), radi i bez interneta. Bez app store-a."},
            {"icon": "🔒", "title": "Bezbedno i vaše",
             "desc": "Podaci na vašem serveru, automatske rezervne kopije i prijava lozinkom."},
        ],
        "how_title": "Kako radi",
        "how_subtitle": "Tri koraka do potpune kontrole nad servisom.",
        "how_steps": [
            {"n": "1", "title": "Dodaj vozilo", "desc": "Unesite tablice — ostalo GaragePro pamti."},
            {"n": "2", "title": "Zabeleži servis", "desc": "Dodajte delove i rad; cena i profit se računaju sami."},
            {"n": "3", "title": "Prati zaradu", "desc": "Izveštaji i profit stižu na e-mail — vi se bavite servisom."},
        ],
        "preview": {
            "title": "Kontrolna tabla",
            "today": "Danas", "month": "Ovaj mesec", "profit": "Profit",
            "services": "Servisa", "revenue": "Promet", "cars": "Vozila",
            "row1": "BMW 320d — zamena pločica",
            "row2": "VW Golf 7 — mali servis",
            "row3": "Audi A4 — vulkanizerski radovi",
        },
        "why_title": "Zašto baš GaragePro",
        "why": [
            {"icon": "⚡", "title": "Brzo i jednostavno",
             "desc": "Bez obuke. Ako znate da koristite telefon, znate i GaragePro."},
            {"icon": "🌐", "title": "Na srpskom i engleskom",
             "desc": "Interfejs i podrška prilagođeni domaćim servisima."},
            {"icon": "🏠", "title": "Vaš server, vaši podaci",
             "desc": "Nema zaključavanja. Podaci ostaju kod vas, uz automatske kopije."},
        ],
        "testimonial": {
            "quote": "„Konačno tačno znam koliko zarađujem po svakom servisu — i ko od radnika koliko donosi.“",
            "author": "Vlasnik auto servisa",
        },
        "faq_title": "Česta pitanja",
        "faq": [
            {"q": "Da li radi na telefonu?",
             "a": "Da. GaragePro se instalira kao aplikacija i radi na telefonu, tabletu i računaru — čak i bez interneta."},
            {"q": "Gde se čuvaju podaci?",
             "a": "Na vašem serveru. Vi ste vlasnik podataka, a mi radimo automatske rezervne kopije."},
            {"q": "Mogu li da vidim profit?",
             "a": "Da — po servisu, radniku, danu i mesecu. Nabavna i prodajna cena delova su razdvojene."},
            {"q": "Koliko traje uvođenje?",
             "a": "Nekoliko minuta. Napravite nalog, dodate radnju i odmah počnete."},
        ],
        "cta": {
            "title": "Spremni da digitalizujete servis?",
            "subtitle": "Zatražite besplatan demo i vidite GaragePro na delu.",
            "button": "Zatraži demo",
        },
        "footer": {
            "tagline": "Softver za moderne auto servise.",
            "contact": "Kontakt",
            "rights": "Sva prava zadržana.",
        },
    },
    "en": {
        "lang_code": "en",
        "dir": "ltr",
        "meta_title": "GaragePro — Auto repair shop software | cars, jobs, profit",
        "meta_description": (
            "GaragePro is simple software to run your auto repair shop: track cars "
            "and services, parts and profit, automatic e-mail reports. Works on "
            "phone, tablet and desktop."
        ),
        "meta_keywords": (
            "auto repair shop software, garage management software, car service app, "
            "vehicle history, mechanic software, tyre shop, shop profit, GaragePro"
        ),
        "og_title": "GaragePro — software for modern auto repair shops",
        "og_description": "Cars, services, parts and profit in one place. Works on every device.",
        "switch_label": "SR",
        "switch_href": "/",
        "nav": {
            "features": "Features",
            "how": "How it works",
            "faq": "FAQ",
            "demo": "Request a demo",
            "login": "Sign in",
        },
        "hero": {
            "badge": "Built for auto repair shops",
            "title_1": "Run your repair shop —",
            "title_2": "without paper and chaos",
            "subtitle": (
                "GaragePro brings cars, services, parts, staff and profit together "
                "in one place. It works on phone, tablet and desktop, and reports "
                "land in your inbox automatically."
            ),
            "cta_primary": "Get a free demo",
            "cta_secondary": "Sign in",
        },
        "stats": [
            {"value": "5 min", "label": "to your first job"},
            {"value": "0", "label": "notebooks & paper"},
            {"value": "24/7", "label": "from any device"},
            {"value": "100%", "label": "your data, your server"},
        ],
        "features_title": "Everything a shop actually needs",
        "features_subtitle": "From car intake to end-of-month profit.",
        "features": [
            {"icon": "🚗", "title": "Cars & customers",
             "desc": "Full history for every vehicle — mileage, parts, jobs and costs in one place."},
            {"icon": "🔧", "title": "Services & labour",
             "desc": "Repairs, tyre work and minor service. Add parts and labour prices in seconds."},
            {"icon": "💰", "title": "Real-time profit",
             "desc": "Cost vs. sale price of parts, margin and earnings — per job, worker and period."},
            {"icon": "📊", "title": "Reports & journals",
             "desc": "Daily, weekly and monthly reports e-mailed automatically. No manual maths."},
            {"icon": "🧾", "title": "Invoice scanning",
             "desc": "Snap an invoice — GaragePro reads the parts and prices and adds them (OCR)."},
            {"icon": "👥", "title": "Multiple staff & shops",
             "desc": "Owner and worker roles, several shops under one account, full control."},
            {"icon": "📱", "title": "Works like an app",
             "desc": "Install on your phone (PWA), works offline too. No app store needed."},
            {"icon": "🔒", "title": "Secure & yours",
             "desc": "Data on your own server, automatic backups and password sign-in."},
        ],
        "how_title": "How it works",
        "how_subtitle": "Three steps to full control of your shop.",
        "how_steps": [
            {"n": "1", "title": "Add a car", "desc": "Type the plate — GaragePro remembers the rest."},
            {"n": "2", "title": "Log the service", "desc": "Add parts and labour; price and profit are calculated for you."},
            {"n": "3", "title": "Track earnings", "desc": "Reports and profit land in your inbox — you focus on the cars."},
        ],
        "preview": {
            "title": "Dashboard",
            "today": "Today", "month": "This month", "profit": "Profit",
            "services": "Services", "revenue": "Revenue", "cars": "Cars",
            "row1": "BMW 320d — brake pads",
            "row2": "VW Golf 7 — minor service",
            "row3": "Audi A4 — tyre work",
        },
        "why_title": "Why GaragePro",
        "why": [
            {"icon": "⚡", "title": "Fast & simple",
             "desc": "No training needed. If you can use a phone, you can use GaragePro."},
            {"icon": "🌐", "title": "Serbian & English",
             "desc": "Interface and support tuned for local repair shops."},
            {"icon": "🏠", "title": "Your server, your data",
             "desc": "No lock-in. Your data stays with you, with automatic backups."},
        ],
        "testimonial": {
            "quote": "“I finally know exactly how much I earn on every job — and which worker brings in what.”",
            "author": "Auto repair shop owner",
        },
        "faq_title": "Frequently asked questions",
        "faq": [
            {"q": "Does it work on a phone?",
             "a": "Yes. GaragePro installs like an app and works on phone, tablet and desktop — even offline."},
            {"q": "Where is the data stored?",
             "a": "On your own server. You own the data, and we run automatic backups."},
            {"q": "Can I see profit?",
             "a": "Yes — per job, worker, day and month. Part cost and sale price are kept separate."},
            {"q": "How long is setup?",
             "a": "A few minutes. Create an account, add your shop and start right away."},
        ],
        "cta": {
            "title": "Ready to digitise your shop?",
            "subtitle": "Request a free demo and see GaragePro in action.",
            "button": "Request a demo",
        },
        "footer": {
            "tagline": "Software for modern auto repair shops.",
            "contact": "Contact",
            "rights": "All rights reserved.",
        },
    },
}
