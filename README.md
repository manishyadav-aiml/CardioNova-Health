<div align="center">

🫀 CardioNova Health

Uncertainty-Aware Heart Disease Risk Estimation

A Django + scikit-learn web application for healthcare ML education and experimentation

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-4.2%20to%205.x-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/scikit--learn-1.8-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white" alt="scikit-learn">
  <img src="https://img.shields.io/badge/Automated_Tests-91-success?style=for-the-badge" alt="91 automated tests">
</p>

<p>
  <img src="https://img.shields.io/badge/Project-Final--Year%20B.Tech-blue?style=flat-square" alt="Final year BTech project">
  <img src="https://img.shields.io/badge/Domain-Healthcare%20ML-purple?style=flat-square" alt="Healthcare ML">
  <img src="https://img.shields.io/badge/Status-Educational%20Project-informational?style=flat-square" alt="Educational project">
</p>

</div>

Medical disclaimer: CardioNova Health is an educational and portfolio project. It is not a medical device, does not diagnose, treat, cure, or prevent disease, and must not be used to make medical decisions. Its outputs are experimental model estimates, not personal clinical risk measurements. Consult a qualified healthcare professional for medical advice.

📚 Table of Contents

Project Overview

Problem Statement

Objectives

Key Features

Technology Stack

System Architecture

Machine Learning Workflow

Dataset

Model Evaluation

Explainability and Prediction Trust

Project Structure

Installation and Setup

Running the Application

Training and Evaluating the Model

Tests and Quality Checks

Security and Privacy

Limitations

Future Improvements

Skills Demonstrated

Academic and Portfolio Relevance

Author

License

📖 Project Overview

CardioNova Health demonstrates an end-to-end machine-learning workflow: preparing a structured dataset, training and evaluating classifiers, persisting the selected model, and integrating inference into a Django web application.

Unlike a basic demo that only displays a class label, the application includes features intended to make model behaviour easier to inspect: a prediction trust check, a rule-based plain-language summary, feature perturbation explanations, and a what-if simulator. These are software and model-inspection aids—not clinical guarantees.

Project Information

Item

Details

Project name

CardioNova Health

Domain

Healthcare analytics and machine learning

Project type

Final-year B.Tech CSE project and portfolio project

Application

Django web application

Language

Python

ML library

scikit-learn

Data processing

pandas and NumPy

Database/deployment options

Django-supported database configuration; PostgreSQL in Docker Compose configuration

Development environment

Visual Studio Code

Version control

Git and GitHub

🎯 Problem Statement

Structured health datasets contain multiple attributes that can be explored with supervised learning. This project investigates how classification models learn patterns associated with a labelled heart-disease outcome and how a trained model can be exposed through a web application.

The goal is to demonstrate a documented ML workflow and responsible presentation of experimental predictions. The system is not designed to replace clinicians, perform diagnosis, or recommend treatment.

✅ Objectives

Load and inspect a structured heart-disease dataset.

Prepare features and target labels consistently.

Compare classification models using cross-validation.

Keep preprocessing inside model pipelines to reduce data leakage risk.

Evaluate the selected model on a held-out test set.

Investigate probability calibration and prediction uncertainty indicators.

Integrate persisted model artifacts into a Django application.

Provide account-based features and privacy-conscious doctor sharing.

Test application behaviour, access control, validation, and security-related cases.

Document limitations and avoid unsupported clinical claims.

✨ Key Features

Prediction and user experience

Patient registration and login.

Health-attribute input form and model-generated prediction result.

Prediction history with charts.

Batch CSV prediction workflow.

Downloadable PDF report.

Dark-mode styling, FAQ, contact form, and print stylesheet.

Model transparency

Prediction trust check: combines indicators such as unusual input values, disagreement between fold models, proximity to a risk-band boundary, and data-entry checks. It reports a Good/Fair/Low trust indication and reasons; this is a heuristic, not a statistically validated guarantee.

Plain-language summary: fixed server-side rules turn model outputs into explanatory text and possible questions to discuss with a clinician. No external generative-AI service is required for this summary.

What-if simulator: re-scores supported changes to selected fields so users can inspect model behaviour. It does not establish medical cause and effect.

Feature perturbation explanation: replaces an input with a training-data reference value and displays the resulting change in model output. This is an explanation of model behaviour, not causation.

Probability calibration experiment: compares calibrated and uncalibrated model probability behaviour.

Privacy, access, and API

Patient and doctor roles.

Doctor access to patient information is opt-in; access events are logged for patient review.

JSON API endpoints for prediction, what-if analysis, and history (/api/predict/, /api/whatif/, /api/history/).

API bearer tokens are stored as hashes rather than plaintext tokens.

Security and delivery

