// src/components/Add/AddPage.jsx
import React, { useState } from "react";
import { useApp } from "../../context/AppContext";

import AssetInline from "../Inline/AssetInline";
import SIPInline from "../Inline/SIPInline";
import EMIInline from "../Inline/EMIInline";
import ExpenseInline from "../Inline/ExpenseInline";

import AssetsList from "../Assets/AssetsList";
import SIPsList from "../SIPs/SIPsList";
import EMIsList from "../EMIs/EMIsList";
import ExpensesList from "../Expenses/ExpensesList";

function Tile({ title, desc, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full p-5 bg-white border rounded-xl text-left shadow-sm hover:shadow-md active:scale-[0.99] transition-all"
    >
      <div className="font-semibold text-gray-800">{title}</div>
      <div className="text-sm text-gray-500 mt-1">{desc}</div>
    </button>
  );
}

export default function AddPage() {
  const { assets = [], transactions = [] } = useApp();
  const [selected, setSelected] = useState(null);

  const renderCategory = (cat) => {
    switch (cat) {
      case "assets":
        return (
          <>
            <AssetInline />
            <AssetsList />
          </>
        );
      case "sips":
        return (
          <>
            <SIPInline />
            <SIPsList />
          </>
        );
      case "emis":
        return (
          <>
            <EMIInline />
            <EMIsList />
          </>
        );
      case "expenses":
        return (
          <>
            <ExpenseInline />
            <ExpensesList />
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {selected && (
            <button
              onClick={() => setSelected(null)}
              className="px-3 py-1 border rounded text-sm hover:bg-gray-50"
            >
              ←
            </button>
          )}
          <h2 className="text-lg font-semibold">
            {selected ? `Add — ${selected.charAt(0).toUpperCase() + selected.slice(1)}` : "Add Financial Item"}
          </h2>
        </div>
        {!selected && <div className="text-sm text-gray-500">Select a category</div>}
      </div>

      {/* Overview or Inline */}
      {!selected ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Tile title="Asset" desc="SIPs, Stocks, Gold, Property" onClick={() => setSelected("assets")} />
          <Tile title="SIP" desc="Recurring investments / SIPs" onClick={() => setSelected("sips")} />
          <Tile title="EMI" desc="Record monthly EMIs & liabilities" onClick={() => setSelected("emis")} />
          <Tile title="Expense" desc="Bills, groceries, taxes" onClick={() => setSelected("expenses")} />
        </div>
      ) : (
        <div className="space-y-6">{renderCategory(selected)}</div>
      )}
    </div>
  );
}