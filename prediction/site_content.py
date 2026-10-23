"""Text for the FAQ page and for the site search (kept in one place so both stay in sync)."""

FAQ = [
    ("What does this website do?",
     "You enter 13 health values and a calibrated Machine Learning model estimates the probability of heart disease, "
     "shows a LOW / MODERATE / HIGH level and explains which inputs raised or lowered the estimate."),
    ("Is the result a medical diagnosis?",
     "No. It is a screening aid built for learning. It cannot replace tests or advice from a qualified doctor."),
    ("What is the Trust check?",
     "Next to every estimate the system tells you how far that particular number can be trusted. It looks at three signals: "
     "unusual inputs compared with the training data, disagreement between the cross-validation versions of the model, "
     "and whether the probability sits close to a risk-level limit. If trust is Low, talk to a doctor."),
    ("What is the What-if simulator?",
     "Move the blood pressure, cholesterol or blood sugar controls and the model recalculates the estimate instantly. "
     "It shows how the MODEL reacts, which is a statistical association and not proof that changing a value will change your health."),
    ("Which dataset was used?",
     "The UCI Heart Disease (Cleveland) dataset with 13 attributes. If a yellow Demo mode banner is visible, "
     "the model was trained on synthetic demo data and its numbers are not meaningful."),
    ("Who can see my predictions?",
     "Only you. If you keep the sharing option on, registered doctors can also open your history, and every doctor view is "
     "recorded in an access log that you can read on your account page. You can switch sharing off at any time."),
    ("Can I delete my data?",
     "Yes. You can delete single predictions from your history, or delete your whole account (with all predictions) from the account page."),
    ("How do the LOW, MODERATE and HIGH levels work?",
     "Below 30 percent is LOW, 30 to below 60 percent is MODERATE and 60 percent or more is HIGH. These limits were chosen for this project; they are not clinical thresholds."),
    ("Can other programs use the model?",
     "Yes. Create a personal API token on your account page and call the JSON API (predict, what-if and history). The token is shown once and only its hash is stored."),
]

# Pages that the site search can find: (title, url name, description, needs login)
PAGES = [
    ("Home", "home", "Overview of the heart disease risk prediction system", False),
    ("New prediction", "predict", "Enter 13 health values and get an estimated probability and risk level", True),
    ("Batch CSV prediction", "batch", "Upload a CSV file to predict for many patients at once", True),
    ("Prediction history", "history", "Your earlier predictions with a risk trend chart", True),
    ("Model details", "model", "Model comparison, accuracy, recall, ROC-AUC, calibration, external validation", False),
    ("My account", "profile", "Settings, sharing with doctors, API token, access log, delete account", True),
    ("FAQ", "faq", "Frequently asked questions", False),
    ("Contact", "contact", "Send a message to the project team", False),
    ("Privacy and cookies", "privacy", "What data is stored, which cookies are used", False),
]
