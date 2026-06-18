import { useEffect, useState } from 'react';
import { getBudget, setBudget } from '../api';

const now = new Date();
const MONTHS = Array.from({length:12},(_,i)=>({value:i+1,label:new Date(2000,i).toLocaleString('default',{month:'long'})}));

export default function Budget() {
  const [month,  setMonth]  = useState(now.getMonth()+1);
  const [year,   setYear]   = useState(now.getFullYear());
  const [data,   setData]   = useState(null);
  const [input,  setInput]  = useState('');
  const [saved,  setSaved]  = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => getBudget(month, year).then(d=>{ setData(d); setInput(d.budget||''); });
  useEffect(()=>{ load(); },[month,year]); // eslint-disable-line

  const save = async (e) => {
    e.preventDefault(); setSaving(true);
    await setBudget({ month, year, amount: parseFloat(input) });
    setSaved(true); setTimeout(()=>setSaved(false), 2000);
    load(); setSaving(false);
  };

  const pct = data?.budget > 0 ? Math.min((data.spent/data.budget)*100,100) : 0;

  return (
    <div className="max-w-lg">
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Budget</h1>
        <p className="text-[13px] text-gray-400 mt-0.5">Set and track your monthly spending limit</p>
      </div>

      {/* Month picker */}
      <div className="flex gap-2 mb-5">
        <select value={month} onChange={e=>setMonth(+e.target.value)}
          className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
          {MONTHS.map(m=><option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
        <select value={year} onChange={e=>setYear(+e.target.value)}
          className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
          {[2024,2025,2026,2027].map(y=><option key={y}>{y}</option>)}
        </select>
      </div>

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label:'Budget',    value:data.budget,    color:'text-gray-900 dark:text-white' },
            { label:'Spent',     value:data.spent,     color:'text-red-500' },
            { label:'Remaining', value:data.remaining, color:data.remaining>=0?'text-accent-600 dark:text-accent-400':'text-red-500' },
          ].map(s=>(
            <div key={s.label} className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-4 text-center">
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-2">{s.label}</p>
              <p className={`text-lg font-semibold ${s.color}`}>₹{s.value?.toLocaleString('en-IN',{maximumFractionDigits:0})}</p>
            </div>
          ))}
        </div>
      )}

      {/* Progress */}
      {data && data.budget > 0 && (
        <div className={`rounded-xl p-4 mb-4 ${data.alert ? 'bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900' : 'bg-accent-50 dark:bg-accent-950/20 border border-accent-100 dark:border-accent-900/30'}`}>
          <div className="flex justify-between text-[12px] mb-2">
            <span className={data.alert ? 'text-red-700 dark:text-red-400 font-medium' : 'text-accent-700 dark:text-accent-300 font-medium'}>
              {data.alert ? '⚠ Over 80% used — slow down!' : `${pct.toFixed(0)}% used`}
            </span>
            <span className="text-gray-400">{pct.toFixed(1)}%</span>
          </div>
          <div className="bg-white/60 dark:bg-gray-800 rounded-full h-2.5">
            <div className={`h-2.5 rounded-full transition-all duration-500 ${data.alert ? 'bg-red-500' : 'bg-accent-500'}`} style={{width:`${pct}%`}} />
          </div>
        </div>
      )}

      {/* Set budget form */}
      <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-5">
        <p className="text-[13px] font-medium text-gray-700 dark:text-gray-300 mb-3">Set Monthly Budget</p>
        <form onSubmit={save} className="flex gap-2">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-[13px]">₹</span>
            <input required type="number" min="1" step="100" placeholder="e.g. 8000" value={input}
              onChange={e=>setInput(e.target.value)}
              className="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg pl-7 pr-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent-500" />
          </div>
          <button type="submit" disabled={saving}
            className="bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-[13px] font-medium transition whitespace-nowrap">
            {saved ? '✓ Saved' : saving ? 'Saving…' : 'Save'}
          </button>
        </form>
      </div>
    </div>
  );
}
