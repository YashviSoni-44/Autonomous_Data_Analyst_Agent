import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CodeBlock({ code, language = 'sql' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!code) return;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-wrapper">
      <div className="code-header">
        <span>{language.toUpperCase()}</span>
        <button className="btn-copy" onClick={handleCopy}>
          {copied ? <Check size={14} color="#34D399" /> : <Copy size={14} />}
          <span>{copied ? 'Copied!' : 'Copy SQL'}</span>
        </button>
      </div>
      <div className="code-content">
        <code>{code || '-- No SQL query generated'}</code>
      </div>
    </div>
  );
}
