<div align="center">

# ❤️ CardioNova Health

### Explainable Machine Learning–Based Heart Disease Risk Prediction System

**An Intelligent Web-Based Decision-Support Prototype Powered by Machine Learning**

<p>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-Web_Framework-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/Machine_Learning-scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white" alt="Machine Learning">
  <img src="https://img.shields.io/badge/Explainable_AI-Model_Interpretation-6A5ACD?style=for-the-badge" alt="Explainable AI">
</p>

<p>
  <img src="https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white" alt="Database">
  <img src="https://img.shields.io/badge/API-REST-009688?style=flat-square" alt="REST API">
  <img src="https://img.shields.io/badge/Deployment-Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Status-Academic_Project-blue?style=flat-square" alt="Project Status">
</p>

**Smarter Insights. Healthier Hearts.**

*A machine learning project exploring heart disease classification, model
interpretability, probability estimation, privacy-aware web development,
and automated evaluation.*

</div>

---

> ⚠️ **IMPORTANT MEDICAL DISCLAIMER**
>
> CardioNova Health is an educational and experimental machine learning
> project. It is not a medical device, and its clinical validity has not
> been established. Its outputs must not be used to diagnose, treat, or
> rule out heart disease. The predictions do not replace professional
> medical evaluation, advice, or emergency care.

---

# 📑 Table of Contents

