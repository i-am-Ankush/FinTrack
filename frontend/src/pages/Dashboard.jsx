import { useEffect, useState } from 'react';
import { getBudget, getSummary, exportPDF } from '../api';
import { PieChart, Pie, Cell, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';

const PIE_COLORS = ['#059669','#34D399','#F59E0B','#EC4899','#8B5CF6','#06B6D4','#EF4444','#6B7280'];
const now = new Date();

function StatCard({ label, value, sub, subColor }) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-4">
      <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-2">{label}</p>
      <p className="text-xl font-semibold text-gray-900 dark:text-white">{value}</p>
      {sub && <p className={`text-[11px] mt-1 ${subColor || 'text-gray-400'}`}>{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const [month,   setMonth]   = useState(now.getMonth() + 1);
  const [year,    setYear]    = useState(now.getFullYear());
  const [budget,  setBudget]  = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([getBudget(month, year), getSummary(month, year)])
      .then(([b, s]) => { setBudget(b); setSummary(s); })
      .finally(() => setLoading(false));
  }, [month, year]);

  const months = Array.from({length:12},(_,i)=>({
    value: i+1,
    label: new Date(2000,i).toLocaleString('default',{month:'long'})
  }));

  // Expenses = sum of positive-amount categories (exclude Income)
  const expenseCategories = summary?.by_category?.filter(c => c.category !== 'Income') || [];
  const totalSpent = expenseCategories.reduce((a, c) => a + c.total, 0);

  // Income = from analytics summary (negative amounts stored as positive total by backend)
  // The /analytics/summary endpoint already filters out Income from by_category
  // We need to get income from the transactions directly via the summary
  const totalIncome = summary?.total_income || 0;
  const netSavings  = totalIncome - totalSpent;

  const pct = budget?.budget > 0 ? Math.min((budget.spent / budget.budget) * 100, 100) : 0;

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            Good {now.getHours() < 12 ? 'morning' : now.getHours() < 17 ? 'afternoon' : 'evening'} 👋
          </h1>
          <p className="text-[13px] text-gray-400 mt-0.5">Here's your financial summary</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={month} onChange={e=>setMonth(+e.target.value)}
            className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
            {months.map(m=><option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          <select value={year} onChange={e=>setYear(+e.target.value)}
            className="border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 rounded-lg px-3 py-1.5 text-[13px] outline-none focus:ring-2 focus:ring-accent-500">
            {[2024,2025,2026,2027].map(y=><option key={y}>{y}</option>)}
          </select>
          <button onClick={()=>exportPDF(month,year)}
            className="flex items-center gap-1.5 bg-accent-600 hover:bg-accent-700 text-white px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition">
            ↓ Export PDF
          </button>
        </div>
      </div>

      {/* Budget bar */}
      {budget && budget.budget > 0 && (
        <div className={`rounded-xl p-4 mb-5 ${budget.alert
          ? 'bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900'
          : 'bg-accent-50 dark:bg-accent-950/20 border border-accent-100 dark:border-accent-900/30'}`}>
          <div className="flex justify-between text-[13px] mb-2">
            <span className={budget.alert
              ? 'text-red-700 dark:text-red-400 font-medium'
              : 'text-accent-800 dark:text-accent-300 font-medium'}>
              {budget.alert ? '⚠ Budget alert — over 80% used' : 'Monthly Budget'}
            </span>
            <span className="text-gray-500 dark:text-gray-400">
              ₹{budget.spent?.toLocaleString('en-IN')} of ₹{budget.budget?.toLocaleString('en-IN')}
            </span>
          </div>
          <div className="bg-white/60 dark:bg-gray-800/60 rounded-full h-2">
            <div className={`h-2 rounded-full transition-all ${budget.alert ? 'bg-red-500' : 'bg-accent-500'}`}
              style={{width:`${pct}%`}} />
          </div>
          <p className="text-[11px] text-gray-400 mt-1.5">
            ₹{budget.remaining?.toLocaleString('en-IN')} remaining · {pct.toFixed(0)}% used
          </p>
        </div>
      )}

      {/* Stat cards — now 5 cards including Income and Net Savings */}
      <div className="grid grid-cols-5 gap-3 mb-5">
        <StatCard
          label="Total Spent"
          value={`₹${totalSpent.toLocaleString('en-IN',{maximumFractionDigits:0})}`}
          sub={budget?.budget > 0 ? `${pct.toFixed(0)}% of budget` : 'No budget set'}
        />
        <StatCard
          label="Budget"
          value={`₹${budget?.budget?.toLocaleString('en-IN',{maximumFractionDigits:0}) || 0}`}
          sub="This month"
        />
        <StatCard
          label="Remaining"
          value={`₹${budget?.remaining?.toLocaleString('en-IN',{maximumFractionDigits:0}) || 0}`}
          subColor={budget?.remaining < 0 ? 'text-red-500' : 'text-accent-600'}
          sub={budget?.remaining < 0 ? 'Over budget' : 'Available'}
        />
        <StatCard
          label="Income"
          value={`₹${totalIncome.toLocaleString('en-IN',{maximumFractionDigits:0})}`}
          sub="Received this month"
          subColor="text-accent-600 dark:text-accent-400"
        />
        <StatCard
          label="Net Savings"
          value={`₹${netSavings.toLocaleString('en-IN',{maximumFractionDigits:0})}`}
          subColor={netSavings >= 0 ? 'text-accent-600 dark:text-accent-400' : 'text-red-500'}
          sub={netSavings >= 0 ? 'Surplus' : 'Deficit'}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-4">
          <p className="text-[13px] font-medium text-gray-700 dark:text-gray-300 mb-4">Daily Spending Trend</p>
          {summary?.daily_trend?.some(d=>d.amount>0) ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={summary.daily_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{fontSize:10}} tickFormatter={d=>d.slice(8)} />
                <YAxis tick={{fontSize:10}} />
                <Tooltip
                  formatter={v=>`₹${v}`}
                  labelFormatter={l=>`Date: ${l}`}
                  contentStyle={{fontSize:12,borderRadius:8,border:'1px solid #e5e7eb'}}
                />
                <Line type="monotone" dataKey="amount" stroke="#059669" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-[13px] text-gray-400">
              No spending data this month
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-800 rounded-xl p-4">
          <p className="text-[13px] font-medium text-gray-700 dark:text-gray-300 mb-4">Spending by Category</p>
          {expenseCategories.length ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie data={expenseCategories} dataKey="total" nameKey="category"
                    cx="50%" cy="50%" outerRadius={70} innerRadius={40}>
                    {expenseCategories.map((_,i)=>(
                      <Cell key={i} fill={PIE_COLORS[i%PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={v=>`₹${v}`} contentStyle={{fontSize:12,borderRadius:8}} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-col gap-1.5 flex-1">
                {expenseCategories.slice(0,6).map((c,i)=>(
                  <div key={c.category} className="flex items-center gap-2 text-[12px]">
                    <div className="w-2 h-2 rounded-full shrink-0"
                      style={{background:PIE_COLORS[i%PIE_COLORS.length]}} />
                    <span className="text-gray-600 dark:text-gray-400 flex-1">{c.category}</span>
                    <span className="font-medium text-gray-800 dark:text-gray-200">
                      ₹{c.total?.toLocaleString('en-IN')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-[13px] text-gray-400">
              No category data
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
