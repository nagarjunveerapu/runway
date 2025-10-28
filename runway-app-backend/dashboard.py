"""Small Streamlit dashboard to visualize parsed transactions.

Run: streamlit run dashboard.py -- --csv data/cleaned/parsed_transactions.csv
"""
import streamlit as st
import pandas as pd
import argparse


def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='data/cleaned/parsed_transactions.csv')
    args = parser.parse_args()

    df = load_data(args.csv)

    st.title('Runway — Transactions Dashboard')

    # Filter to only count withdrawals as spend
    # Check if we have withdrawal column (from CSV parser)
    if 'withdrawal' in df.columns:
        withdrawals_df = df[df['withdrawal'] > 0].copy()
        total_spend = withdrawals_df['withdrawal'].sum()
        upi_spend = withdrawals_df[withdrawals_df['channel']=='UPI']['withdrawal'].sum()
    elif 'transaction_type' in df.columns:
        withdrawals_df = df[df['transaction_type'] == 'withdrawal'].copy()
        total_spend = withdrawals_df['amount'].sum()
        upi_spend = withdrawals_df[withdrawals_df['channel']=='UPI']['amount'].sum()
    else:
        # Fallback for text-parsed transactions
        withdrawals_df = df
        total_spend = df['amount'].sum()
        upi_spend = df[df['channel']=='UPI']['amount'].sum()

    st.metric('Total spend', f"₹{total_spend:,.2f}")
    upi_pct = (upi_spend/total_spend*100) if total_spend else 0
    st.metric('UPI % of spend', f"{upi_pct:.1f}%")
    st.metric('Number transactions', len(df))
    st.metric('Withdrawal transactions', len(withdrawals_df))

    st.header('Spend by Category')
    if 'withdrawal' in df.columns:
        cat = withdrawals_df.groupby('category')['withdrawal'].sum().reset_index().rename(columns={'withdrawal': 'amount'})
    elif 'transaction_type' in df.columns:
        cat = withdrawals_df.groupby('category')['amount'].sum().reset_index()
    else:
        cat = df.groupby('category')['amount'].sum().reset_index()
    st.bar_chart(cat.set_index('category'))

    st.header('Top Merchants')
    if 'withdrawal' in df.columns:
        topm = withdrawals_df.groupby('merchant')['withdrawal'].sum().sort_values(ascending=False).head(10)
    elif 'transaction_type' in df.columns:
        topm = withdrawals_df.groupby('merchant')['amount'].sum().sort_values(ascending=False).head(10)
    else:
        topm = df.groupby('merchant')['amount'].sum().sort_values(ascending=False).head(10)
    st.bar_chart(topm)

    st.header('Recurring Payments')
    if 'recurring' in df.columns:
        rec = df[df['recurring']].groupby('merchant')['recurrence_count'].sum().reset_index().sort_values('recurrence_count', ascending=False)
        st.table(rec)
    else:
        st.write('No recurring data available')


if __name__ == '__main__':
    main()
