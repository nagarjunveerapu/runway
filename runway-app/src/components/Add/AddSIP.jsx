// src/components/Add/AddSIP.jsx
import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";

export default function AddSIP({ open=true, editing=null, onClose = () => {} }){
  const { lookups = {}, addTransaction, updateTransaction } = useApp();
  const [form, setForm] = useState({ date:'', category:'Investments-SIP', amount:'', notes:'' });

  useEffect(()=>{ if(editing){ setForm({ date: editing.date || '', category: editing.category || 'Investments-SIP', amount: editing.amount || '', notes: editing.notes || '' }); } }, [editing]);

  if(!open) return null;

  function handleSubmit(e){ e && e.preventDefault && e.preventDefault();
    const payload = { ...form, amount: Number(form.amount||0), type: 'investment' };
    if(editing && editing.id) updateTransaction && updateTransaction({ ...editing, ...payload });
    else addTransaction && addTransaction(payload);
    onClose && onClose();
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-3 bg-white p-4 rounded shadow">
        <h3 className="font-semibold">{editing ? "Edit SIP" : "Add SIP"}</h3>
        <input className="w-full p-2 border rounded" type="date" value={form.date} onChange={e=>setForm(s=>({...s,date:e.target.value}))} />
        <input className="w-full p-2 border rounded" value={form.category} onChange={e=>setForm(s=>({...s,category:e.target.value}))} placeholder="Category (Investments-SIP...)" />
        <input className="w-full p-2 border rounded" type="number" value={form.amount} onChange={e=>setForm(s=>({...s,amount:e.target.value}))} placeholder="Monthly amount" />
        <input className="w-full p-2 border rounded" value={form.notes} onChange={e=>setForm(s=>({...s,notes:e.target.value}))} placeholder="Notes (optional)" />
        <div className="flex gap-2">
          <button className="px-3 py-2 bg-runwayTeal text-white rounded" type="submit">{editing ? "Save" : "Add SIP"}</button>
          <button type="button" className="px-3 py-2 border rounded" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  );
}