Health Conditions Driving Employer Health Care Costs, 2025

Cancer: 88%
Musculoskeletal: 71%
Cardiovascular: 35%
Diabetes: 21%
Mental health: 18%
Obesity: 15%
Maternity: 15%
Autoimmune: 11%
Gastroenterology/digestive issues: 7%
Neurology: 5%
High-risk maternity: 5%
HIV/AIDS: 1%
Other: 5%

---

---

---


Inpatient Utilization, Q2 2024 - Q1 2025 

Inpatient (IP) Utilization	Q2 2024 - Q1 2025	Percent Change from Q2 2023 - Q1 2024

IP % admitted from Emergency Department (ED)	68%	1.3%

IP % not admitted from ED	32%	-2.7%

Average length of stay (days)	5.49	-0.7%

Mortality rate	2.3%	-4.4%

30-day readmission rate	12.3%	2.2%

Average cost per IP stay	$10,860	4.8%

Average cost per IP day	$1,977	5.5%

---

---

---

# dbt models
What is dbt?

dbt is the industry standard for data transformation. Learn how it can help you transform data and deploy analytics code following software engineering best practices like version control, modularity, portability, CI/CD, and documentation.

dbt is a transformation workflow that helps you get more work done while producing higher quality results. You can use dbt to modularize and centralize your analytics code, while also providing your data team with guardrails typically found in software engineering workflows. Collaborate on data models, version them, and test and document your queries before safely deploying them to production, with monitoring and visibility.

dbt compiles and runs your analytics code against your data platform, enabling you and your team to collaborate on a single source of truth for metrics, insights, and business definitions. This single source of truth, combined with the ability to define tests for your data, reduces errors when logic changes, and alerts you when issues arise.


dbt models are SQL or Python scripts containing SELECT statements and Common Table Expressions (CTEs) that define data transformations within a dbt project, creating tables or views in your data warehouse. They are organized into a project directory and are the core component for transforming data, with the process of running them creating a materialized object in the warehouse. 
Key Characteristics:
Written in SQL or Python: Most models are written in SQL as SELECT statements, but Python models are supported for complex logic or integration with Python libraries. 
Contain Transformational Logic: Models house the code for joining data, applying functions, and cleaning data to make it ready for analysis. 
Materialized into Tables or Views: When you run a dbt model, it creates a new table or view in your data warehouse, such as Snowflake, Redshift, or BigQuery. 
Organized within a dbt Project: Models are .sql or .py files within a dbt project's models directory. 
How They Work:
Define the Logic: A developer writes a SELECT statement that performs transformations on raw data. 
dbt Runs the SQL: When the dbt run command is executed, dbt translates this SELECT statement into CREATE TABLE or CREATE VIEW statements for your specific data warehouse. 
Data is Transformed: Your data is transformed within your data warehouse without ever leaving it. 
Benefits of Using dbt Models: 
Modularity and Reusability: You can build reusable data models, changing the logic in one model and having that change propagate to all downstream models and analyses.
Version Control: dbt models integrate with mature source control processes like branching, pull requests, and code reviews.
Reliable Analytics: They encapsulate complex business logic, preventing the need to copy and paste code and reducing the risk of errors.
Data Quality: You can quickly write and run tests on the data within your models to identify and handle edge cases.


About dbt models

dbt Core and Cloud are composed of different moving parts working harmoniously. All of them are important to what dbt does — transforming data—the 'T' in ELT. When you execute dbt run, you are running a model that will transform your data without that data ever leaving your warehouse.

Models are where your developers spend most of their time within a dbt environment. Models are primarily written as a select statement and saved as a .sql file. While the definition is straightforward, the complexity of the execution will vary from environment to environment. Models will be written and rewritten as needs evolve and your organization finds new ways to maximize efficiency.

SQL is the language most dbt users will utilize, but it is not the only one for building models. Starting in version 1.3, dbt Core and dbt support Python models. Python models are useful for training or deploying data science models, complex transformations, or where a specific Python package meets a need — such as using the dateutil library to parse dates.

Models and modern workflows

The top level of a dbt workflow is the project. A project is a directory of a .yml file (the project configuration) and either .sql or .py files (the models). The project file tells dbt the project context, and the models let dbt know how to build a specific data set. For more details on projects, refer to About dbt projects.

Your organization may need only a few models, but more likely you’ll need a complex structure of nested models to transform the required data. A model is a single file containing a final select statement, and a project can have multiple models, and models can even reference each other. Add to that, numerous projects and the level of effort required for transforming complex data sets can improve drastically compared to older methods.

Learn more about models in SQL models and Python models pages. If you'd like to begin with a bit of practice, visit our Getting Started Guide for instructions on setting up the Jaffle_Shop sample data so you can get hands-on with the power of dbt.