Rate limiting and request/upload size controls.

Security headers and Content Security Policy configuration.

CSV formula-injection protections.

Password-reset flows using OTP and email links.

Password-confirmed account deletion flow.

Docker configuration, PostgreSQL service configuration, Render blueprint, and GitHub Actions CI workflow.

See docs/SECURITY.md and docs/DEPLOYMENT.md for implementation-specific details. A listed feature should be considered verified only after it is checked in the current code and tested in the running application.

🛠️ Technology Stack

Technology

Purpose

Python

Application and ML code

Django

Routing, views, forms, authentication, database integration

scikit-learn

Pipelines, model training, cross-validation, calibration, evaluation

pandas / NumPy

Tabular data processing and numerical operations

joblib / pickle-based artifacts

Persisting trained estimator and preprocessing artifacts

HTML / CSS / JavaScript

Browser interface and interactive components

Django test framework

Application and regression tests

Git / GitHub

Source control and repository hosting

Docker / Docker Compose

Containerized application and database setup

GitHub Actions

Automated CI workflow

The authoritative dependency list is requirements.txt. The committed model artifacts were generated with scikit-learn 1.8.0; use the pinned version when loading them unless the artifacts are retrained and tested with another version.

🏗️ System Architecture

Browser / User
      │
      ▼
Django URLs, Views, Forms and Authentication
      │
      ▼
Input Validation and Application Rules
      │
      ▼
Saved ML Model + Required Preprocessing Artifacts
      │
      ▼
Prediction, Trust Indicators and Explanations
      │
      ▼
Result Page / History / PDF / API Response

Offline model development:
Dataset → Data preparation → Train/test split → Cross-validation
        → Model comparison and calibration → Evaluation → Saved artifacts

This is a conceptual view. The exact request path and persistence behaviour are defined by the current Django views, forms, model-loading code, and settings.

🧠 Machine Learning Workflow

Load data: read dataset/heart.csv through the shared loader in ml_pipeline/data.py.

Prepare labels: remove duplicate rows and, for the main training dataset, records with missing required values. The target is converted to a binary no-disease/disease label by treating values greater than zero as positive.

Split data: the recorded training artifact used 297 usable rows, with a stratified 80/20 split of 237 training rows and 60 test rows.

Preprocess in a pipeline: median imputation and standard scaling are fitted as part of the training pipeline, rather than before splitting.

Compare models: tune six individual classifiers with GridSearchCV and five-fold stratified cross-validation using ROC-AUC.

Compare ensembles: evaluate soft voting and stacking ensembles alongside the individual models.

Select a model: select using training cross-validation ROC-AUC, not by selecting whichever model looks best on the held-out test set.

Calibrate and evaluate: apply the configured sigmoid calibration process and evaluate on the held-out test set. The training script also computes bootstrap confidence intervals and permutation feature importance.

Save artifacts: write the model, preprocessing artifact, comparison table, model metadata, and charts used by the web application.

External evaluation: the training script can evaluate compatible datasets placed in dataset/external/. Results must be interpreted cautiously because dataset completeness, coding, and class distribution may differ.

📊 Dataset

The main file is dataset/heart.csv, based on the historical UCI Cleveland heart-disease dataset and its 13 input features. The local file has 303 rows initially; removing duplicate and incomplete records leaves 297 usable records for the recorded experiment.

Property

Description

Task

Supervised binary classification

Input

13 structured clinical attributes encoded in the dataset

Target

Original target values converted to 0 = no disease and 1 = disease present (target > 0)

Usable records in recorded run

297

Training records

237

Held-out test records

60

Intended use

Educational experimentation and portfolio demonstration

External datasets

The project includes scripts/fetch_uci_external.py, which downloads historical UCI processed datasets for Hungary, Switzerland, and the VA site into dataset/external/. These files contain substantial missingness and may have small or highly imbalanced classes. Matching column names does not by itself prove that feature meanings, measurement practices, or category coding are identical across sites.

External validation results are not claimed here. Run the training/evaluation process and inspect model/model_info.json before reporting external metrics. For the Switzerland dataset in particular, very few negative examples make some metrics unstable. Do not describe these datasets as current hospital data or as representative of all populations.

📈 Model Evaluation

The included model/model_info.json and model/model_comparison.csv record an experiment trained on 2026-10-27 with scikit-learn 1.8.0. The selected model in those saved artifacts is Gradient Boosting. These values describe that recorded run; they must be refreshed after retraining before being presented as results from a newer experiment.

Recorded held-out test results

Metric

Recorded result

Accuracy

0.817

Precision

0.870

Recall

0.714

F1-score

0.784

ROC-AUC

0.925

Brier score

0.121

