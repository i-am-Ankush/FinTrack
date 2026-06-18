import { useState } from 'react';
import { uploadPDF, trainModel, getMLMetrics } from '../api';

export default function Upload() {
  const [file,    setFile]    = useState(null);
  const [bank,    setBank]    = useState('sbi');
  const [status,  setStatus]  = useState(null); // {type:'success'|'error', msg}
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);

  const upload = async (e) => {
    e.preventDefault(); if (!file) return;
    setLoading(true); setStatus(null);
    try {
      const res = await uploadPDF(file, bank);
      setStatus({ type:'success', msg:`Imported ${res.count} transactions from ${bank.toUpperCase()} statement.` });
    } catch (err) {
      setStatus({ type:'error', msg:err.message });
    } finally { setLoading(false); }
  };

  const train = async () => {
    setLoading(true); setStatus({ type:'info', msg:'Training ML model…' });
    try {
      const res = await trainModel();
      setStatus({ type:'success', msg:`Model trained! Accuracy: ${res.accuracy}% on ${res.samples} samples.` });
      setMetrics(res);
    } catch (err) {
      setStatus({ type:'error', msg:err.message });
    } finally { setLoading(false); }
  };

  const fetchMetrics = async () => {
    const m = await getMLMetrics();
    setMetrics(m);
  };

  const statusStyles = {
    success: 'bg-accent-50 dark:bg-accent-950/30 border-accent-100 dark:border-accent-900 text-accent-700 dark:text-accent-300',
    error:   'bg-red-50 dark:bg-red-950/30 border-red-100 dark:border-red-900 text-red-700 dark:text-red-400',
    info:    'bg-blue-50 dark:bg-blue-950/30 border-blue-100 dark:border-blue-900 text-blue-700 dark:text-blue-400',
  };

  return (
    <div className="max-w-lg">
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Upload PDF</h1>
        <p className="text-[13px] text-gray-400 mt-0.5">Import transactions from your bank statement</p>
      </div>

      {/* Upload card */}
      <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-5 mb-4">
        <p className="text-[13px] font-medium text-gray-700 dark:text-gray-300 mb-4">Bank Statement</p>
        <form onSubmit={upload} className="flex flex-col gap-3">
          <div>
            <label className="text-[12px] font-medium text-gray-500 dark:text-gray-400 block mb-1">Bank</label>
            <select value={bank} onChange={e=>setBank(e.target.value)}
              className="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-lg px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
              <option value="sbi">SBI</option>
              <option value="paytm">Paytm / UPI</option>
            </select>
          </div>
          <div>
            <label className="text-[12px] font-medium text-gray-500 dark:text-gray-400 block mb-1">PDF File</label>
            <div className="border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg p-4 text-center hover:border-accent-400 transition-colors">
              <input type="file" accept=".pdf" required id="pdffile"
                onChange={e=>setFile(e.target.files[0])}
                className="hidden" />
              <label htmlFor="pdffile" className="cursor-pointer">
                <div className="text-2xl mb-1">📄</div>
                <p className="text-[13px] text-gray-500 dark:text-gray-400">
                  {file ? file.name : 'Click to choose PDF'}
                </p>
                <p className="text-[11px] text-gray-400 mt-0.5">Max 16MB</p>
              </label>
            </div>
          </div>
          <button type="submit" disabled={loading || !file}
            className="w-full bg-accent-600 hover:bg-accent-700 disabled:opacity-40 text-white py-2.5 rounded-lg text-[13px] font-medium transition">
            {loading ? 'Uploading…' : 'Upload & Import'}
          </button>
        </form>
      </div>

      {/* ML card */}
      <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-5 mb-4">
        <p className="text-[13px] font-medium text-gray-700 dark:text-gray-300 mb-1">ML Auto-Classifier</p>
        <p className="text-[12px] text-gray-400 mb-4">After importing 10+ transactions, train the model to auto-categorise future entries.</p>
        <div className="flex gap-2">
          <button onClick={train} disabled={loading}
            className="flex items-center gap-1.5 bg-accent-600 hover:bg-accent-700 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-[13px] font-medium transition">
            🧠 Train Model
          </button>
          <button onClick={fetchMetrics}
            className="border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 px-4 py-2 rounded-lg text-[13px] hover:bg-gray-50 dark:hover:bg-gray-800 transition">
            View Metrics
          </button>
        </div>

        {metrics?.accuracy && (
          <div className="mt-4 bg-accent-50 dark:bg-accent-950/20 border border-accent-100 dark:border-accent-900/30 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[13px] font-semibold text-accent-700 dark:text-accent-300">Accuracy: {metrics.accuracy}%</p>
              <p className="text-[12px] text-gray-400">{metrics.samples} samples</p>
            </div>
            {metrics.report && (
              <div className="grid grid-cols-2 gap-1.5 mt-2">
                {Object.entries(metrics.report)
                  .filter(([k])=>!['accuracy','macro avg','weighted avg'].includes(k))
                  .map(([cat,vals])=>(
                    <div key={cat} className="flex justify-between text-[11px] text-gray-500 dark:text-gray-400">
                      <span>{cat}</span>
                      <span>P:{(vals.precision*100).toFixed(0)}% R:{(vals.recall*100).toFixed(0)}%</span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Status */}
      {status && (
        <div className={`border rounded-xl p-4 text-[13px] ${statusStyles[status.type]}`}>
          {status.msg}
        </div>
      )}

      {/* Info */}
      <div className="mt-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-xl p-4">
        <p className="text-[12px] font-semibold text-amber-700 dark:text-amber-400 mb-1">Supported formats</p>
        <p className="text-[12px] text-amber-600 dark:text-amber-500"><strong>SBI:</strong> e-statement PDF with Dr/Cr columns</p>
        <p className="text-[12px] text-amber-600 dark:text-amber-500 mt-0.5"><strong>Paytm/UPI:</strong> Monthly statement with +/− amounts</p>
      </div>
    </div>
  );
}
