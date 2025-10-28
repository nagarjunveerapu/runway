// src/components/EMIs/EMIsList.jsx
import React from "react";
import { useApp } from "../../context/AppContext";

export default function EMIsList(){
  const { transactions = [] } = useApp();
  const emis = (transactions || []).filter(t => /emi/i.test(t.category || '') || t.type === 'expense' && /home loan|personal loan|car/i.test(t.category || ''));
  return (
    <div className="bg-white p-4 rounded shadow">
      <h3 className="font-semibold mb-2">EMIs</h3>
      {emis.length === 0 ? <div className="text-sm text-gray-500">No EMIs recorded.</div> : (
        <div className="space-y-2">
          {emis.map(s => (
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