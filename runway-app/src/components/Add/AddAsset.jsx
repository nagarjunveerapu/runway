// src/components/Add/AddAsset.jsx
import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";

export default function AddAsset({ open=true, editing=null, onClose = () => {} }){
  const { lookups = { assetTypes: [] }, addAsset, updateAsset } = useApp();
  const [form, setForm] = useState({ name:'', type: lookups.assetTypes[0]?.name || 'Bank Account', quantity:'', purchase_value:'', purchase_date:'', is_investment:true, liquid: false });

  useEffect(()=>{
    if(editing){
      setForm({
        name: editing.name || '',
        type: editing.type || lookups.assetTypes[0]?.name || 'Bank Account',
        quantity: editing.quantity || '',
        purchase_value: editing.purchase_value || '',
        purchase_date: editing.purchase_date || '',
        is_investment: !!editing.is_investment,
        liquid: !!editing.liquid
      });
    }
  }, [editing]);

  if(!open) return null;

  function handleSubmit(e){
    e && e.preventDefault && e.preventDefault();
    const payload = {
      ...form,
      quantity: Number(form.quantity || 0),
      purchase_value: Number(form.purchase_value || 0),
      liquid: !!form.liquid
    };
    if(editing && editing.id){
      updateAsset && updateAsset({ ...editing, ...payload });
    } else {
      addAsset && addAsset(payload);
    }
    onClose && onClose();
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-3 bg-white p-4 rounded shadow">
        <h3 className="font-semibold">{editing ? "Edit Asset" : "Add Asset"}</h3>
        <input className="w-full p-2 border rounded" placeholder="Asset name" value={form.name} onChange={e=>setForm(s=>({...s,name:e.target.value}))} />
        <select className="w-full p-2 border rounded" value={form.type} onChange={e=>setForm(s=>({...s,type:e.target.value}))}>
          {(lookups.assetTypes||[]).map(t=> <option key={t.name} value={t.name}>{t.name}</option>)}
        </select>
        <div className="grid grid-cols-2 gap-2">
          <input className="p-2 border rounded" placeholder="Quantity" type="number" value={form.quantity} onChange={e=>setForm(s=>({...s,quantity:e.target.value}))} />
          <input className="p-2 border rounded" placeholder="Purchase value" type="number" value={form.purchase_value} onChange={e=>setForm(s=>({...s,purchase_value:e.target.value}))} />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm">Liquid</label>
          <input type="checkbox" checked={!!form.liquid} onChange={e=>setForm(s=>({...s,liquid:e.target.checked}))} />
          <label className="text-sm ml-4">Is Investment</label>
          <input type="checkbox" checked={!!form.is_investment} onChange={e=>setForm(s=>({...s,is_investment:e.target.checked}))} />
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-2 bg-runwayTeal text-white rounded" type="submit">{editing ? "Save" : "Add Asset"}</button>
          <button type="button" className="px-3 py-2 border rounded" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </div>
  );
}