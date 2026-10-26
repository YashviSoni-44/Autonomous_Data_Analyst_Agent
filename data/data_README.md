# Test Datasets Directory (`data/`)

This directory contains test datasets across multiple domains and data qualities designed for testing the **Autonomous Data Analyst Agent**.

---

## Summary Matrix

| Dataset Filename | Format | Compatibility | Data Quality / Type | Domain & Description | Key Edge Cases / Characteristics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`clean_saas_metrics.csv`** | `.csv` | **Compatible** (200 OK) | Clean | SaaS Subscription & Churn | Strict ISO dates, integer NPS (1-10), clean MRR, subscription tiers |
| **`clean_multi_sheet_enterprise.xlsx`** | `.xlsx` | **Compatible** (200 OK) | Clean (Multi-Sheet) | Enterprise Retail & Supply Chain | 3 relational sheets (`dim_customers`, `dim_products`, `fact_orders`) |
| **`mixed_healthcare_clinical_trials.csv`** | `.csv` | **Compatible** (200 OK) | Mixed | Clinical Trial Bio-markers & Outcomes | Mixed booleans (`TRUE`/`FALSE`, `yes`/`no`, `1`/`0`), timezone offsets, dosage units |
| **`mixed_marketing_campaigns.csv`** | `.csv` | **Compatible** (200 OK) | Mixed | Ad Campaign Performance | Percentages as strings (`5.00%`), wide dynamic numeric scale (spend vs impressions) |
| **`dirty_ecommerce_returns.csv`** | `.csv` | **Compatible** (200 OK) | Dirty | E-commerce RMA & Returns | Inconsistent nulls (`N/A`, `null`, `?`, `-999`), dirty dates, negative prices, outlier qty |
| **`dirty_payroll_ledger.xlsx`** | `.xlsx` | **Compatible** (200 OK) | Dirty | HR & Accounting Payroll Ledger | Blank spacer rows, Excel formula text (`=D5+E5`, `#VALUE!`), accounting brackets `(450.00)` |
| **`sample_dataset.csv`** *(existing)* | `.csv` | **Compatible** (200 OK) | Clean | Retail Orders | Baseline reference dataset with sample orders |
| **`autonomous_data_analyst_dirty_sales.csv`** *(existing)* | `.csv` | **Compatible** (200 OK) | Dirty | Large Scale Sales Ledger | Large dirty CSV dataset for stress-testing profiling & ingestion |
| **`autonomous_data_analyst_dirty_sales.xlsx`** *(existing)* | `.xlsx` | **Compatible** (200 OK) | Dirty | Large Scale Sales Ledger | Excel counterpart of dirty sales ledger |
| **`incompatible_web_events.json`** | `.json` | **Incompatible** (400) | Nested JSON Objects | Web Analytics & Clickstream | Tests backend file-type rejection for nested JSON arrays |
| **`incompatible_iot_telemetry.parquet`** | `.parquet` | **Incompatible** (400) | Columnar Binary | Industrial IoT Sensor Readings | Tests backend rejection for Apache Parquet files |
| **`incompatible_genomics_expression.tsv`** | `.tsv` | **Incompatible** (400) | Tab-Separated Values | Bioinformatics Gene Expression | Tests rejection for non-comma separated text formats |
| **`incompatible_server_access.txt`** | `.txt` / Log | **Incompatible** (400) | Unstructured Log Lines | Nginx / Apache Access Logs | Tests rejection for plain text logs |
| **`incompatible_tax_invoices.xml`** | `.xml` | **Incompatible** (400) | Hierarchical Markup | Corporate Tax & Invoicing Batch | Tests rejection for XML documents |
| **`incompatible_quarterly_report.pdf`** | `.pdf` | **Incompatible** (400) | Binary Document | Executive Briefing PDF | Tests rejection for document file uploads |

---

## Detailed Dataset Specifications

### 1. `clean_saas_metrics.csv` (Compatible · Clean)
- **Use Case:** Test baseline statistical profiling, retention analysis, MRR distribution, and SQL aggregations without data cleaning overhead.
- **Columns:** `subscription_id`, `customer_id`, `company_name`, `plan_tier`, `mrr_usd`, `billing_cycle`, `signup_date`, `renewal_date`, `is_active`, `churn_reason`, `seats_purchased`, `nps_score`
- **Sample Queries to Test:**
  - *"What is the total and average MRR grouped by plan tier?"*
  - *"Calculate customer churn rate and identify top reasons for cancellation."*

