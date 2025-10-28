// src/components/Inline/SIPInline.jsx
import React, { useState, useCallback } from "react";
import InlineAddCard from "./InlineAddCard";
import { useApp } from "../../context/AppContext";

export default function SIPInline({ onSuccess }) {
  const { addTransaction, lookups } = useApp();
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [startDate, setStartDate] = useState("");

  // choose first investment category if present
  const defaultCategory = (lookups && lookups.investmentCategories && lookups.investmentCategories[0]) || "Investments-SIP";

  const [category, setCategory] = useState(defaultCategory);

  const handleSubmit = useCallback(async () => {
    if (!amount || !startDate) return alert("Please enter amount and date");
    const txn = {
      date: startDate,
      category: category || `Investments-SIP: ${name || "SIP"}`,
      amount: Number(amount),
      notes: "",
      user_forced_type: "investment",
    };
    try {
      await addTransaction(txn);
      // reset
      setName("");
      setAmount("");
      setStartDate("");
      setCategory(defaultCategory);
      // external hook
      if (typeof onSuccess === "function") onSuccess(txn);
      // keep older dispatching behavior for other parts of app that listen
      window.dispatchEvent(new CustomEvent("inline-add-success", { detail: { message: "SIP added", txn } }));
    } catch (err) {
      alert("Error adding SIP: " + (err?.message || "unknown"));
    }
  }, [amount, startDate, category, name, addTransaction, onSuccess, defaultCategory]);

  return (
    <InlineAddCard title="Add SIP" subtitle="Recurring investments / SIPs" onSubmitLabel="Add SIP" onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-center">
        <input className="p-2 border rounded sm:col-span-1" placeholder="SIP name" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="p-2 border rounded" value={category} onChange={(e) => setCategory(e.target.value)}>
          {(lookups?.investmentCategories || []).map((c) => <option key={c} value={c}>{c}</option>)}
          <option value={`Investments-SIP: ${name || "SIP"}`}>Custom</option>
        </select>
        <input className="p-2 border rounded" placeholder="Amount / month" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input className="p-2 border rounded" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
      </div>
    </InlineAddCard>
  );
}