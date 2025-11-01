#!/bin/bash
# Quick PostgreSQL access script for Runway Finance

export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

echo "PostgreSQL Quick Access"
echo "======================"
echo ""
echo "Choose an option:"
echo "1. Interactive psql session"
echo "2. List all databases"
echo "3. List all tables in runway_finance"
echo "4. Query users"
echo "5. Query accounts"
echo "6. Query transactions (last 10)"
echo "7. Show database stats"
echo "8. Custom SQL query"
echo ""
read -p "Enter option (1-8) or 'q' to quit: " choice

case $choice in
    1)
        echo "Connecting to runway_finance..."
        echo "Tip: Type '\q' to exit, '\dt' to list tables, '\\d table_name' to describe table"
        psql -d runway_finance
        ;;
    2)
        psql -d postgres -c "\l"
        ;;
    3)
        psql -d runway_finance -c "\dt"
        ;;
    4)
        psql -d runway_finance -c "SELECT * FROM users;"
        ;;
    5)
        psql -d runway_finance -c "SELECT account_id, account_name, account_type, balance FROM accounts;"
        ;;
    6)
        psql -d runway_finance -c "SELECT transaction_id, date, merchant_canonical, amount, category FROM transactions ORDER BY date DESC LIMIT 10;"
        ;;
    7)
        echo "Database Stats:"
        echo "==============="
        psql -d runway_finance -c "SELECT 'users' as table_name, COUNT(*) as count FROM users UNION ALL SELECT 'transactions', COUNT(*) FROM transactions UNION ALL SELECT 'accounts', COUNT(*) FROM accounts UNION ALL SELECT 'merchants', COUNT(*) FROM merchants;"
        ;;
    8)
        read -p "Enter your SQL query: " query
        psql -d runway_finance -c "$query"
        ;;
    q)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option"
        ;;
esac

