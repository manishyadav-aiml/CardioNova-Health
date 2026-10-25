# 🫀 CardioNova Health — Heart Disease Prediction System

### An ML-Powered Web Application for Heart Disease Risk Prediction

CardioNova Health is a machine learning-based web application developed to estimate the likelihood of heart disease using structured patient health attributes. Built with Python, Django, and Scikit-learn, the project demonstrates the integration of a machine learning pipeline with a web application.

The project covers model training, evaluation, model persistence, web integration, and automated testing. It is designed as a final-year BTech Computer Science and Engineering project and an AI/ML portfolio project.

> **Medical Disclaimer:** This application is intended for educational and research demonstration purposes only. It is not a medical device, does not provide a clinical diagnosis, and must not be used as a substitute for professional medical advice.

---

## 📌 Table of Contents

1. [Project Overview](#-project-overview)
2. [Problem Statement](#-problem-statement)
3. [Project Objectives](#-project-objectives)
4. [Key Features](#-key-features)
5. [Technology Stack](#-technology-stack)
6. [System Architecture](#-system-architecture)
7. [Machine Learning Workflow](#-machine-learning-workflow)
8. [Dataset](#-dataset)
9. [Model Evaluation](#-model-evaluation)
10. [Model Explainability](#-model-explainability)
11. [Project Structure](#-project-structure)
12. [Installation and Setup](#-installation-and-setup)
13. [Running the Application](#-running-the-application)
14. [Training the Model](#-training-the-model)
15. [Running Tests](#-running-tests)
16. [Security and Privacy](#-security-and-privacy)
17. [Limitations](#-limitations)
18. [Future Improvements](#-future-improvements)
19. [Skills Demonstrated](#-skills-demonstrated)
20. [Author](#-author)
21. [License](#-license)

---

## 📖 Project Overview

Heart disease is a major global health concern. Machine learning provides methods for analyzing structured health data and identifying statistical patterns associated with disease outcomes.

CardioNova Health demonstrates how a supervised machine learning model can be integrated into a Django web application to estimate the likelihood of heart disease from supported patient health attributes.

### Project Information

| Property | Details |
|---|---|
| Project Name | CardioNova Health |
| Project Domain | Healthcare Analytics and Machine Learning |
| Project Type | Final-Year BTech CSE Project |
| Application Type | Machine Learning Web Application |
| Programming Language | Python |
| Web Framework | Django |
| Machine Learning Library | Scikit-learn |
| Selected Model in Latest Recorded Experiment | Random Forest |
| Development Environment | Visual Studio Code |
| Version Control | Git and GitHub |
| Primary Purpose | Academic Project and AI/ML Portfolio |

### Project Goals

- Develop a machine learning pipeline for a healthcare-related classification problem.
- Compare candidate classification models.
- Evaluate model performance using appropriate metrics.
- Integrate a trained model into a Django application.
- Maintain automated tests for application behavior.
- Document model limitations and responsible-use considerations.

---

## 🎯 Problem Statement

Assessing heart disease risk involves interpreting multiple patient health attributes. This project explores the use of supervised machine learning to identify patterns in a labeled dataset and estimate the likelihood of a heart disease outcome.

The goal is to build an educational application that demonstrates the complete workflow from data preparation and model training to evaluation and web integration.

The system is not intended to replace doctors or independently determine whether a person has heart disease.

---

## 🎯 Project Objectives

1. Load and prepare a structured heart disease dataset.
2. Perform data preprocessing appropriate to the selected features.
3. Train and compare classification algorithms.
4. Evaluate models using cross-validation and held-out test data.
5. Investigate probability calibration.
6. Save trained model artifacts for application use.
7. Integrate the prediction pipeline with Django.
8. Test application functionality and security-related behavior.
9. Document evaluation results, limitations, and possible improvements.

---

## ✨ Key Features

The following features describe the project's core areas. Confirm the current implementation before claiming optional features as completed.

### 1. Heart Disease Prediction

Uses a trained machine learning model to generate predictions from supported input features.

### 2. Django Web Application

Provides a web interface through which users can interact with the prediction system.

### 3. Machine Learning Pipeline

Separates model development and training from the web application's prediction workflow.

### 4. Model Evaluation

Evaluates the selected model using classification metrics, including accuracy, precision, recall, F1-score, ROC-AUC, and Brier score.

### 5. Probability Calibration Experiment

Compares Brier scores before and after calibration to investigate the quality of predicted probabilities.

### 6. Model Persistence

Stores trained model artifacts so that the application can load the model without retraining it for every prediction.

### 7. Automated Testing

Includes an automated test suite for checking application behavior and selected security-related cases.

### 8. Security Improvements

Includes changes to password-reset templates that remove unnecessary use of Django's `safe` template filter.

> Feature availability, exact prediction outputs, and security coverage should be verified against the current source code before making broader claims.

---

## 🛠️ Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Programming Language | Python | Application and ML development |
| Web Framework | Django | Server-side web application |
| Machine Learning | Scikit-learn | Training and evaluating classification models |
| Data Processing | Pandas | Tabular data processing, where used |
| Numerical Computing | NumPy | Numerical operations, where used |
| Model Persistence | Pickle-based artifacts | Saving and loading trained models |
| Frontend | HTML, CSS, JavaScript | User interface, where implemented |
| Testing | Django Test Framework and Python tests | Automated testing |
| IDE | Visual Studio Code | Development environment |
| Version Control | Git | Source-code management |
| Repository Hosting | GitHub | Project hosting and version control |

The installed dependency versions should be taken from the project's `requirements.txt` file.

---

## 🏗️ System Architecture

The application follows a typical machine learning web-application workflow.

```text
                   ┌────────────────────────┐
                   │     User / Browser     │
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │    Django Web Layer    │
                   │ Views and Form Handling│
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   Input Validation     │
                   │ and Preprocessing      │
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   Trained ML Model     │
                   │     Random Forest      │
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   Prediction Result    │
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │    Django Web Page     │
                   └────────────────────────┘
```

### Architecture Components

**Presentation Layer**

Provides the browser-based interface for entering supported information and viewing results.

**Application Layer**

Handles HTTP requests, application logic, and communication between the interface and prediction components.

**Preprocessing Layer**

Applies the feature transformations expected by the trained model, where required.

**Machine Learning Layer**

Loads the persisted model and generates predictions.

**Evaluation Layer**

Supports the offline training and evaluation process used during model development.

The diagram is a conceptual overview. The exact implementation should be confirmed against the application's current views, forms, and prediction code.

---

## 🧠 Machine Learning Workflow

The project follows these general machine learning stages.

### Step 1: Data Loading

Load the labeled dataset containing patient health attributes and the target outcome.

### Step 2: Data Inspection

Inspect the dataset's structure, feature types, target distribution, and data quality.

### Step 3: Data Preprocessing

Prepare the input features for model training. This may include handling missing values, encoding variables, or scaling features as required by the selected model.

### Step 4: Data Splitting

Separate the available data into appropriate training and evaluation subsets.

### Step 5: Model Training

Train candidate classification models using the training data.

### Step 6: Cross-Validation

Evaluate candidate models using cross-validation to obtain a more robust estimate of their performance.

### Step 7: Model Selection

Compare model performance using appropriate evaluation metrics.

### Step 8: Probability Calibration

Compare Brier scores before and after calibration where calibration is supported by the training pipeline.

### Step 9: Final Evaluation

Evaluate the selected model on held-out test data.

### Step 10: Model Persistence

Save the trained model and any required preprocessing artifacts.

### Step 11: Web Integration

Load the saved model in the Django application and connect it to the prediction workflow.

### Step 12: Automated Testing

Run the test suite to check application behavior and catch regressions.

### Important Evaluation Principle

The held-out test set should not be used repeatedly to choose models, tune hyperparameters, or select calibration settings. Doing so can produce overly optimistic estimates of generalization performance.

---

## 📊 Dataset

The original project documentation identifies the **UCI Heart Disease Cleveland dataset**. Verify the exact source, local dataset file, preprocessing steps, feature definitions, and target encoding against the current training code before final submission.

### Dataset Summary

| Property | Description |
|---|---|
| Domain | Healthcare |
| Data Type | Structured tabular data |
| Learning Task | Supervised classification |
| Input | Supported patient health attributes |
| Target | Heart disease outcome, as defined by the dataset |
| Records in Latest Recorded Training Run | 297 |
| Intended Use | Educational machine learning experimentation |

### Dataset Considerations

- Document the original dataset source.
- Explain the target variable and its encoding.
- Identify missing values and explain how they are handled.
- Document any filtering or preprocessing that changes the record count.
- Explain how the training, validation, and test sets are created.
- Avoid describing the dataset as real-time hospital data unless that is verified.
- Avoid claiming that the dataset represents every patient population.

The dataset is relatively small. Therefore, the model's performance may differ when applied to other populations or healthcare settings.

---

## 📈 Model Evaluation

The latest recorded local training experiment selected a **Random Forest classifier**.

The results below reflect the recorded experiment. Re-run the training pipeline and confirm the generated evaluation artifacts before treating these values as the final results for a submission or publication.

### Cross-Validation Results

| Metric | Recorded Result |
|---|---:|
| ROC-AUC | 0.889 |
| Brier Score Before Calibration | 0.1405 |
| Brier Score After Calibration | 0.1349 |

The lower Brier score after calibration indicates improved probability-error performance in the recorded experiment. It does not, by itself, establish that individual predictions are clinically reliable.

### Held-Out Test Results

| Metric | Recorded Result |
|---|---:|
| Accuracy | 0.833 |
| Precision | 0.909 |
| Recall | 0.714 |
| F1-Score | 0.800 |
| ROC-AUC | 0.949 |
| Brier Score | 0.107 |

### Understanding the Evaluation Metrics

**Accuracy**

The proportion of evaluated predictions that were correct.

**Precision**

The proportion of positive predictions that were correct.

**Recall**

The proportion of actual positive cases identified by the model.

**F1-Score**

The harmonic mean of precision and recall.

**ROC-AUC**

Measures how effectively the model ranks positive cases above negative cases across different classification thresholds.

**Brier Score**

Measures the squared difference between predicted probabilities and observed outcomes. Lower values generally indicate better probability predictions on the evaluated data.

### Interpretation

The recorded experiment shows promising classification performance on its evaluation data. However, several factors must be considered:

- The dataset is relatively small.
- Results depend on the evaluation split and class distribution.
- Precision and recall depend on the decision threshold.
- A high ROC-AUC does not establish clinical usefulness.
- Calibration performance should be evaluated on data not used to fit the calibration process.
- Independent external validation would be required to investigate generalization to other populations.

**These are experimental machine learning results, not evidence of clinical validation or diagnostic accuracy in real-world medical practice.**

---

## 🔍 Model Explainability

Model explainability can help developers investigate which input features influence a model's predictions.

Possible approaches for a tree-based model include:

- Feature importance analysis.
- SHAP-based explanations, if implemented in the current codebase.
- Controlled feature-perturbation experiments.
- Reviewing prediction behavior across different input ranges.

An explanation describes aspects of model behavior; it does not establish that a prediction is correct or that a feature causes heart disease.

Only describe a particular explainability technique as an implemented feature if its code and output have been verified.

---

## 📂 Project Structure

The following is a representative overview of the repository. Some files and directories may differ in the current version.

```text
CardioNova-Health/
│
├── heart_disease/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── prediction/
│   ├── migrations/
│   ├── templates/
│   │   └── prediction/
│   ├── static/
│   │   └── prediction/
│   ├── tests.py
│   └── ...
│
├── model/
│   ├── heart_disease_model.pkl
│   ├── scaler.pkl
│   ├── model_comparison.csv
│   ├── model_info.json
│   └── ...
│
├── dataset/
│   └── ...
│
├── manage.py
├── train_model.py
├── requirements.txt
├── .gitignore
└── README.md
```

### Important Files

| File or Directory | Purpose |
|---|---|
| `manage.py` | Django management commands |
| `heart_disease/` | Django project configuration |
| `prediction/` | Prediction application code, templates, tests, and migrations |
| `model/` | Saved model and related artifacts |
| `train_model.py` | Model training script, if present at the repository root |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Files and directories excluded from Git |
| `README.md` | Project documentation |

Confirm the exact paths in VS Code before using this structure as a definitive file listing.

---

## ⚙️ Installation and Setup

Follow these steps to run the project locally on Windows.

### Prerequisites

Install the following:

- Python version compatible with the project's dependencies.
- Git.
- Visual Studio Code.
- PowerShell or another terminal.

### Step 1: Clone the Repository

Open PowerShell and run:

```powershell
git clone https://github.com/manishyadav-aiml/CardioNova-Health.git
```

Move into the project directory:

```powershell
cd CardioNova-Health
```

### Step 2: Create a Virtual Environment

```powershell
python -m venv venv
```

### Step 3: Activate the Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, temporarily allow scripts for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again:

```powershell
.\venv\Scripts\Activate.ps1
```

### Step 4: Install Dependencies

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the project dependencies:

```powershell
pip install -r requirements.txt
```

Use the versions declared in `requirements.txt`. Saved Scikit-learn model artifacts may not be compatible with arbitrary versions of Scikit-learn.

### Step 5: Configure Environment Variables

Check `heart_disease/settings.py` and any environment-variable examples in the repository to determine which configuration values are required.

If the application uses a `.env` file, create one locally and provide the required variables.

For example:

```env
SECRET_KEY=replace-with-a-secure-local-secret
DEBUG=True
```

These are illustrative values, not a complete configuration specification.

**Do not commit `.env` files, production secrets, passwords, or private credentials to GitHub.**

### Step 6: Apply Database Migrations

```powershell
python manage.py migrate
```

If this command fails, inspect the migration history and database state before attempting corrective actions. Do not delete your existing database to work around a migration error.

### Step 7: Run Django System Checks

```powershell
python manage.py check
```

Resolve any reported configuration or application errors before continuing.

---

## ▶️ Running the Application

Start the Django development server:

```powershell
python manage.py runserver
```

Open the local address displayed in the terminal. The default is:

```text
http://127.0.0.1:8000/
```

If the application uses a different route for its main page, navigate to the appropriate URL defined in the project's URL configuration.

To stop the development server, press:

```text
Ctrl + C
```

### Development Server Notice

Django's built-in development server is intended for local development and testing. It should not be used as the production deployment server.

---

## 🤖 Training the Model

The repository includes a model training script.

If the script supports quick training, run:

```powershell
python train_model.py --quick
```

To inspect the supported command-line options, run:

```powershell
python train_model.py --help
```

Training may update the saved model and evaluation artifacts. Review the generated files and compare the new metrics with the documented results before committing changes.

### Recommended Training Practices

- Use a documented dataset version.
- Keep preprocessing consistent between training and prediction.
- Avoid data leakage.
- Separate model selection from final evaluation.
- Evaluate multiple relevant metrics.
- Record the random seed and split strategy where applicable.
- Preserve reproducible training instructions.
- Confirm that the model artifacts match the installed library versions.

---

## 🧪 Running Tests

The latest recorded local test run completed successfully:

```text
Ran 71 tests in 66.308s

OK
```

To run the Django test suite:

```powershell
python manage.py test
```

The test suite should be rerun after significant changes to the application, model integration, templates, database logic, or dependencies.

### Check Migration Consistency

Run:

```powershell
python manage.py makemigrations --check --dry-run
```

The last recorded check returned:

```text
No changes detected
```

This indicates that Django did not detect new model changes requiring migrations. It does **not** prove that all migrations can be applied successfully to a fresh database.

### Fresh-Database Migration Verification

Before deployment:

1. Create a separate temporary test database.
2. Configure a test environment to use that database.
3. Apply all migrations from the beginning.
4. Run the application checks and relevant tests.
5. Verify that the expected database tables exist.
6. Keep the existing development database unchanged.

This verification is especially important before describing the project as deployment-ready.

---

## 🔐 Security and Privacy

Security is important for any application that handles health-related information.

The project includes automated tests and security-related template fixes. However, these measures alone do not prove that the entire application is secure.

### Recommended Security Practices

- Keep secret keys and credentials outside version control.
- Disable Django debug mode in production.
- Configure appropriate allowed hosts.
- Use HTTPS in a deployed environment.
- Validate user-submitted input.
- Apply authentication and authorization checks where required.
- Avoid exposing sensitive information in logs or error messages.
- Keep dependencies updated.
- Review error handling and session management.
- Test database migrations and backup procedures before deployment.
- Avoid collecting or retaining unnecessary personal or health information.

### Sensitive Information

Never publish real patient records, passwords, secret keys, database credentials, or private configuration files in the public repository.

Do not claim regulatory compliance, such as HIPAA compliance, unless the application has been independently assessed and the claim is justified.

---

## ⚠️ Limitations

The project has several limitations that should be considered when interpreting its results.

### 1. Limited Dataset Size

The latest recorded training experiment used 297 records. This is a small dataset for establishing robust performance across diverse populations.

### 2. Dataset Representativeness

The dataset may not represent all age groups, demographic groups, clinical settings, or patient populations.

### 3. No Established Clinical Validation

The model has not been established as suitable for clinical diagnosis or treatment decisions.

### 4. Potential Data Bias

Sampling, measurement, and labeling practices may affect the patterns learned by the model.

### 5. Probability Uncertainty

A probability output is not automatically a clinically meaningful risk estimate. Calibration should be evaluated carefully and independently.

### 6. Generalization

Good results on one test split do not guarantee similar performance on independent external datasets.

### 7. Deployment Readiness

Production deployment requires additional verification of database migrations, configuration, security, monitoring, and operational reliability.

### 8. Model Maintenance

Changes in the data distribution may affect model performance over time. A production system would require monitoring and a documented model-update process.

The application should be treated as an educational machine learning demonstration, not a clinical decision-making system.

---

## 🚀 Future Improvements

Potential improvements include:

- Evaluate the model on an independent external dataset.
- Strengthen the reproducibility of the training pipeline.
- Document the complete dataset provenance and preprocessing process.
- Add appropriate model-explainability methods.
- Improve probability calibration analysis.
- Evaluate decision thresholds using documented criteria.
- Add experiment tracking and model versioning.
- Add continuous integration for automated tests.
- Improve accessibility and responsive interface design.
- Document deployment configuration.
- Add monitoring for input quality and model performance if deployed.
- Conduct a security review before accepting sensitive information.
- Verify the complete database migration process against a fresh database.

These items are proposed future improvements. They should not be interpreted as features already implemented.

---

## 💼 Skills Demonstrated

| Skill | Application in the Project |
|---|---|
| Python Programming | Building application and machine learning components |
| Machine Learning | Developing a supervised classification workflow |
| Scikit-learn | Training and evaluating classification models |
| Model Evaluation | Interpreting precision, recall, F1-score, ROC-AUC, and Brier score |
| Data Processing | Preparing structured data for model training |
| Django | Integrating model functionality into a web application |
| Model Persistence | Saving and loading trained model artifacts |
| Software Testing | Running automated tests and investigating failures |
| Debugging | Resolving dependency and model-compatibility problems |
| Git and GitHub | Maintaining source control and a public project repository |
| Responsible AI | Documenting limitations and avoiding unsupported clinical claims |

---

## 🎓 Academic and Portfolio Relevance

CardioNova Health is suitable for presentation as a final-year BTech CSE project, provided its implementation, documentation, and evaluation are verified.

For academic evaluation, the project can demonstrate:

- A defined problem statement.
- A documented machine learning methodology.
- Dataset preparation and model evaluation.
- Web application integration.
- Automated testing.
- Discussion of limitations and future work.

For an AI/ML portfolio, the strongest evidence includes the reproducible training pipeline, clearly documented evaluation metrics, working application, meaningful tests, and the ability to explain technical decisions.

A strong project presentation should distinguish implemented functionality from planned improvements and experimental results from clinically validated evidence.

---

## 👨‍💻 Author

**Manish Yadav**

Final-Year BTech Computer Science and Engineering Student

**Areas of Interest**
- Artificial Intelligence
- Machine Learning
- Python Development
- Data Science
- Web Application Development

### GitHub

**Profile:**  
https://github.com/manishyadav-aiml

**Project Repository:**  
https://github.com/manishyadav-aiml/CardioNova-Health

---

## 📜 License

Add the project's applicable license here.

If the repository does not yet contain a `LICENSE` file, choose an appropriate license before claiming that the project is open source. Do not assume that public availability on GitHub automatically grants permission to reuse the code.

---

## ⚖️ Disclaimer

CardioNova Health is an educational and portfolio project. It is not intended to diagnose, treat, cure, or prevent any disease.

Predictions generated by this application must not be used as the sole basis for medical decisions. Always consult a qualified healthcare professional for medical evaluation and advice.

The reported model metrics are experimental results from a limited dataset. They do not establish clinical effectiveness, safety, or generalization to real-world medical populations.