- [🌟 Project Overview](#-project-overview)
- [🎯 Problem Statement](#-problem-statement)
- [💡 Project Objectives](#-project-objectives)
- [✨ Key Features](#-key-features)
- [🚀 What Makes CardioNova Different](#-what-makes-cardionova-different)
- [🏗️ System Architecture](#️-system-architecture)
- [🔄 Application Workflow](#-application-workflow)
- [🤖 Machine Learning Methodology](#-machine-learning-methodology)
- [📊 Dataset Description](#-dataset-description)
- [🧠 Explainable AI](#-explainable-ai)
- [🚦 Risk Classification](#-risk-classification)
- [👥 User Roles and Privacy](#-user-roles-and-privacy)
- [📦 Batch CSV Prediction](#-batch-csv-prediction)
- [🔌 REST API](#-rest-api)
- [🛠️ Technology Stack](#️-technology-stack)
- [📁 Project Structure](#-project-structure)
- [💻 Installation and Setup](#-installation-and-setup)
- [▶️ Running the Application](#️-running-the-application)
- [🧪 Testing and Quality Assurance](#-testing-and-quality-assurance)
- [🔐 Security](#-security)
- [🚀 Deployment](#-deployment)
- [📈 Model Evaluation](#-model-evaluation)
- [⚠️ Limitations](#️-limitations)
- [🔮 Future Enhancements](#-future-enhancements)
- [🎓 Academic Relevance](#-academic-relevance)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [⚕️ Final Disclaimer](#️-final-disclaimer)

---

# 🌟 Project Overview

**CardioNova Health** is a web-based heart disease risk prediction
prototype developed using Python, Django, and machine learning.

The application accepts 13 health-related input parameters, processes
them through a trained classification model, and displays the model's
estimated probability of a positive heart disease classification.

The project combines machine learning with a complete web application
workflow, including user authentication, prediction history, explainable
results, PDF report generation, CSV-based batch processing, and
token-authenticated API access.

The system is designed to demonstrate how a machine learning model can
be integrated into a practical software application while making its
outputs easier to inspect and understand.

## 📌 Project Information

| Attribute | Details |
|---|---|
| Project Name | CardioNova Health |
| Project Domain | Artificial Intelligence and Machine Learning |
| Project Category | Healthcare Analytics / Classification |
| Application Type | Django Web Application |
| Academic Level | Final-Year BTech CSE |
| Project Type | Major Project / Capstone Candidate |
| Primary Language | Python |
| Web Framework | Django |
| Machine Learning Library | scikit-learn |
| Main Dataset | UCI Heart Disease Cleveland dataset |
| Input Features | 13 health-related attributes |
| Prediction Type | Binary classification |
| Explainability | Feature ablation and permutation importance |
| Database | SQLite for local development, PostgreSQL where configured |
| API | JSON REST endpoints |
| Deployment Options | Docker and compatible cloud platforms |

The final project classification depends on the institution's academic
requirements and the depth of the verified implementation.

## 🎯 Intended Application

CardioNova Health demonstrates the integration of:

- Data preprocessing and validation.
- Supervised machine learning.
- Classification and probability estimation.
- Model comparison and evaluation.
- Explainable machine learning.
- Web application development.
- Database-backed prediction history.
- Privacy-aware access control.
- Automated testing and deployment.

The application is an academic prototype and is not intended for
independent medical decision-making.

---

# 🎯 Problem Statement

Heart disease datasets contain multiple health-related attributes that
can be studied using statistical and machine learning methods.

However, a prediction model by itself does not provide a complete
application. Users also need a suitable interface, understandable
outputs, consistent input validation, and clear information about
the limitations of the model.

A web application can provide a convenient environment for exploring
machine learning predictions, comparing model outputs, and examining
how input features influence a model's estimate.

CardioNova Health addresses this software-development problem by
integrating a classification pipeline with a Django application.

### Key Problems Addressed

| Problem | Project Approach |
|---|---|
| Raw data requires preprocessing | Data validation and preprocessing pipeline |
| Different algorithms may perform differently | Cross-validated model comparison |
| Accuracy alone does not describe model behavior | Multiple evaluation metrics |
| Model outputs can be difficult to interpret | Feature-ablation explanations |
| Predictions need a usable interface | Django-based web application |
| Users may need to revisit previous results | Database-backed prediction history |
| Large numbers of records may require processing | CSV-based batch prediction |
| Other applications may need programmatic access | JSON API |
| Health-related data requires careful access controls | Authentication and privacy settings |
| Model outputs can be misunderstood | Explicit limitations and disclaimers |

---

# 💡 Project Objectives

The primary objectives of CardioNova Health are:

1. To develop a machine learning pipeline for heart disease classification.
2. To compare multiple classification algorithms using consistent
   evaluation procedures.
3. To apply suitable data preprocessing and validation techniques.
4. To investigate hyperparameter tuning and ensemble learning.
5. To evaluate classification performance using multiple metrics.
6. To investigate probability calibration where appropriate.
7. To explain individual predictions using model-agnostic techniques.
8. To develop a web application using Django.
9. To provide user authentication and access-controlled prediction history.
10. To support downloadable reports and batch prediction.
11. To expose selected application functions through a JSON API.
12. To implement automated tests and deployment configuration.
13. To document limitations and responsible use of machine learning
    in a healthcare-related application.

---

# ✨ Key Features

## 🤖 1. Machine Learning

The project includes a training pipeline designed to compare multiple
classification algorithms.

| Feature | Description |
|---|---|
| Model comparison | Evaluate several classification algorithms |
| Hyperparameter tuning | Search selected parameter combinations |
| Cross-validation | Estimate performance across training folds |
| Ensemble learning | Compare voting and stacking approaches |
| Probability estimation | Produce model probability outputs where supported |
| Calibration analysis | Investigate probability calibration |
| Model persistence | Save the selected trained model |
| Reproducibility | Use configured random seeds where applicable |

## 📊 2. Model Evaluation

The training pipeline is designed to generate multiple performance
metrics and evaluation charts.

| Metric | Purpose |
|---|---|
| Accuracy | Measures overall classification correctness |
| Precision | Measures the proportion of positive predictions that are correct |
| Recall | Measures the proportion of positive cases identified |
| F1-score | Combines precision and recall |
| ROC-AUC | Evaluates ranking discrimination |
| Brier score | Evaluates probability prediction error |
| Confusion matrix | Summarizes true and false classifications |
| Calibration curve | Compares predicted probabilities with observed frequencies |
| Permutation importance | Estimates the effect of feature shuffling on model performance |

Actual performance must be calculated using the current dataset and
training pipeline.

## 🔍 3. Explainable AI

- Feature-ablation explanations for individual predictions.
- Percentage-point changes in model output.
- Global permutation feature importance.
- Explanation information displayed with prediction results.
- Explanation information included in supported PDF and API responses.

These explanations describe model behavior, not medical causation.

## 👤 4. User Management

- Patient registration.
- Login and logout.
- Django authentication.
- Administrator-managed doctor roles.
- Personal prediction history.
- Configurable doctor-sharing preference.
- Supported prediction and account deletion workflows.

## 📈 5. Prediction History

The application is designed to let users review their saved predictions.

Potential history functions include:

- Personal prediction records.
- Search and filtering.
- Pagination.
- Historical result review.
- Risk-label trend charts.

A historical chart summarizes stored model outputs; it is not a
validated representation of a person's changing medical risk.

## 📄 6. PDF Reports

The application includes a PDF reporting module.

Depending on the implemented version, reports can include:

- Prediction summary.
- Model probability.
- Application-defined classification.
- Explanation of influential features.
- Submitted input values.
- Generation date.
- Medical disclaimer.

PDF reports must not be represented as hospital-issued or
clinically validated documents.

## 📦 7. Batch CSV Prediction

- CSV file upload.
- Input column validation.
- Row-level error reporting.
- Configured file-size and row-count limits.
- Prediction output for valid records.
- Optional saving to history.
- CSV results download.

## 🔌 8. REST API

- Model health endpoint.
- Authenticated prediction endpoint.
- Authenticated prediction history endpoint.
- JSON request and response formats.
- Input validation and error responses.

## 🔐 9. Security and Privacy

- Django authentication.
- CSRF protection where applicable.
- Server-side input validation.
- Access-controlled prediction records.
- Token-based API authentication.
- Environment-based configuration.
- Restrictions on batch-upload size.
- Logging designed to avoid recording submitted health values.

The implementation and tests must be reviewed before these controls
are described as fully verified.

## 🚀 10. Deployment Support

The repository is designed to support deployment through configuration
files for:

- Docker.
- Docker Compose.
- PostgreSQL.
- Gunicorn.
- WhiteNoise.
- Render-compatible deployment.
- Automated GitHub Actions checks.

Deployment requires appropriate environment variables, a verified
dataset, valid model artifacts, and production security configuration.

---

# 🚀 What Makes CardioNova Different?

## 1. Per-Prediction Trust Check

The application can present warnings when a prediction requires
additional caution.

Examples include:

- Inputs that fail validation.
- Missing or incompatible model artifacts.
- Inputs that differ substantially from the training data, if such
  checks are implemented.
- Other explicitly implemented reliability warnings.

A trust check must not be presented as a guarantee that the model
is correct or clinically reliable.

## 2. What-If Simulator

The what-if simulator is intended to demonstrate how changing an
input affects the model's output.

For example, it may compare the output for the original inputs
with the output after one input is changed.

This is a software and model-interpretation feature. It does not
establish that changing the input will cause a corresponding change
in a person's actual medical risk.

Implementation documentation:

`docs/INNOVATION_AND_INTERVIEW.md`

## 3. Multi-Dataset Evaluation

The training workflow supports evaluation on separate datasets when
they have been correctly prepared and made compatible with the
primary dataset.

This can help reveal whether model performance changes across
different data sources.

External evaluation is meaningful only when the actual external
datasets are available and the evaluation has been executed.

## 4. Multiple Access Methods

The same application provides several ways to interact with the
prediction workflow:

| Access Method | Intended Use |
|---|---|
| Web form | Individual interactive prediction |
| Prediction history | Review previously saved results |
| Batch CSV | Process multiple records |
| JSON API | Programmatic integration |
| PDF report | Download a formatted result summary |

---

# 🏗️ System Architecture

CardioNova Health contains an offline model-training workflow and
an online prediction workflow.

## A. Model Training Architecture

```text
                 DATASET
                    |
                    v
        Dataset Validation and Cleaning
                    |
                    v
           Target Preparation
                    |
                    v
          Stratified Data Split
             /           \
            v             v
      Training Data     Test Data
            |
            v
     Preprocessing Pipeline
            |
            v
    Candidate Model Training
            |
            v
      Hyperparameter Tuning
            |
            v
     Cross-Validation Results
            |
            v
       Model Selection
            |
            v
   Probability Calibration Review
            |
            v
     Final Held-Out Evaluation
            |
            v
      Saved Model Artifacts
            |
            v
       Evaluation Reports