### 2. `clean_multi_sheet_enterprise.xlsx` (Compatible · Clean Multi-Table)
- **Use Case:** Tests multi-sheet Excel ingestion into distinct DuckDB tables (`dim_customers`, `dim_products`, `fact_orders`) and multi-table relational joins.
- **Sheets:**
  1. `dim_customers`: Customer details, industry, country, account tiers.
  2. `dim_products`: Product catalog, unit cost, unit prices.
  3. `fact_orders`: Transactional orders with foreign keys `customer_id` and `product_id`.
- **Sample Queries to Test:**
  - *"Which industry generated the highest revenue after applying discounts?"*
  - *"Calculate gross profit margin per product category across all orders."*

### 3. `dirty_ecommerce_returns.csv` (Compatible · Dirty)
- **Use Case:** Tests agent data-cleaning robustness, anomaly detection, type coercion, and outlier handling.
- **Included Anomalies:**
  - **Inconsistent missing values:** `""`, `"N/A"`, `"null"`, `"?"`, `"-999"`, `"None"`
  - **Whitespace and Casing:** `"  Defective item  "`, `"ELECTRONICS"`, `" apparel "`
  - **Erroneous / Outlier Values:** Price `-$45.00`, customer rating `999` and `-5`, return quantity `50000`
  - **Malformed / Mixed Dates:** `"2026-01-10"`, `"12/01/2026"`, `"Jan 16, 2026"`, `"2026-02-30"` (impossible calendar date)
  - **Currency String Artifacts:** `"$1,249.99"`, `"$49.99"`, `"399.00"`
  - **Duplicate primary keys:** Duplicate `RET-001` entry

### 4. `dirty_payroll_ledger.xlsx` (Compatible · Dirty Excel)
- **Use Case:** Tests common real-world spreadsheet issues.
- **Included Anomalies:**
  - Blank spacer rows between department blocks.
  - Formula string representations stored as text (`"=D5+E5"`).
  - Excel formula error values (`"#VALUE!"`).
  - Accounting format brackets for negative deductions: `"(450.00)"`.
  - Trailing summary totals row (`"TOTAL / SUMMARY"`).

### 5. `mixed_healthcare_clinical_trials.csv` (Compatible · Mixed)
- **Use Case:** Tests parsing of heterogeneous data types, mixed boolean representations, and textual clinical notes with punctuation.
- **Included Mixed Types:**
  - Mixed booleans: `"TRUE"`, `"FALSE"`, `"yes"`, `"no"`, `"1"`, `"0"`, `"Y"`, `"N"`.
  - Timestamps with timezone offsets: `"2026-01-05T08:30:00Z"`, `"2026-01-06T09:15:20-05:00"`.
  - Text units: `"50mg"`, `"100mg"`, `"Placebo"`.
  - Percentages formatted as text: `"88.5%"`, `"92.1%"`.
  - Free-form text fields containing internal commas and quotes.

### 6. `mixed_marketing_campaigns.csv` (Compatible · Mixed)
- **Use Case:** Tests campaign funnel analysis, multi-channel attribution, and conversion efficiency metrics.
- **Columns:** `campaign_id`, `campaign_name`, `channel`, `target_device`, `start_date`, `end_date`, `budget_usd`, `actual_spend`, `impressions`, `clicks`, `conversions`, `ctr_pct`, `cpc_usd`, `roi_multiplier`.

---

## Incompatible Format Datasets (Validation & Error Handling Testing)

These datasets verify that the application properly validates uploads and returns clear `400 Bad Request` messages (*"Unsupported file format. Please upload a .csv or .xlsx / .xls file."*):

1. **`incompatible_web_events.json`** (`.json`)
2. **`incompatible_iot_telemetry.parquet`** (`.parquet`)
3. **`incompatible_genomics_expression.tsv`** (`.tsv`)
4. **`incompatible_server_access.txt`** (`.txt`)
5. **`incompatible_tax_invoices.xml`** (`.xml`)
6. **`incompatible_quarterly_report.pdf`** (`.pdf`)
