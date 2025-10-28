# Auto-Launch Dashboard Feature

## Overview
The transaction analysis pipeline now **automatically launches the Streamlit dashboard** in your browser after processing transactions!

## What Changed

### Automatic Dashboard Launch
When you run `python3 main.py`, the pipeline will:
1. Process your transaction files
2. Generate CSV and JSON outputs
3. **Automatically open the dashboard in your browser** 🚀

No more manual commands needed!

## Usage

### Default Behavior (Auto-Launch)
```bash
python3 main.py
```
This will:
- Process `data/Transactions.csv`
- Launch the dashboard automatically
- Open your browser to view the results

### Control Options

#### Skip Dashboard
If you only want to process files without the dashboard:
```bash
python3 main.py --no-dashboard
```

#### Dashboard Only
Launch just the dashboard with previously processed data:
```bash
python3 main.py --dashboard-only
```

### All Processing Options
```bash
# Process and auto-launch dashboard (default)
python3 main.py

# Process specific file and auto-launch dashboard
python3 main.py data/MyFile.csv

# Process multiple files and auto-launch dashboard
python3 main.py file1.csv file2.csv file3.txt

# Process without dashboard
python3 main.py --no-dashboard

# Only show dashboard (no processing)
python3 main.py --dashboard-only

# Process all CSVs and auto-launch dashboard
python3 main.py --csv-only

# Process all files and auto-launch dashboard
python3 main.py --all
```

## How It Works

### Implementation Details

1. **Dashboard Launch Function** (`launch_dashboard()`)
   - Uses `subprocess.run()` to execute Streamlit
   - Passes the processed CSV file path to the dashboard
   - Handles errors gracefully (missing Streamlit, keyboard interrupt)

2. **Command-Line Arguments**
   - `--no-dashboard`: Skip dashboard launch
   - `--dashboard-only`: Only launch dashboard, skip processing

3. **Smart Defaults**
   - Dashboard launches by default after processing
   - User can press `Ctrl+C` to stop the dashboard
   - Clear messages guide the user

### Code Changes

**Files Modified:**
- `main.py` - Added auto-launch functionality
  - New function: `launch_dashboard(csv_path)`
  - New arguments: `--no-dashboard`, `--dashboard-only`
  - Updated `run()` to return the output CSV path
  - Integrated dashboard launch after processing

**Dependencies:**
- No new dependencies required
- Uses built-in `subprocess` module
- Requires Streamlit (already in requirements.txt)

## Error Handling

### Streamlit Not Installed
If Streamlit is not installed, you'll see:
```
ERROR - Streamlit not found. Install it with: pip3 install streamlit
```

### Dashboard Interrupted
Press `Ctrl+C` to stop:
```
INFO - Dashboard stopped by user.
```

### No Processed Data
If you run `--dashboard-only` without data:
```
ERROR - No processed data found at data/cleaned/parsed_transactions_latest.csv
ERROR - Run without --dashboard-only to process files first.
```

## User Experience Flow

### Typical Workflow
1. User runs: `python3 main.py`
2. Pipeline processes transactions
3. Logs show progress
4. Dashboard automatically opens in browser
5. User views interactive visualizations
6. User presses `Ctrl+C` when done

### Dashboard-Only Workflow
1. User has already processed data
2. User runs: `python3 main.py --dashboard-only`
3. Dashboard opens immediately
4. Shows previously processed data

### No-Dashboard Workflow
1. User wants batch processing only
2. User runs: `python3 main.py --no-dashboard`
3. Processing completes
4. Helpful message shows how to launch dashboard later

## Benefits

### For End Users
- ✅ **One Command**: No need to remember Streamlit commands
- ✅ **Instant Visualization**: See results immediately
- ✅ **Flexible**: Can skip dashboard if needed
- ✅ **Quick View**: `--dashboard-only` for quick data review

### For Development
- ✅ **Better UX**: Seamless workflow
- ✅ **Backward Compatible**: All existing functionality preserved
- ✅ **Well Documented**: Clear help messages and docs
- ✅ **Error Handling**: Graceful degradation

## Testing

All functionality tested and working:
- ✅ Auto-launch works
- ✅ `--no-dashboard` flag works
- ✅ `--dashboard-only` flag works
- ✅ Error messages clear and helpful
- ✅ All existing tests pass

## Examples

### Example 1: Quick Analysis
```bash
$ python3 main.py
2025-10-25 23:49:38 - INFO - Processing default file...
2025-10-25 23:49:38 - INFO - Files to process: 1
2025-10-25 23:49:38 - INFO - Total transactions: 438
2025-10-25 23:49:38 - INFO - Processing complete!
2025-10-25 23:49:38 - INFO - Launching dashboard...
2025-10-25 23:49:38 - INFO - Dashboard will open in your browser shortly.

  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

### Example 2: Batch Processing
```bash
$ python3 main.py --no-dashboard file1.csv file2.csv
2025-10-25 23:50:00 - INFO - Processing file: file1.csv
2025-10-25 23:50:00 - INFO - Processing file: file2.csv
2025-10-25 23:50:01 - INFO - Processing complete!
2025-10-25 23:50:01 - INFO - Dashboard launch skipped (--no-dashboard flag used)
2025-10-25 23:50:01 - INFO - To view dashboard later, run:
2025-10-25 23:50:01 - INFO -   python3 main.py --dashboard-only
```

### Example 3: Review Previous Data
```bash
$ python3 main.py --dashboard-only
2025-10-25 23:51:00 - INFO - Launching dashboard...

  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

## Documentation Updates

Updated documentation:
- ✅ README.md - Added auto-launch feature to features list
- ✅ QUICK_START.md - Updated basic usage examples
- ✅ main.py docstring - Updated usage examples
- ✅ --help output - Shows new options

## Future Enhancements

Potential improvements:
- Add `--port` option to specify Streamlit port
- Add `--browser` option to choose browser
- Add `--no-browser` to run dashboard without opening browser
- Support custom dashboard configurations

## Conclusion

The auto-launch dashboard feature makes the transaction analysis pipeline even more user-friendly. Users can now get from raw data to interactive visualizations with a single command!

**Just run `python3 main.py` and you're done!** 🎉
