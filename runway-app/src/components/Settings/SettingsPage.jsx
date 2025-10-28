// src/components/Settings/SettingsPage.jsx
import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import ConfirmModal from "../Common/ConfirmModal";
import { DEFAULT_LOOKUPS } from "../../lookups.js";

function Tile({ title, desc, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full p-4 bg-white border rounded-xl text-left shadow-sm hover:shadow-md active:scale-[0.99] transition-all"
    >
      <div className="font-semibold text-gray-800">{title}</div>
      <div className="text-sm text-gray-500 mt-1">{desc}</div>
    </button>
  );
}

function ListEditor({ label, items, setItems, isObject = false }) {
  // isObject: items are objects (used for assetTypes), else simple strings
  function updateItem(idx, value) {
    const copy = Array.isArray(items) ? [...items] : [];
    copy[idx] = value;
    setItems(copy);
  }
  function removeItem(idx) {
    const copy = [...items];
    copy.splice(idx, 1);
    setItems(copy);
  }
  function addItem() {
    const copy = items ? [...items] : [];
    copy.push(isObject ? { name: "New", liquid: false } : "");
    setItems(copy);
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold">{label}</h3>
        <button onClick={addItem} className="text-sm text-runwayTeal">+ Add</button>
      </div>

      <div className="space-y-2">
        {!items || items.length === 0 ? (
          <div className="text-sm text-gray-500">No items yet.</div>
        ) : (
          items.map((it, i) => (
            <div key={i} className="flex items-center gap-2">
              {isObject ? (
                <>
                  <input
                    value={it.name}
                    onChange={(e) => updateItem(i, { ...it, name: e.target.value })}
                    className="p-2 border rounded flex-1"
                  />
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={!!it.liquid}
                      onChange={(e) => updateItem(i, { ...it, liquid: !!e.target.checked })}
                    />
                    <span className="text-xs text-gray-600">Liquid</span>
                  </label>
                  <button onClick={() => removeItem(i)} className="px-2 py-1 text-sm border rounded text-red-600">Delete</button>
                </>
              ) : (
                <>
                  <input
                    value={it}
                    onChange={(e) => updateItem(i, e.target.value)}
                    className="p-2 border rounded flex-1"
                  />
                  <button onClick={() => removeItem(i)} className="px-2 py-1 text-sm border rounded text-red-600">Delete</button>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { lookups, updateLookups } = useApp();

  // local editable copy
  const [draft, setDraft] = useState(() => lookups || DEFAULT_LOOKUPS);
  const [selected, setSelected] = useState(null);
  const [confirmConfig, setConfirmConfig] = useState({ open: false, title: "", message: "", onConfirm: null });

  useEffect(() => {
    setDraft(lookups || DEFAULT_LOOKUPS);
  }, [lookups]);

  function openConfirm({ title, message, onConfirm }) {
    setConfirmConfig({ open: true, title, message, onConfirm });
  }
  function closeConfirm() {
    setConfirmConfig({ open: false, title: "", message: "", onConfirm: null });
  }

  function save() {
    // basic validation: ensure lists exist
    const next = {
      incomeCategories: draft.incomeCategories || [],
      expenseCategories: draft.expenseCategories || [],
      assetTypes: draft.assetTypes || [],
      liabilityTypes: draft.liabilityTypes || [],
      investmentCategories: draft.investmentCategories || []
    };
    updateLookups(next);
    setSelected(null);
  }

  function resetToDefault() {
    openConfirm({
      title: "Reset lookups",
      message: "Reset all lookup lists to the built-in defaults? This will overwrite your local changes.",
      onConfirm: () => {
        updateLookups(DEFAULT_LOOKUPS);
        setDraft(DEFAULT_LOOKUPS);
        closeConfirm();
        setSelected(null);
      }
    });
  }

  function updateField(key, value) {
    setDraft((s) => ({ ...(s || {}), [key]: value }));
  }

  const categories = [
    { id: "incomeCategories", title: "Income Categories", desc: "Used to classify income transactions", isObject: false },
    { id: "expenseCategories", title: "Expense Categories", desc: "Used to classify expenses", isObject: false },
    { id: "assetTypes", title: "Asset Types", desc: "Types of assets (mark liquid where applicable)", isObject: true },
    { id: "liabilityTypes", title: "Liability Types", desc: "Loans and liabilities", isObject: false },
    { id: "investmentCategories", title: "Investment Categories", desc: "Common investment labels", isObject: false }
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {selected && (
            <button onClick={() => setSelected(null)} className="px-3 py-1 border rounded text-sm hover:bg-gray-50">←</button>
          )}
          <h2 className="text-lg font-semibold">{selected ? categories.find(c => c.id === selected)?.title : "Settings — Lookup Lists"}</h2>
        </div>
        {!selected && (
          <div className="flex items-center gap-2">
            <button onClick={resetToDefault} className="px-3 py-1 border rounded text-sm text-red-600 hover:bg-red-50">Reset to Default</button>
            <button onClick={() => save()} className="px-3 py-1 bg-runwayTeal text-white rounded text-sm">Save</button>
          </div>
        )}
      </div>

      {!selected ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {categories.map((c) => (
            <Tile
              key={c.id}
              title={c.title}
              desc={c.desc}
              onClick={() => setSelected(c.id)}
            />
          ))}
        </div>
      ) : (
        <div className="bg-white p-4 rounded shadow">
          {/* Editor area for selected category */}
          <div className="mb-4">
            <ListEditor
              label={categories.find(c => c.id === selected).title}
              items={draft[selected]}
              setItems={(v) => updateField(selected, v)}
              isObject={categories.find(c => c.id === selected).isObject}
            />
          </div>

          <div className="flex gap-2 justify-end">
            <button onClick={() => { setDraft(lookups || DEFAULT_LOOKUPS); setSelected(null); }} className="px-3 py-1 border rounded">Cancel</button>
            <button onClick={save} className="px-3 py-1 bg-runwayTeal text-white rounded">Save</button>
          </div>
        </div>
      )}

      <div className="mt-6 text-sm text-gray-600">
        <div>Tip: Changes persist locally in your browser. Use Reset to restore built-in defaults.</div>
      </div>

      <ConfirmModal
        open={confirmConfig.open}
        title={confirmConfig.title}
        message={confirmConfig.message}
        onCancel={closeConfirm}
        onConfirm={() => {
          if (typeof confirmConfig.onConfirm === "function") confirmConfig.onConfirm();
          else closeConfirm();
        }}
      />
    </div>
  );
}