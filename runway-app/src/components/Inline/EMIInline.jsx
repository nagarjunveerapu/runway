// src/components/Inline/EMIInline.jsx
import React, { useState, useCallback } from "react";
import InlineAddCard from "./InlineAddCard";
import { useApp } from "../../context/AppContext";

export default function EMIInline({ onSuccess }) {
  const { addTransaction } = useApp();
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [startDate, setStartDate] = useState("");

  const handleSubmit = useCallback(async () => {
    if (!name || !amount || !startDate) return alert("Please fill name, amount and date");
    const txn = {
      date: startDate,
      category: `EMI-${name}`,
      amount: Number(amount),
      type: "expense",
      notes: ""
    };
    try {
      await addTransaction(txn);
      setName("");
      setAmount("");
      setStartDate("");
      if (typeof onSuccess === "function") onSuccess(txn);
      window.dispatchEvent(new CustomEvent("inline-add-success", { detail: { message: "EMI added", txn } }));
    } catch (err) {
      alert("Error adding EMI: " + (err?.message || "unknown"));
    }
  }, [name, amount, startDate, addTransaction, onSuccess]);

  return (
    <InlineAddCard title="Add EMI" subtitle="Record monthly EMIs & liabilities" onSubmitLabel="Add EMI" onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
        <input className="p-2 border rounded" placeholder="Loan / EMI name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="p-2 border rounded" placeholder="Amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input className="p-2 border rounded" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
      </div>
    </InlineAddCard>
  );
}