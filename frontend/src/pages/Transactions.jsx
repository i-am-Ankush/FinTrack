import { useEffect, useState } from 'react';
import { getTransactions, addTransaction, updateTransaction, deleteTransaction } from '../api';

const CATEGORIES = ['Food','Transport','Shopping','Education','Health','Entertainment','Utilities','Income','Other'];
const now = new Date();
const toMonthStr = (y,m) => `${y}-${String(m).padStart(2,'0')}`;

const CAT_COLORS = {
  Food:'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  Transport:'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  Shopping:'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  Education:'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  Health:'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  Entertainment:'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  Utilities:'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  Income:'bg-accent-100 text-accent-700 dark:bg-accent-900/30 dark:text-accent-400',
  Other:'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

export default function Transactions() {
  const [txns,     setTxns]     = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [search,   setSearch]   = useState('');
  const [catFilter,setCatFilter]= useState('');
  const [month,    setMonth]    = useState(toMonthStr(now.getFullYear(), now.getMonth()+1));
  const [showForm, setShowForm] = useState(false);
  const [editing,  setEditing]  = useState(null);
  const [form,     setForm]     = useState({ amount:'', description:'', date:now.toISOString().slice(0,10), category:'Other' });
  const [error,    setError]    = useState('');
  const [saving,   setSaving]   = useState(false);

  const load = async () => {
    setLoading(true);
    const params = {};
    if (month)     params.month    = month;
    if (catFilter) params.category = catFilter;
    if (search)    params.search   = search;
    const data = await getTransactions(params).catch(()=>[]);
    setTxns(data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [month, catFilter, search]); // eslint-disable-line

  const openAdd = () => {
    setEditing(null);
    setForm({ amount:'', description:'', date:now.toISOString().slice(0,10), category:'Other' });
    setShowForm(true); setError('');
  };

  const openEdit = (t) => {
    setEditing(t.id);
    setForm({ amount:t.amount, description:t.description, date:t.date, category:t.category });
    setShowForm(true); setError('');
  };

  const submit = async (e) => {
    e.preventDefault(); setError(''); setSaving(true);
    try {
      if (editing) await updateTransaction(editing, form);
      else         await addTransaction(form);
      setShowForm(false); load();
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  };

  const del = async (id) => {
    if (!window.confirm('Delete this transaction?')) return;
    await deleteTransaction(id); load();
  };

  const totalExpense = txns.filter(t=>t.amount>0).reduce((a,t)=>a+t.amount,0);
  const totalIncome  = txns.filter(t=>t.amount<0).reduce((a,t)=>a+Math.abs(t.amount),0);

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Transactions</h1>
          <p className="text-[13px] text-gray-400 mt-0.5">{txns.length} entries</p>
        </div>
        <button onClick={openAdd}
          className="flex items-center gap-1.5 bg-accent-600 hover:bg-accent-700 text-white px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition">
          + Add transaction
        </button>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          { label:'Expenses', value:`₹${totalExpense.toLocaleString('en-IN',{maximumFractionDigits:0})}`, color:'text-red-500' },
          { label:'Income',   value:`₹${totalIncome.toLocaleString('en-IN',{maximumFractionDigits:0})}`,  color:'text-accent-600 dark:text-accent-400' },
          { label:'Net',      value:`₹${(totalIncome-totalExpense).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color:(totalIncome-totalExpense)>=0?'text-accent-600 dark:text-accent-400':'text-red-500' },
        ].map(s=>(
          <div key={s.label} className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl px-4 py-3">
            <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-1">{s.label}</p>
            <p className={`text-lg font-semibold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        <input placeholder="Search transactions…" value={search} onChange={e=>setSearch(e.target.value)}
          className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500 flex-1 max-w-xs" />
        <input type="month" value={month} onChange={e=>setMonth(e.target.value)}
          className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500" />
        <select value={catFilter} onChange={e=>setCatFilter(e.target.value)}
          className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
          <option value="">All categories</option>
          {CATEGORIES.map(c=><option key={c}>{c}</option>)}
        </select>
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">{editing ? 'Edit' : 'Add'} Transaction</h3>
            <form onSubmit={submit} className="flex flex-col gap-3">
              {[
                { label:'Amount (₹)', type:'number', step:'0.01', placeholder:'e.g. 349', key:'amount' },
                { label:'Description', type:'text', placeholder:'e.g. Swiggy order', key:'description' },
                { label:'Date', type:'date', key:'date' },
              ].map(f=>(
                <div key={f.key}>
                  <label className="text-[12px] font-medium text-gray-500 dark:text-gray-400 block mb-1">{f.label}</label>
                  <input required type={f.type} step={f.step} placeholder={f.placeholder} value={form[f.key]}
                    onChange={e=>setForm({...form,[f.key]:e.target.value})}
                    className="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent-500" />
                </div>
              ))}
              <div>
                <label className="text-[12px] font-medium text-gray-500 dark:text-gray-400 block mb-1">Category</label>
                <select value={form.category} onChange={e=>setForm({...form,category:e.target.value})}
                  className="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
                  {CATEGORIES.map(c=><option key={c}>{c}</option>)}
                </select>
              </div>
              {error && <p className="text-red-500 text-[12px]">{error}</p>}
              <div className="flex gap-2 mt-1">
                <button type="submit" disabled={saving}
                  className="flex-1 bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white py-2 rounded-lg text-[13px] font-medium transition">
                  {saving ? 'Saving…' : editing ? 'Update' : 'Add'}
                </button>
                <button type="button" onClick={()=>setShowForm(false)}
                  className="flex-1 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 py-2 rounded-lg text-[13px] hover:bg-gray-50 dark:hover:bg-gray-800 transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : txns.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl flex flex-col items-center justify-center py-16 text-gray-400">
          <p className="text-3xl mb-3">📭</p>
          <p className="text-[13px]">No transactions found</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                {['Date','Description','Category','Amount',''].map(h=>(
                  <th key={h} className="px-4 py-3 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
              {txns.map(t=>(
                <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 text-[13px] text-gray-400">{t.date}</td>
                  <td className="px-4 py-3 text-[13px] text-gray-800 dark:text-gray-200 max-w-xs truncate">{t.description}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${CAT_COLORS[t.category] || CAT_COLORS.Other}`}>
                      {t.category}
                    </span>
                  </td>
                  <td className={`px-4 py-3 text-[13px] font-medium ${t.amount < 0 ? 'text-accent-600 dark:text-accent-400' : 'text-gray-800 dark:text-gray-200'}`}>
                    {t.amount < 0 ? '+' : '−'}₹{Math.abs(t.amount).toLocaleString('en-IN',{maximumFractionDigits:2})}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-3">
                      <button onClick={()=>openEdit(t)} className="text-[12px] text-gray-400 hover:text-accent-600 transition-colors">Edit</button>
                      <button onClick={()=>del(t.id)}   className="text-[12px] text-gray-400 hover:text-red-500 transition-colors">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
