// src/components/Assets/AssetsList.jsx
import React from "react";
import { useApp } from "../../context/AppContext";

export default function AssetsList() {
  const { assets = [], updateAsset, addAsset, /* deleteAsset maybe */ } = useApp() || {};

  return (
    <div className="bg-white border rounded p-3">
      <h3 className="font-semibold">Assets</h3>
      {(!assets || assets.length === 0) ? (
        <div className="text-sm text-gray-500">No assets yet.</div>
      ) : (
        <ul>
          {assets.map(a => (
            <li key={a.id} className="flex justify-between items-center py-2">
              <div>
                <div className="font-medium">{a.name}</div>
                <div className="text-xs text-gray-500">{a.type} • Qty:{a.quantity || 0} • Val: {Number(a.purchase_value||0).toLocaleString()}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}