import React from 'react';
export default function ConfirmModal({ open, title='Confirm', message='', onCancel, onConfirm }){ if(!open) return null; return (
  <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
    <div className="bg-white rounded-lg shadow-lg max-w-lg w-full p-4">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-gray-700 mb-4">{message}</p>
      <div className="flex justify-end gap-2">
        <button className="px-3 py-1 border rounded" onClick={onCancel}>Cancel</button>
        <button className="px-3 py-1 bg-runwayTeal text-white rounded" onClick={onConfirm}>Confirm</button>
      </div>
    </div>
  </div>
); }