The recorded 95% bootstrap intervals were 0.717–0.917 for accuracy, 0.536–0.885 for recall, and 0.851–0.982 for ROC-AUC. The held-out test set contains only 60 rows, so these estimates have substantial uncertainty.

The recorded experiment also reported recall of 0.929 at the application's 0.30 low/moderate boundary, with precision 0.765. This is a project-defined threshold and must not be interpreted as a clinically established decision threshold.

How to interpret the metrics

Accuracy: fraction of predictions that were correct.

Precision: fraction of positive predictions that were correct.

Recall: fraction of positive-labelled cases identified by the model.

F1-score: harmonic mean of precision and recall.

ROC-AUC: ability to rank positive-labelled cases above negative-labelled cases across thresholds.

Brier score: mean squared error of predicted probabilities; lower is generally better on the evaluated sample.

These metrics do not establish clinical usefulness, diagnostic accuracy in practice, fairness, or safe use with individual patients. A small test set and one historical dataset limit conclusions about generalization.

🔍 Explainability and Prediction Trust

The application provides model-behaviour indicators rather than medical explanations:

Input-range checks: flag values outside reference ranges derived from the training data.

Fold-model disagreement: uses differences among cross-validation fold models as one uncertainty signal.

Boundary proximity: indicates when a probability is close to a project-defined risk-band threshold.

Input consistency checks: flag selected implausible combinations or possible entry errors.

Feature perturbation: compares the prediction with one input replaced by a reference value.

Plain-language summary: explains the model output using fixed server-side rules.

These signals are heuristic. They are not a formal confidence interval, a validated measure of clinical uncertainty, or evidence that an input caused a health outcome.

📂 Project Structure

CardioNova-Health/
├── heart_disease/                 # Django settings, URLs, ASGI/WSGI
├── prediction/                    # App views, forms, ML logic, templates, tests
│   ├── migrations/                # Database schema migrations
│   ├── management/commands/       # Management commands, including doctor setup
│   ├── static/prediction/         # CSS, JavaScript, charts and report assets
│   └── templates/prediction/      # HTML templates
├── ml_pipeline/                   # Shared dataset-loading helpers
├── dataset/
│   ├── heart.csv                  # Main dataset
│   └── external/                  # Optional external evaluation datasets
├── model/                         # Saved model, preprocessing and metrics
├── scripts/                       # External dataset fetch and security scan scripts
├── docs/                          # Security, deployment and project documentation
├── .github/workflows/ci.yml       # GitHub Actions workflow
├── train_model.py                 # Model training/evaluation pipeline
├── manage.py                      # Django management entry point
├── requirements.txt               # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── README.md

Generated folders, optional files, or paths may vary by checkout. The actual repository contents are authoritative.

⚙️ Installation and Setup

Prerequisites

A Python version supported by the project's dependency pins (the repository includes .python-version; check it before creating an environment).

Git and PowerShell on Windows.

Visual Studio Code or another code editor.

1. Clone the repository

git clone https://github.com/manishyadav-aiml/CardioNova-Health.git
cd CardioNova-Health

2. Create and activate a virtual environment

python -m venv venv
.\venv\Scripts\Activate.ps1

If PowerShell blocks activation, allow scripts for this terminal session only, then retry:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

3. Install dependencies

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Use the dependency versions defined by the repository. Model files saved with one scikit-learn version may not be compatible with another version.

4. Configure environment variables

Review heart_disease/settings.py and .env.example for the variables required by this project. For local development, create a local .env based on the example and set the values needed by your environment. Do not copy example secrets into a public production deployment, and never commit real .env files, passwords, or secret keys.

5. Apply migrations and check the project

python manage.py migrate
python manage.py check

6. Start the development server

python manage.py runserver

Open http://127.0.0.1:8000/ in your browser. Stop the server with Ctrl+C. Django's built-in server is for development and testing, not production hosting.

🤖 Training and Evaluating the Model

Important: training overwrites files in model/ and generates report charts. Back up the current model artifacts before running it if you need to preserve the previous experiment.

Inspect supported options:

python train_model.py --help

Run the full training/evaluation workflow:

python train_model.py

Or run the smaller quick search if supported by the current script:

python train_model.py --quick

To download the optional external evaluation datasets:

python scripts/fetch_uci_external.py

Then rerun training/evaluation to calculate external metrics. Review the terminal output and updated model/model_info.json; do not claim external validation merely because the files were downloaded. Confirm data compatibility and missingness before interpreting results.

🧪 Tests and Quality Checks

The recorded local verification for this project version includes 91 passing tests in python manage.py test prediction, a successful Django system check, and a successful collectstatic run. Rerun the commands below after changing code, dependencies, model artifacts, or templates.

python manage.py check
python manage.py test prediction
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput

The project also contains a GitHub Actions workflow. Passing tests provide evidence about the cases covered by the suite; they do not prove that the application is completely secure or clinically reliable. A fresh-database migration test and deployment-specific checks should be completed before production use.

🔐 Security and Privacy

Security controls are particularly important because the application handles health-related inputs. The repository includes security-focused implementation and tests, but a checklist or passing test suite is not a guarantee of complete security.

Keep secret keys, credentials, and local environment files out of version control.

Keep production debug mode disabled and configure allowed hosts correctly.

Use HTTPS in deployed environments.

Validate and limit incoming requests and uploaded files.

Apply authentication and authorization checks to protected views and APIs.

Review rate limiting, proxy configuration, session handling, password reset, and account deletion flows.

Avoid logging unnecessary personal or health information.

Back up the database before migrations or destructive data operations.

Review docs/SECURITY.md and test the production configuration separately.

Do not claim HIPAA or other regulatory compliance without a formal assessment that supports the claim.

Doctor sharing is designed to be opt-in. Verify the actual database state and migration behaviour before assuming that an existing account's preferences have changed automatically.

⚠️ Limitations

Small dataset: the recorded run used 297 complete records from a historical dataset.

Limited representativeness: the dataset does not represent every demographic group, geography, or clinical setting.

No clinical validation: the model is not established for diagnosis, treatment, or medical decisions.

Experimental risk bands: the 0.30 and 0.60 boundaries are project-defined, not clinical standards.

Uncertainty indicators are heuristic: they should not be treated as formal guarantees of prediction reliability.

Explanations are not causal: feature changes describe model response, not the cause of disease.

External data comparability: missingness, small class counts, and differing data collection practices can make cross-site metrics unreliable or hard to compare.

Deployment requires more verification: database migrations, secrets, HTTPS, monitoring, backups, and production configuration need separate review.

No guarantee of future performance: dataset shift or changed usage patterns may affect model behaviour.

🚀 Future Improvements

Complete and document careful external-dataset evaluation.

Investigate model performance across age and sex groups, while reporting small-sample limitations.

Add experiment tracking and model versioning.

Improve reproducibility and dataset provenance documentation.

Review calibration on suitable independent data.

Add drift monitoring if the application is deployed.

Consider integrity-pinned or self-hosted frontend dependencies.

Review multi-factor authentication and operational monitoring.

Test fresh-database migrations and deployment recovery procedures.

Conduct an independent security review before handling real sensitive information.

These are proposed improvements, not claims that the features are already implemented.

💼 Skills Demonstrated

Skill

Evidence in this project

Python

Application logic and model-training scripts

Machine learning

Supervised classification and model comparison

scikit-learn

Pipelines, cross-validation, calibration, evaluation

Data processing

Tabular loading, missing-data handling, target preparation

Model evaluation

Precision, recall, F1-score, ROC-AUC, Brier score, bootstrap intervals

Django

Web routing, views, forms, authentication and persistence

API development

JSON endpoints and token-based access

Software testing

Automated tests and regression checks

Application security

Access controls, request validation, rate limiting and security headers

Git and GitHub

Source control and CI workflow

Responsible AI

Documenting limits and avoiding unsupported clinical claims

🎓 Academic and Portfolio Relevance

CardioNova Health can be presented as a final-year B.Tech CSE project when the submitted source code, model artifacts, report, and demonstration are consistent with the claims in this README.

For an academic viva or technical interview, be ready to explain:

Why this dataset and target encoding were selected.

How the training/test split and cross-validation work.

Why preprocessing belongs inside the pipeline.

Why ROC-AUC, recall, precision, and Brier score provide different information.

What calibration does—and what it does not prove.

How Django loads the model and validates input.

How authentication, role-based access, opt-in sharing, and tests work.

Why the project must not be used as a clinical diagnostic tool.

A strong presentation distinguishes implemented features from planned work and reports only metrics that can be reproduced from the saved artifacts and training code.

👨‍💻 Author

Manish Kumar Yadav
Final-year B.Tech Computer Science and Engineering (AI/ML) student

GitHub profile: https://github.com/manishyadav-aiml

Project repository: https://github.com/manishyadav-aiml/CardioNova-Health

📜 License

Check whether the repository contains a root-level LICENSE file before describing the project as open source. If no license exists, choose and add an appropriate license before granting reuse permissions. Public availability on GitHub does not automatically grant permission to reuse the code.

⚖️ Final Disclaimer

CardioNova Health is an educational machine-learning demonstration. It is not intended to diagnose, treat, cure, or prevent disease. Its outputs must not be used as the sole basis for medical decisions. Reported metrics are experimental results from a limited dataset and do not establish clinical effectiveness, safety, or generalization to real-world medical populations.