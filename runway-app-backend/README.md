# Runway: Bank Statement Parser POC

This project is a local, offline proof-of-concept to parse bank statements from **multiple formats** (structured CSV files and unstructured text files), extract structured transactions, clean and normalize them, classify them into categories, and produce analysis outputs including summary reports and a Streamlit dashboard.

## Features

- **Auto-Launch Dashboard**: Dashboard opens automatically in your browser after processing! 🚀
- **Multi-format Support**: Parse both structured CSV files (e.g., exported bank statements) and unstructured text files
- **Batch Processing**: Process multiple files in a single run
- **Flexible Input**: Command-line arguments to specify which files to process
- **Merchant Normalization**: Fuzzy matching to normalize merchant names using rapidfuzz
- **Transaction Classification**: Rule-based categorization into 12+ categories
- **Recurring Transaction Detection**: Automatically identify recurring payments
- **Summary Reports**: JSON summaries with transaction statistics
- **Interactive Dashboard**: Beautiful Streamlit-based visualization

## Requirements

- Python 3.9+
- See `requirements.txt` for dependencies

## Quick Install

```bash
pip3 install -r requirements.txt
```

## Usage

### Basic Usage

Process the default file and **automatically launch the dashboard**:
```bash
python3 main.py
# or
./run.sh
```
The dashboard will open in your browser automatically after processing! 🎉
Press `Ctrl+C` to stop the dashboard when done.

Process a specific CSV file (dashboard launches automatically):
```bash
python3 main.py path/to/your/file.csv
```

Process multiple files at once:
```bash
python3 main.py file1.csv file2.csv file3.txt
```

**Skip the dashboard** if you only want to process files:
```bash
python3 main.py --no-dashboard
```

**Launch only the dashboard** with previously processed data:
```bash
python3 main.py --dashboard-only
```

### Advanced Options

Process all CSV files in the data directory:
```bash
python3 main.py --csv-only
```

Process all .txt and .csv files in the data directory:
```bash
python3 main.py --all
```

Get help:
```bash
python3 main.py --help
```

### Input File Formats

**CSV Format**: Structured bank statement CSVs with columns like:
- Transaction Date / Value Date
- Transaction Remarks
- Withdrawal Amount / Debit
- Deposit Amount / Credit
- Balance

**Text Format**: Unstructured transaction lines like:
```
UPI/518203569642/DHBHDBFS20261/ipo.hdbfsbse@ko/Kotak Mahindra    22940.00
APY_500118843752_Rs.529 fr 072025    529.00
```

## Output Files

The pipeline produces timestamped output files:
- `data/cleaned/parsed_transactions_YYYYMMDD_HHMMSS.csv` - Processed transactions
- `reports/summary_YYYYMMDD_HHMMSS.json` - Transaction summary

Plus "latest" versions for convenience:
- `data/cleaned/parsed_transactions_latest.csv`
- `reports/summary_latest.json`

## Run Streamlit Dashboard

```bash
streamlit run dashboard.py -- --csv data/cleaned/parsed_transactions_latest.csv
```

## Project Layout

```
run_poc/
├─ data/
│  ├─ Transactions.csv           # Input CSV files
│  └─ cleaned/                   # Output directory
├─ reports/                      # Summary JSON files
├─ src/
│  ├─ parser.py                  # Text file parser
│  ├─ csv_parser.py              # CSV file parser (new)
│  ├─ cleaner.py                 # Transaction cleaning
│  ├─ merchant_normalizer.py     # Fuzzy merchant matching
│  ├─ classifier.py              # Category classification
│  ├─ summary.py                 # Summary generation
│  └─ utils.py                   # Utility functions
├─ dashboard.py                  # Streamlit dashboard
├─ main.py                       # Main pipeline orchestrator
├─ run.sh                        # Convenience script
├─ run_tests.sh                  # Test runner
├─ requirements.txt
└─ tests/
   └─ test_parser_and_classifier.py
```

## Output CSV Columns

- `id` (UUID)
- `raw_remark` (original text)
- `remark` (cleaned)
- `amount` (float; absolute value)
- `transaction_type` (withdrawal/deposit for CSV inputs)
- `withdrawal` (float; for CSV inputs)
- `deposit` (float; for CSV inputs)
- `balance` (float; for CSV inputs)
- `channel` (UPI, NEFT, IMPS, ACH, BIL, MMT, NFS, INF, OTHER)
- `merchant` (normalized merchant name)
- `merchant_raw` (extracted merchant substring)
- `category` (Food, Pharmacy, Subscriptions, Bills, Investment, EMI/Loan, Rent, Fuel, Cash Withdrawal, Salary, Transfer, Other)
- `date` (if detectable, else null)
- `recurring` (boolean)
- `recurrence_count` (int)
- `notes` (string)

## Example Output CSV

```csv
id,raw_remark,remark,amount,transaction_type,merchant,category,recurring,recurrence_count
<uuid>,UPI/.../Kotak Mahindra,UPI ... Kotak Mahindra,22940.0,withdrawal,Kotak Mahindra,Transfer,False,1
<uuid>,UPI/Apollo Dia/...,UPI Apollo Dia ...,499.0,withdrawal,Apollo Pharmacy,Pharmacy,True,2
<uuid>,NFS/CASH WDL/...,NFS CASH WDL ...,10000.0,withdrawal,Other,Cash Withdrawal,False,1
```

## Example Summary JSON

```json
{
  "total_transactions": 438,
  "total_spend": 295432.50,
  "upi_transactions_count": 245,
  "top_merchants_by_spend": [...],
  "spend_by_category": {
    "Pharmacy": 499.0,
    "Cash Withdrawal": 30000.0,
    "EMI/Loan": 90781.00
  },
  "recurring_payments": [
    {"merchant": "Apollo Pharmacy", "count": 2}
  ]
}
```

## Extending Merchants and Categories

- Edit `src/merchant_normalizer.py` to add canonical merchants
- Edit `src/classifier.py` to add or change keyword-to-category rules

## ML Classifier Scaffold

`src/classifier.py` contains a scaffold to vectorize text and train a LogisticRegression model if labeled data is provided. The rule-based classifier is used by default for this POC.

## Tests

Run the included pytest tests:

```bash
./run_tests.sh
```

All tests should pass:
- `test_parse_count_and_amounts` - Validates transaction parsing
- `test_channel_detection` - Verifies channel extraction
- `test_merchant_and_category` - Tests merchant normalization

## Processing Pipeline

1. **File Detection**: Automatically detects file type (.csv or .txt)
2. **Parsing**: Uses appropriate parser based on file type
3. **Cleaning**: Normalizes transaction text
4. **Merchant Normalization**: Fuzzy matches merchants to canonical names
5. **Classification**: Assigns categories based on keywords and merchant names
6. **Recurring Detection**: Identifies repeated transactions
7. **Output Generation**: Creates CSV and JSON summary files

## License & Notes

POC code — extend and harden for production use.
