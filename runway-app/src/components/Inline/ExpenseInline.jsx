// src/components/Inline/ExpenseInline.jsx
import React, { useState, useCallback } from "react";
import InlineAddCard from "./InlineAddCard";
import { useApp } from "../../context/AppContext";

export default function ExpenseInline({ onSuccess }) {
  const { addTransaction, lookups } = useApp();
  const [category, setCategory] = useState((lookups?.expenseCategories && lookups.expenseCategories[0]) || "");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");

  const handleSubmit = useCallback(async () => {
    if (!category || !amount || !date) return alert("Please fill category, amount and date");
    const txn = {
      date,
      category,
      amount: Number(amount),
      type: "expense",
      notes: ""
    };
    try {
      await addTransaction(txn);
      setCategory((lookups?.expenseCategories && lookups.expenseCategories[0]) || "");
      setAmount("");
      setDate("");
      if (typeof onSuccess === "function") onSuccess(txn);
      window.dispatchEvent(new CustomEvent("inline-add-success", { detail: { message: "Expense added", txn } }));
    } catch (err) {
      alert("Error adding expense: " + (err?.message || "unknown"));
    }
  }, [category, amount, date, addTransaction, lookups, onSuccess]);

  return (
    <InlineAddCard title="Add Expense" subtitle="Bills, groceries, taxes" onSubmitLabel="Add Expense" onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
        <select className="p-2 border rounded" value={category} onChange={(e) => setCategory(e.target.value)}>
          {(lookups?.expenseCategories || []).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <input className="p-2 border rounded" placeholder="Amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input className="p-2 border rounded" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>
    </InlineAddCard>
  );
}