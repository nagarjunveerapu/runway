// src/components/Settings/LookupsEditor.jsx
import React, { useState } from "react";

/**
 * Props:
 *  - items: array (for assetTypes it's array of objects)
 *  - onAdd(item)
 *  - onUpdate(index, newVal)
 *  - onDelete(index)
 *  - type: 'simple' | 'assetTypes' (controls UI)
 */
export default function LookupsEditor({ title, items = [], setItems, type = "simple" }) {
  const [newValue, setNewValue] = useState("");
  const [newLiquid, setNewLiquid] = useState(true);

  function handleAdd() {
    if (!newValue || (type === "assetTypes" && !newValue.trim())) return;
    if (type === "assetTypes") {
      setItems([{ name: newValue.trim(), liquid: !!newLiquid }, ...items]);
    } else {
      setItems([newValue.trim(), ...items]);
    }
    setNewValue("");
    setNewLiquid(true);
  }

  function handleUpdate(i, v) {
    const copy = [...items];
    copy[i] = v;
    setItems(copy);
  }

  function handleDelete(i) {
    const copy = [...items];
    copy.splice(i, 1);
    setItems(copy);
  }

  return (
    <div className="mb-4">
      <h3 className="font-semibold mb-2">{title}</h3>

      <div className="mb-2 flex gap-2">
        <input
          className="p-2 border rounded flex-1"
          placeholder={type === "assetTypes" ? "e.g. Mutual Fund" : "New item"}
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
        />
        {type === "assetTypes" && (
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={newLiquid} onChange={(e) => setNewLiquid(e.target.checked)} />
            liquid
          </label>
        )}
        <button className="px-3 py-1 bg-runwayTeal text-white rounded" onClick={handleAdd}>Add</button>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-gray-500">No items</div>
      ) : (
        <div className="space-y-2 max-h-48 overflow-auto">
          {items.map((it, idx) => (
            <div key={idx} className="flex items-center gap-2">
              {type === "assetTypes" ? (
                <>
                  <input className="p-1 border rounded flex-1" value={it.name} onChange={(e) => handleUpdate(idx, { ...it, name: e.target.value })} />
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={!!it.liquid} onChange={(e) => handleUpdate(idx, { ...it, liquid: e.target.checked })} />
                    liquid
                  </label>
                </>
              ) : (
                <input className="p-1 border rounded flex-1" value={it} onChange={(e) => handleUpdate(idx, e.target.value)} />
              )}
              <button className="px-2 py-1 border rounded text-red-600" onClick={() => handleDelete(idx)}>Delete</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}