export const DEFAULT_LOOKUPS = {
  incomeCategories: [
    "Salary-Primary","Salary-Spouse","Bonus","Rental Income","Business/Side Hustle",
    "Interest","Dividends","Capital Gains","Other"
  ],
  expenseCategories: [
    "EMI-Home Loan","EMI-Personal Loan","EMI-Plot Loan","EMI-Car/Bike Loan",
    "Credit Card Payment","Groceries","Dining Out","Utilities-Electricity","Utilities-Water",
    "Utilities-Internet/Mobile","Fuel/Transport","Taxi/Metro","House Help","Child Education/Fees",
    "Healthcare-Medicine","Healthcare-Doctor","Insurance-Health","Insurance-Life","Insurance-Vehicle",
    "Shopping","Entertainment","Travel","Subscriptions","Gifts","Taxes","Miscellaneous"
  ],
  assetTypes: [
    { name: "Bank Account", liquid: true },
    { name: "Fixed Deposit", liquid: false },
    { name: "EPF/PPF", liquid: false },
    { name: "Mutual Fund", liquid: true },
    { name: "Stock", liquid: true },
    { name: "Gold", liquid: true },
    { name: "Property", liquid: false },
    { name: "Crypto", liquid: true },
    { name: "Other", liquid: false }
  ],
  liabilityTypes: ["Home Loan","Personal Loan","Plot Loan","Car/Bike Loan","Credit Card","Education Loan","Other"],
  investmentCategories: [
    "Investments-SIP: Motilal Oswal Midcap",
    "Investments-SIP: Bandan Small Cap",
    "Investments-SIP: ICICI Pru BAF",
    "Investments-SIP: Nippon Small Cap",
    "Investments-SIP: Motial Gold And Silver Fund",
    "Investments-Direct Stocks",
    "Investments-Gold",
    "Investment - DownPayments"
  ]
};
