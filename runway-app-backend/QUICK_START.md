# Quick Start Guide

## Installation

```bash
pip3 install -r requirements.txt
```

## Basic Usage

### Process Default File
The simplest way to run - processes `data/Transactions.csv` and **auto-launches the dashboard**:
```bash
python3 main.py
```
or
```bash
./run.sh
```

**The dashboard will automatically open in your browser!** 🚀

Press `Ctrl+C` when you're done viewing the dashboard.

### Process Specific File
```bash
python3 main.py data/MyBankStatement.csv
```
Dashboard launches automatically after processing.

### Process Multiple Files
```bash
python3 main.py file1.csv file2.csv file3.txt
```

### Skip Dashboard Launch
If you only want to process files without launching the dashboard:
```bash
python3 main.py --no-dashboard
```

### View Dashboard Only
To launch just the dashboard with previously processed data:
```bash
python3 main.py --dashboard-only
```

### Batch Processing

Process all CSV files in data directory:
```bash
python3 main.py --csv-only
```

Process all files (CSV and TXT):
```bash
python3 main.py --all
```

## Output

After running, check:
- `data/cleaned/parsed_transactions_latest.csv` - Your processed transactions
- `reports/summary_latest.json` - Transaction summary statistics

## View Results

### CSV Output
```bash
head -20 data/cleaned/parsed_transactions_latest.csv
```

### JSON Summary
```bash
cat reports/summary_latest.json | python3 -m json.tool
```

### Dashboard (Optional)
```bash
streamlit run dashboard.py -- --csv data/cleaned/parsed_transactions_latest.csv
```

## Help

```bash
python3 main.py --help
```

## Run Tests

```bash
./run_tests.sh
```

## Example Workflow

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Place your CSV file in data/ folder
cp ~/Downloads/MyBankStatement.csv data/

# 3. Process it
python3 main.py data/MyBankStatement.csv

# 4. View results
head data/cleaned/parsed_transactions_latest.csv

# 5. Check summary
cat reports/summary_latest.json | python3 -m json.tool

# 6. (Optional) Launch dashboard
streamlit run dashboard.py -- --csv data/cleaned/parsed_transactions_latest.csv
```

## Supported File Formats

### CSV Files
Bank statement CSVs with columns like:
- Transaction Date / Value Date
- Transaction Remarks / Description
- Withdrawal Amount / Debit
- Deposit Amount / Credit
- Balance

### Text Files
Unstructured transaction lines like:
```
UPI/518203569642/DHBHDBFS20261/ipo.hdbfsbse@ko/Kotak Mahindra    22940.00
APY_500118843752_Rs.529 fr 072025    529.00
```

## What It Does

1. Parses transactions from CSV or text files
2. Extracts merchant names from transaction descriptions
3. Normalizes merchant names (e.g., "Apollo Dia" → "Apollo Pharmacy")
4. Categorizes transactions (Food, Pharmacy, Bills, etc.)
5. Detects recurring transactions
6. Generates enriched CSV and JSON summary

## Troubleshooting

**Error: No such file or directory**
- Make sure you're in the `run_poc` directory when running
- Check that your file path is correct

**Error: ModuleNotFoundError**
- Run `pip3 install -r requirements.txt`

**No transactions found**
- Verify your CSV has the expected columns
- Check file encoding (should be UTF-8)

**Tests failing**
- Make sure you're in the project root directory
- Run `./run_tests.sh` from `run_poc/` directory
