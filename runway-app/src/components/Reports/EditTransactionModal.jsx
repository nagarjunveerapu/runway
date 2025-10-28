// src/components/Reports/EditTransactionModal.jsx
import React, { useState, useEffect } from "react";

/**
 * EditTransactionModal
 * Props:
 *  - open: boolean
 *  - tx: transaction object
 *  - onClose: fn
 *  - onSave: fn(updatedTx)
 *  - categories: array of category strings
 */
export default function EditTransactionModal({ open, tx, onClose, onSave, categories = [] }) {
  const [form, setForm] = useState({ date: "", category: "", subcategory: "", amount: "", notes: "" });

  useEffect(() => {
    if (tx) {
      setForm({
        date: tx.date || "",
        category: tx.category || (categories[0] || ""),
        subcategory: tx.subcategory || "",
        amount: tx.amount || "",
        notes: tx.notes || "",
      });
    } else {
      setForm({ date: "", category: categories[0] || "", subcategory: "", amount: "", notes: "" });
    }
  }, [tx, categories]);

  if (!open) return null;

  function handleSubmit(e) {
    e && e.preventDefault();
    // compute month (YYYY-MM) from date
   const months = useMemo(() => {
        const s = new Set(transactions.map(t => (t.date || "").slice(0,7)).filter(Boolean));
        return Array.from(s).sort().reverse();
        }, [transactions]);
    const updated = {
      ...tx,
      date: form.date,
      month,
      category: form.category,
      subcategory: form.subcategory,
      amount: Number(form.amount || 0),
      notes: form.notes,
    };
    onSave && onSave(updated);
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <form onSubmit={handleSubmit} className="bg-white p-4 rounded shadow max-w-md w-full">
        <h3 className="font-semibold mb-2">Edit Transaction</h3>

        <div className="mb-2">
          <label className="block text-sm">Date</label>
          <input
            type="date"
            className="p-2 border rounded w-full"
            value={form.date}
            onChange={(e) => setForm(s => ({ ...s, date: e.target.value }))}
          />
        </div>

        <div className="mb-2">
          <label className="block text-sm">Category</label>
          <select
            className="p-2 border rounded w-full"
            value={form.category}
            onChange={(e) => setForm(s => ({ ...s, category: e.target.value }))}
          >
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
            {/* keep current value as option in case it's custom */}
            <option value={form.category}>{form.category}</option>
          </select>
        </div>

        <div className="mb-2">
          <label className="block text-sm">Subcategory</label>
          <input
            className="p-2 border rounded w-full"
            value={form.subcategory}
            onChange={(e) => setForm(s => ({ ...s, subcategory: e.target.value }))}
          />
        </div>

        <div className="mb-2">
          <label className="block text-sm">Amount</label>
          <input
            type="number"
            className="p-2 border rounded w-full"
            value={form.amount}
            onChange={(e) => setForm(s => ({ ...s, amount: e.target.value }))}
          />
        </div>

        <div className="mb-3">
          <label className="block text-sm">Notes</label>
          <input
            className="p-2 border rounded w-full"
            value={form.notes}
            onChange={(e) => setForm(s => ({ ...s, notes: e.target.value }))}
          />
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" className="px-3 py-1 border rounded" onClick={onClose}>Cancel</button>
          <button type="submit" className="px-3 py-1 bg-runwayTeal text-white rounded">Save</button>
        </div>
      </form>
    </div>
  );
}