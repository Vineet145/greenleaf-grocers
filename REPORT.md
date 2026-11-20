# Inventory & Sales Management System with Analytics Dashboard for GreenLeaf Grocers
Project report | Python Developer Internship (Unified Mentor), Project 2

## Abstract
Small retail stores often track stock on paper or scattered spreadsheets, causing stock-outs, expiry losses and billing mistakes. This project delivers a single web application built with Flask and SQLite that manages products, automates billing and stock deduction, raises low-stock and near-expiry alerts, and reports sales analytics with pandas.

## 1. Problem and objectives
Problems: late restocking, unnoticed losses, no view of daily sales or top sellers, billing errors. Objectives: a working web app for product, stock and sales management; automated billing; sales and inventory reports; fewer stock-outs; faster, more accurate billing; data to support purchasing decisions.

## 2. Design
Five normalized tables (users, suppliers, products, sales, sale_items) with primary keys, foreign keys and CHECK constraints (price > 0, stock >= 0). Code is split into modules: routes, database, billing, reports, utils.

## 3. Methodology
1. Database design and ER modelling. 2. Flask backend with hashed passwords (werkzeug) and role checks. 3. Billing as one transaction: validate, save sale, deduct stock. 4. pandas analytics: daily/monthly revenue, top 10 products, category share, slow movers (no sales in 30 days). 5. Validation: reject negative quantities, invalid dates and overselling; friendly error messages. 6. Testing: 15 pytest tests on a separate database.

## 4. Results
The system was tested on generated data (56 products, 650 sales over 120 days). Reports, KPIs, alerts and CSV export work as specified. Tests cover billing totals, discounts, stock deduction, validation, login, roles and CSV import.

## 5. Challenges and learnings
Merging duplicate bill lines, keeping stock correct if validation fails (all checks run before any write), and handling empty date ranges in pandas. Learned full-cycle development: schema design, backend logic, validation, testing, analytics and deployment.

## 6. Future work
7-day sales forecasting, barcode input, email alerts for low stock, Docker deployment.

## Conclusion
The project moves from simple scripts to a complete data-backed application covering database design, backend logic, validation, testing and reporting.
