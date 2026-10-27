<div align="center">

# ❤️ CardioNova Health

### Uncertainty-Aware Heart Disease Risk Estimation

**An educational healthcare machine learning application built with Django and scikit-learn.**

Explore machine learning predictions, model evaluation, interpretable outputs, and responsible AI practices through a web-based application.

<br>

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2%2B-092E20?style=for-the-badge&logo=django&logoColor=white)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Status](https://img.shields.io/badge/Project-Educational-7C3AED?style=for-the-badge)

<br>

[Features](#-key-features) •
[Architecture](#-system-architecture) •
[Machine Learning](#-machine-learning-pipeline) •
[Results](#-model-performance) •
[Installation](#-installation-and-setup) •
[Testing](#-testing-and-quality-checks)

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [System Architecture](#-system-architecture)
- [Machine Learning Pipeline](#-machine-learning-pipeline)
- [Dataset](#-dataset)
- [Model Performance](#-model-performance)
- [Prediction Interpretability](#-prediction-interpretability)
- [Project Structure](#-project-structure)
- [Installation and Setup](#-installation-and-setup)
- [Training the Model](#-training-the-model)
- [Testing and Quality Checks](#-testing-and-quality-checks)
- [Security Considerations](#-security-considerations)
- [Limitations](#-limitations)
- [Future Improvements](#-future-improvements)
- [Learning Outcomes](#-learning-outcomes)
- [Academic Relevance](#-academic-relevance)
- [Author](#-author)
- [License](#-license)
- [Medical Disclaimer](#-medical-disclaimer)

---

## 🔍 Overview

**CardioNova Health** is a web-based machine learning project that demonstrates how a trained classification model can be integrated into a Django application.

The project combines a machine learning pipeline with a web interface to demonstrate the complete workflow, from data preparation and model evaluation to prediction delivery and result presentation.

### Project Objectives

- Build a reproducible machine learning training workflow.
- Compare classification algorithms using cross-validation.
- Integrate a trained model into a Django web application.
- Present model outputs through an accessible interface.
- Explore prediction explanations and heuristic uncertainty indicators.
- Apply authentication, input validation, testing, and security practices.
- Demonstrate responsible communication of machine learning limitations.

### Application Workflow

1. A user enters the requested input features.
2. The application validates the submitted values.
3. The trained model processes the input using the required preprocessing.
4. The application generates a model prediction.
5. The result and applicable explanatory information are presented.
6. Authenticated users can access supported history and reporting features.

> **Important:** This project is intended for educational and portfolio use. Its predictions are experimental model outputs, not clinically validated estimates of an individual's actual heart disease risk.

---

## ✨ Key Features

The following summarizes the intended project capabilities. Each feature should be verified against the current implementation before being treated as production-ready.

### 🧠 Machine Learning

- Data cleaning and preprocessing.
- Multiple classifier comparison.
- Stratified train-test splitting.
- Cross-validation-based model selection.
- Evaluation using classification and probability metrics.
- Saved model artifacts for application inference.
- Feature importance and perturbation-based explanations.

### 🌐 Web Application

- Django-powered web interface.
- User registration and authentication.
- Prediction form and results page.
- Prediction history and visualizations.
- Batch prediction through CSV uploads.
- PDF report generation.
- Dark mode and responsive presentation.
- FAQ and contact pages.
- Print-friendly styles.

### 🔎 Prediction Interpretation

- Input-range checks against training-data ranges.
- Model disagreement indicators.
- Signals for predictions near configured risk-band boundaries.
- Input consistency checks.
- Feature perturbation explanations.
- Fixed-rule, plain-language summaries.

These indicators are application-level heuristics. They do not establish clinical uncertainty or guarantee that a prediction is correct.

### 👥 User and Access Management

- Patient and doctor roles, where implemented.
- Opt-in doctor access to supported records.
- Access logging for applicable actions.
- Password-reset workflows.
- Account deletion with password confirmation.

### 🔌 API and Integration

- `POST /api/predict/`
- `POST /api/whatif/`
- `GET /api/history/`

The exact methods, authentication requirements, response formats, and permissions should be confirmed in the current URL configuration and API implementation.

### 🔐 Security and Deployment

- Server-side input validation.
- Authentication and access-control checks.
- API bearer tokens stored as hashes, where implemented.
- Request and upload-size controls.
- Rate-limiting mechanisms.
- Security headers and Content Security Policy.
- CSV formula-injection protections.
- Docker-based development or deployment configuration.
- PostgreSQL configuration support.
- Render deployment blueprint.
- GitHub Actions workflow.

**Security note:** Listing a security feature does not establish that the application is secure or production-ready. Review the implementation and deployment configuration before making that claim.

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Web Framework | Django |
| Machine Learning | scikit-learn |
| Data Processing | pandas, NumPy |
| Frontend | HTML, CSS, JavaScript |
| Data Visualization | Application charts and visualizations |
| Testing | Django test framework |
| Database | Django-supported database configuration |
| Deployment | Docker, Docker Compose, Render configuration |
| Automation | GitHub Actions |
| Version Control | Git and GitHub |

**Compatibility note:** The saved model artifacts were generated with scikit-learn 1.8.0. Use the project's pinned dependency versions or retrain the model when changing incompatible library versions.

---

## 🏗️ System Architecture

### Web Application Architecture

```text
┌──────────────────────────────┐
│         User / Browser       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        Django Web Layer      │
│                              │
│ URLs • Views • Forms • Auth  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│    Validation and Rules      │
│                              │
│ Input checks • Permissions   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Machine Learning        │
│                              │
│ Preprocessing • Saved Model  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Prediction Services     │
│                              │
│ Results • Explanations       │
│ History • Reports • API      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Result Presentation    │
└──────────────────────────────┘
```

### Model Training Architecture

```text
Dataset
   │
   ▼
Data Cleaning and Validation
   │
   ▼
Stratified Train-Test Split
   │
   ▼
Preprocessing Pipeline
   │
   ▼
Cross-Validation and Model Search
   │
   ▼
Classifier Comparison
   │
   ▼
Held-Out Evaluation
   │
   ▼
Saved Model Artifacts and Reports
   │
   ▼
Django Application Inference
```

The training workflow and web inference workflow serve different purposes. Training evaluates and creates model artifacts, while the web application loads those artifacts to generate predictions.

---

## 🤖 Machine Learning Pipeline

The training workflow is designed to support model comparison and reproducible evaluation.

### Workflow

1. Load the heart disease dataset.
2. Remove duplicate records and handle records with missing required values.
3. Convert the original target into a binary classification target.
4. Create a stratified training and held-out test split.
5. Fit preprocessing steps within the machine learning pipeline.
6. Compare six classifiers using `GridSearchCV`.
7. Use five-fold stratified cross-validation with ROC-AUC as the search metric.
8. Compare soft voting and stacking approaches.
9. Select a model using training cross-validation results.
10. Evaluate the selected model on the held-out test set.
11. Generate evaluation reports and supporting artifacts.
12. Save the trained model and associated metadata.

### Preprocessing

The configured workflow uses:

- Median imputation.
- Standard scaling.
- Pipeline-based preprocessing to help prevent data leakage.
- Stratified data splitting.
- Cross-validation for model comparison.

Preprocessing transformations must be fitted on training data rather than the complete dataset before splitting.

### Evaluation Metrics

| Metric | Purpose |
|---|---|
| Accuracy | Overall proportion of correct predictions |
| Precision | Proportion of positive predictions that are correct |
| Recall | Proportion of actual positive cases identified |
| F1-score | Harmonic mean of precision and recall |
| ROC-AUC | Ability to rank positive cases above negative cases |
| Brier Score | Measures the squared error of predicted probabilities |

No single metric establishes clinical usefulness. Interpretation depends on the dataset, decision threshold, class distribution, intended application, and consequences of errors.

---

## 📊 Dataset

The project uses the historical **UCI Cleveland Heart Disease dataset**.

| Attribute | Details |
|---|---|
| Original dataset size | 303 records |
| Usable records after cleaning | 297 |
| Input features | 13 |
| Training records | 237 |
| Held-out test records | 60 |
| Problem type | Binary classification |
| Positive target | Original target greater than zero |
| Negative target | Original target equal to zero |

### Data Preparation

- Remove duplicate records.
- Exclude records missing required values according to the configured preprocessing logic.
- Convert the original target into a binary label.
- Split the usable records using stratified sampling.
- Fit preprocessing transformations within the training pipeline.

### External Dataset Exploration

The project includes a script for fetching additional processed UCI heart disease datasets from Hungary, Switzerland, and VA.

```powershell
python scripts/fetch_uci_external.py
```

Downloading external datasets does **not** automatically mean that external validation has been completed.

Differences in missing values, feature definitions, coding, and class distributions can make direct comparisons unreliable. Any external evaluation should document its preprocessing, feature mapping, exclusions, and limitations.

---

## 📈 Model Performance

The following results were recorded in the project's model artifacts on **October 27, 2026**, using scikit-learn 1.8.0.

The selected model was **Gradient Boosting**.

### Held-Out Test Results

| Metric | Recorded Result |
|---|---:|
| Accuracy | 0.817 |
| Precision | 0.870 |
| Recall | 0.714 |
| F1-score | 0.784 |
| ROC-AUC | 0.925 |
| Brier Score | 0.121 |

### Bootstrap Confidence Intervals

| Metric | Recorded 95% Interval |
|---|---|
| Accuracy | 0.717–0.917 |
| Recall | 0.536–0.885 |
| ROC-AUC | 0.851–0.982 |

### Project-Defined Threshold Experiment

At the application's configured decision boundary of `0.30`, the recorded results were:

| Metric | Result |
|---|---:|
| Recall | 0.929 |
| Precision | 0.765 |

Changing a decision threshold can change the balance between identifying positive cases and generating false positives.

The `0.30` boundary is a **project-defined experimental threshold**, not a clinically recommended threshold.

### Interpreting These Results

The reported metrics come from a small held-out test set. They should be treated as experimental results rather than evidence of clinical performance.

In particular:

- Results may vary across different data splits.
- A small test set can produce uncertain performance estimates.
- Historical data may not represent current patient populations.
- High ROC-AUC does not guarantee accurate individual predictions.
- Good classification performance does not automatically imply well-calibrated probabilities.
- No independent clinical validation is established by these results.

**Reproducibility:** Check `model/model_info.json` and `model/model_comparison.csv` for the metadata and comparison results associated with the current model artifacts. Refresh this section after retraining.

---

## 🔎 Prediction Interpretability

CardioNova explores several techniques to make model outputs easier to inspect.

| Technique | Purpose | Important Limitation |
|---|---|---|
| Input-range checks | Flag inputs outside observed training ranges | In-range values can still be inappropriate |
| Model disagreement | Indicate disagreement between model estimates | Disagreement is not a formal confidence interval |
| Boundary proximity | Flag predictions near configured decision boundaries | A boundary is not a clinical diagnosis threshold |
| Input consistency checks | Identify selected combinations requiring attention | Rules cannot detect every invalid or misleading input |
| Feature perturbation | Examine how changing an input affects a model output | Does not prove causation |
| Fixed-rule summaries | Present results in plain language | Simplifies model behavior and may omit important context |

These techniques help explore model behavior. They do not establish causal relationships, clinical certainty, or the reliability of a particular prediction.

---

## 📂 Project Structure

```text
CardioNova-Health/
│
├── heart_disease/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── prediction/
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   ├── static/
│   │   └── prediction/
│   ├── templates/
│   │   └── prediction/
│   └── ...
│
├── ml_pipeline/
│
├── dataset/
│   ├── heart.csv
│   └── external/
│
├── model/
│   ├── model_info.json
│   └── model_comparison.csv
│
├── scripts/
│
├── docs/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── train_model.py
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── render.yaml
```

The tree highlights major project areas. Exact filenames and generated artifacts may vary by version.

---

## 🚀 Installation and Setup

Follow these instructions to run the application locally on Windows using PowerShell.

### Prerequisites

- Python 3.11 or a compatible version supported by the project dependencies.
- Git.
- Visual Studio Code (recommended).
- A terminal such as PowerShell.

### 1. Clone the Repository

```powershell
git clone https://github.com/manishyadav-aiml/CardioNova-Health.git
cd CardioNova-Health
```

### 2. Create a Virtual Environment

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the following in the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Use the dependency versions specified by the project wherever possible.

### 4. Configure Environment Variables

Review `.env.example`, if present, and the Django settings.

Configure the required local environment variables before starting the application.

**Never commit `.env` files, passwords, API tokens, email credentials, or production secret keys.**

For deployment, use a unique secret key, disable debug mode, configure allowed hosts and trusted origins, and set up the database and email provider appropriately.

### 5. Apply Database Migrations

```powershell
python manage.py migrate
```

### 6. Run Django Checks

```powershell
python manage.py check
```

### 7. Start the Development Server

```powershell
python manage.py runserver
```

Open the application in your browser:

**http://127.0.0.1:8000/**

> Django's development server is intended for local development, not production deployment.

---

## 🧪 Training the Model

The repository includes a training entry point.

### View Available Options

```powershell
python train_model.py --help
```

### Train the Model

```powershell
python train_model.py
```

If the script supports quick mode, it can also be invoked with:

```powershell
python train_model.py --quick
```

Check the script's help output before using optional flags.

### Review the Generated Artifacts

After training, inspect the available model files and evaluation reports under `model/`.

Review:

- Model metadata.
- Model comparison results.
- Evaluation metrics.
- Generated plots and reports.
- Feature preprocessing and compatibility information.

**Warning:** Training may overwrite existing model artifacts and reports. Back up important files before retraining.

---

## ✅ Testing and Quality Checks

The project has previously recorded **91 passing automated tests**.

The following local checks were also reported as passing:

- Django system checks.
- Static file collection.
- Automated tests.

To repeat the checks in your current environment:

### Run Django System Checks

```powershell
python manage.py check
```

### Run Application Tests

```powershell
python manage.py test prediction
```

### Check for Uncommitted Model Changes

Run the relevant tests after modifying preprocessing, model artifacts, authentication, API endpoints, or database models.

### Check for Unintended Migration Changes

```powershell
python manage.py makemigrations --check --dry-run
```

### Check Static File Collection

```powershell
python manage.py collectstatic --noinput
```

A successful test suite is useful evidence of tested behavior, but it does not prove complete security, production readiness, or clinical reliability.

For a stronger release check, also test migrations against a fresh database and verify the deployment configuration.

---

## 🔐 Security Considerations

Security is especially important when an application handles health-related information.

The project includes or explores several security-related mechanisms. Review the current code and configuration before relying on them.

### Application Security Checklist

- [ ] Keep secret keys and credentials outside version control.
- [ ] Set `DEBUG=False` in production.
- [ ] Configure allowed hosts and trusted origins correctly.
- [ ] Use HTTPS in production.
- [ ] Validate inputs on the server.
- [ ] Enforce upload size and request limits.
- [ ] Apply authentication and authorization to protected views and APIs.
- [ ] Review session, password-reset, and rate-limiting behavior.
- [ ] Avoid exposing sensitive health information in logs.
- [ ] Review CSV upload and formula-injection protections.
- [ ] Configure database backups and recovery procedures.
- [ ] Test migrations and destructive operations before deployment.
- [ ] Review `docs/SECURITY.md`, if present.
- [ ] Conduct an independent security review before handling real users' health information.

### Responsible Handling of Health Data

Use synthetic or otherwise appropriately authorized data for demonstrations.

Doctor-access features should follow explicit consent and appropriate authorization rules. Verify that access restrictions apply to existing accounts as well as newly created accounts.

**This project should not be described as HIPAA-compliant or as meeting any other formal healthcare compliance standard without a proper assessment.**

---

## ⚠️ Limitations

CardioNova is a learning and portfolio project. Its current scope has important limitations.

1. **Limited dataset size:** The reported training and test results come from a small historical dataset.
2. **Limited representativeness:** The dataset may not reflect current or diverse patient populations.
3. **No established clinical validation:** The project does not demonstrate that its predictions are suitable for patient care.
4. **Experimental decision thresholds:** Configured risk bands and thresholds are project-defined.
5. **Heuristic indicators:** Model disagreement and boundary proximity are not formal measures of clinical uncertainty.
6. **Non-causal explanations:** Feature perturbations do not establish that a feature causes a health outcome.
7. **External data challenges:** Different datasets may use incompatible feature definitions, coding, and missing-value conventions.
8. **Deployment considerations:** Production security, monitoring, backup, recovery, and operational reliability require separate verification.

The application must not be used to diagnose disease, recommend treatment, or make medical decisions.

---

## 🔮 Future Improvements

Potential areas for further development include:

- [ ] Conduct carefully documented external-dataset evaluation.
- [ ] Evaluate subgroup performance while accounting for small sample sizes.
- [ ] Improve dataset provenance and preprocessing documentation.
- [ ] Track model versions and training experiments.
- [ ] Evaluate probability calibration on suitable independent data.
- [ ] Add monitoring for input distribution changes.
- [ ] Pin and audit production dependencies.
- [ ] Expand authentication and account-protection options.
- [ ] Improve structured application logging and monitoring.
- [ ] Add fresh-database migration and recovery tests.
- [ ] Conduct an independent application security assessment.
- [ ] Document reproducible training and deployment procedures.

These are proposed improvements, not claims that the features have already been implemented.

---

## 🎓 Learning Outcomes

This project demonstrates practical work across several areas of software engineering and machine learning.

### Machine Learning

- Data cleaning and preparation.
- Train-test splitting and cross-validation.
- Classification model comparison.
- Classification and probability metrics.
- Preprocessing pipelines.
- Model persistence and inference.

### Web Development

- Django application structure.
- Views, forms, templates, and authentication.
- Integrating machine learning models into web applications.
- API endpoint design.
- Data validation and result presentation.

### Software Engineering

- Automated testing.
- Git and GitHub workflows.
- Environment configuration.
- Docker-based workflows.
- Continuous integration.
- Security-conscious application development.
- Technical documentation.

### Responsible AI

- Communicating model limitations.
- Distinguishing model estimates from clinical measurements.
- Recognizing dataset bias and representativeness issues.
- Understanding why validation and monitoring matter.

---

## 🎯 Academic Relevance

CardioNova Health can serve as a **final-year B.Tech CSE / AIML academic and portfolio project**, provided the submitted implementation, report, model artifacts, and demonstration accurately reflect the work completed.

For a project demonstration or interview, be prepared to explain:

1. Why the dataset was selected and how its target was encoded.
2. How training and testing data were separated.
3. Why preprocessing was fitted within a pipeline.
4. How cross-validation was used for model selection.
5. What accuracy, precision, recall, F1-score, ROC-AUC, and Brier score mean.
6. How Django loads the model and processes an input.
7. How authentication and authorization protect user information.
8. What the automated tests cover.
9. Why the results do not establish clinical validity.
10. What you would improve before considering a production deployment.

A strong project presentation should include the running application, a reproducible training workflow, test results, and a clear explanation of the limitations.

---

## 👨‍💻 Author

**Manish Kumar Yadav**

Final-Year B.Tech Student | Computer Science Engineering — AI & Machine Learning

- GitHub: [@manishyadav-aiml](https://github.com/manishyadav-aiml)
- Project Repository: [CardioNova-Health](https://github.com/manishyadav-aiml/CardioNova-Health)

---

## 📄 License

Check the repository's root directory for a `LICENSE` file.

If no license exists, choose and add an appropriate license before granting others permission to reuse, modify, or distribute the code.

A publicly accessible GitHub repository does not automatically grant permission to reuse its contents.

---

## ⚕️ Medical Disclaimer

**CardioNova Health is an educational and portfolio project. It is not a medical device, does not diagnose, treat, cure, or prevent disease, and must not be used to make medical decisions. Its outputs are experimental model estimates, not personal clinical risk measurements. Consult a qualified healthcare professional for medical advice.**

---

<div align="center">

**Built to explore machine learning, web development, and responsible AI.**

⭐ If you find this project useful for learning, consider starring the repository.

</div>