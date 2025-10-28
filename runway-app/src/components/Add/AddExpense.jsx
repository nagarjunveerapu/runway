// src/components/Add/AddExpense.jsx
import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";

export default function AddExpense({ open=true, editing=null, onClose = () => {} }){
  const { lookups = {}, addTransaction, updateTransaction } = useApp();
  const [form, setForm] = useState({ date:'', category: (lookups.expenseCategories && lookups.expenseCategories[0]) || '', amount:'', notes:'' });

  useEffect(()=>{ if(editing){ setForm({ date: editing.date || '', category: editing.category || (lookups.expenseCategories && lookups.expenseCategories[0]) || '', amount: editing.amount || '', notes: editing.notes || '' }); } }, [editing]);

  if(!open) return null;

  function handleSubmit(e){ e && e.preventDefault && e.preventDefault();
    const payload = { ...form, amount: Number(form.amount||0), type: 'expense' };
    if(editing && editing.id) updateTransaction && updateTransaction({ ...editing, ...payload });
    else addTransaction && addTransaction(payload);
    onClose && onClose();
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-3 bg-white p-4 rounded shadow">
        <h3 className="font-semibold">{editing ? "Edit Expense" : "Add Expense"}</h3>
        <input className="w-full p-2 border rounded" type="date" value={form.date} onChange={e=>setForm(s=>({...s,date:e.target.value}))} />
        <select className="w-full p-2 border rounded" value={form.category} onChange={e=>setForm(s=>({...s,category:e.target.value}))}>
          {(lookups.expenseCategories||[]).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <input className="w-full p-2 border rounded" type="number" value={form.amount} onChange={e=>setForm(s=>({...s,amount:e.target.value}))} placeholder="Amount" />
        <input className="w-full p-2 border rounded" value={form.notes} onChange={e=>setForm(s=>({...s,notes:e.target.value}))} placeholder="Notes (optional)" />
        <div className="flex gap-2">
          <button className="px-3 py-2 bg-runwayTeal text-white rounded" type="submit">{editing ? "Save" : "Add Expense"}</button>
          <button type="button" className="px-3 py-2 border rounded" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  );
}