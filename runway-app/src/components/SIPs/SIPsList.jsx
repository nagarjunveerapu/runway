// src/components/SIPs/SIPsList.jsx
import React from "react";
import { useApp } from "../../context/AppContext";

export default function SIPsList(){
  const { transactions = [] } = useApp();
  const sips = (transactions || []).filter(t => t.type === 'investment' || /sip/i.test(t.category||''));
  return (
    <div className="bg-white p-4 rounded shadow">
      <h3 className="font-semibold mb-2">SIPs / Investments</h3>
      {sips.length === 0 ? <div className="text-sm text-gray-500">No SIPs recorded.</div> : (
        <div className="space-y-2">
          {sips.map(s => (
            <div key={s.id} className="p-2 border rounded flex justify-between items-center">
              <div>
                <div className="font-medium">{s.category}</div>
                <div className="text-xs text-gray-500">{s.date} • {s.amount}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}