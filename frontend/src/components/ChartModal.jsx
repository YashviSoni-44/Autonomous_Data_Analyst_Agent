import React from 'react';
import { X } from 'lucide-react';

export default function ChartModal({ imageBase64, onClose }) {
  if (!imageBase64) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <X size={18} />
        </button>
        <img
          src={`data:image/png;base64,${imageBase64}`}
          alt="Expanded Visualization"
          style={{ maxWidth: '100%', maxHeight: '80vh', borderRadius: '8px', objectFit: 'contain' }}
        />
      </div>
    </div>
  );
}
