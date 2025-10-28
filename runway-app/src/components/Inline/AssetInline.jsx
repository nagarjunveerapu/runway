// src/components/Inline/AssetInline.jsx
import React, { useState, useCallback } from "react";
import InlineAddCard from "./InlineAddCard";
import { useApp } from "../../context/AppContext";

export default function AssetInline({ onSuccess }) {
  const { addAsset, lookups } = useApp();
  const defaultType = lookups?.assetTypes?.[0]?.name || "Bank Account";

  const [name, setName] = useState("");
  const [type, setType] = useState(defaultType);
  const [purchaseValue, setPurchaseValue] = useState("");

  const handleSubmit = useCallback(async () => {
    if (!name || !purchaseValue) return alert("Please enter name and purchase value");
    const a = {
      name,
      type,
      quantity: 1,
      purchase_value: Number(purchaseValue),
      purchase_date: new Date().toISOString().slice(0,10),
    };
    try {
      const created = await addAsset(a);
      setName("");
      setType(defaultType);
      setPurchaseValue("");
      if (typeof onSuccess === "function") onSuccess(created);
      window.dispatchEvent(new CustomEvent("inline-add-success", { detail: { message: "Asset added", asset: created } }));
    } catch (err) {
      alert("Error adding asset: " + (err?.message || "unknown"));
    }
  }, [name, type, purchaseValue, addAsset, defaultType, onSuccess]);

  return (
    <InlineAddCard title="Add Asset" subtitle="SIPs, Stocks, Gold, Property" onSubmitLabel="Add Asset" onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
        <input name="name" className="p-2 border rounded" placeholder="Asset name" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="p-2 border rounded" value={type} onChange={(e) => setType(e.target.value)}>
          {(lookups?.assetTypes || [{name:'Bank Account'}]).map((t) => <option key={t.name || t} value={t.name || t}>{t.name || t}</option>)}
        </select>
        <input name="purchase_value" type="number" className="p-2 border rounded" placeholder="Purchase value" value={purchaseValue} onChange={(e) => setPurchaseValue(e.target.value)} />
      </div>
    </InlineAddCard>
  );
}