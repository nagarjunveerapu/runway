import React, { useMemo } from 'react';
export default function DropdownWithCustom({ options=[], value, onChange, customValue, onCustomChange, placeholder='-- select --' }){
  const isCustom = useMemo(()=> value && !options.includes(value), [value, options]);
  return (
    <div>
      <select className="mt-1 block w-full p-2 border rounded" value={isCustom? '__custom__': (value||'')} onChange={(e)=>{ const v = e.target.value; if(v==='__custom__') onChange('__custom__'); else onChange(v); }}>
        <option value="">{placeholder}</option>
        {options.map(o=> <option key={o} value={o}>{o}</option>)}
        <option value="__custom__">-- Custom --</option>
      </select>
      { (isCustom || value==='__custom__') && (
        <input className="mt-2 block w-full p-2 border rounded" placeholder="Type custom..." value={customValue||''} onChange={e=>onCustomChange(e.target.value)} />
      )}
    </div>
  );
}