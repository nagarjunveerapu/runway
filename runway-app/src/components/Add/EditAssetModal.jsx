// src/components/Add/EditAssetModal.jsx
import React, { useEffect, useState } from "react";
import { useApp } from "../../context/AppContext";
import DropdownWithCustom from "../Common/DropdownWithCustom";

export default function EditAssetModal({ open, asset, onClose }) {
  const { lookups, updateAsset } = useApp();

  const [form, setForm] = useState({
    id: "", name: "", type: "", quantity: "", purchase_value: "", purchase_date: "", is_investment: true
  });
  const [custom, setCustom] = useState("");

  useEffect(() => {
    if (asset) {
      setForm({
        id: asset.id,
        name: asset.name || "",
        type: asset.type || (lookups.assetTypes?.[0]?.name || ""),
        quantity: asset.quantity ?? "",
        purchase_value: asset.purchase_value ?? "",
        purchase_date: asset.purchase_date || "",
        is_investment: !!asset.is_investment,
      });
    } else {
      setForm({
        id: "", name: "", type: lookups.assetTypes?.[0]?.name || "", quantity: "", purchase_value: "", purchase_date: "", is_investment: true
      });
    }
  }, [asset, lookups.assetTypes]);

  if (!open) return null;

  function handleSave(e) {
    e && e.preventDefault();
    const payload = {
      id: form.id || Date.now().toString(),
      name: (form.name && form.name.trim()) || (custom && custom.trim()) || 'Untitled',
      type: form.type === '__custom__' ? (custom && custom.trim() ? custom.trim() : form.type) : form.type,
      quantity: Number(form.quantity || 0),
      purchase_value: Number(form.purchase_value || 0),
      purchase_date: form.purchase_date || "",
      is_investment: !!form.is_investment,
      updated_at: new Date().toISOString()
    };
    updateAsset(payload);
    onClose && onClose();
  }

  const assetOptions = (lookups.assetTypes || []).map(a => a.name);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <form onSubmit={handleSave} className="bg-white p-4 rounded shadow max-w-md w-full">
        <h3 className="font-semibold mb-2">Edit Asset</h3>

        <div className="mb-2">
          <label className="block text-sm">Name</label>
          <input className="p-2 border rounded w-full" value={form.name} onChange={e => setForm(s => ({ ...s, name: e.target.value }))} />
        </div>

        <div className="mb-2">
          <label className="block text-sm">Type</label>
          <DropdownWithCustom
            options={assetOptions}
            value={form.type}
            onChange={v => setForm(s => ({ ...s, type: v }))}
            customValue={custom}
            onCustomChange={v => { setCustom(v); setForm(s => ({ ...s, type: '__custom__' })); }}
            placeholder="Select asset type"
          />
        </div>

        <div className="grid grid-cols-2 gap-2 mb-2">
          <input type="number" className="p-2 border rounded" placeholder="Quantity" value={form.quantity} onChange={e => setForm(s => ({ ...s, quantity: e.target.value }))} />
          <input type="number" className="p-2 border rounded" placeholder="Purchase value" value={form.purchase_value} onChange={e => setForm(s => ({ ...s, purchase_value: e.target.value }))} />
        </div>

        <div className="grid grid-cols-2 gap-2 mb-2">
          <input type="date" className="p-2 border rounded" value={form.purchase_date} onChange={e => setForm(s => ({ ...s, purchase_date: e.target.value }))} />
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.is_investment} onChange={e => setForm(s => ({ ...s, is_investment: e.target.checked }))} />
            Is Investment
          </label>
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" className="px-3 py-1 border rounded" onClick={onClose}>Cancel</button>
          <button type="submit" className="px-3 py-1 bg-runwayTeal text-white rounded">Save</button>
        </div>
      </form>
    </div>
  );
}