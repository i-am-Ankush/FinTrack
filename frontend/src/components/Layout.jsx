import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { getBudget } from '../api';

const now = new Date();

const navLinks = [
  { to: '/',             label: 'Dashboard' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/budget',       label: 'Budget' },
  { to: '/upload',       label: 'Upload PDF' },
];

export default function Layout({ children, dark, setDark }) {
  const navigate     = useNavigate();
  const { pathname } = useLocation();
  const [budget, setBudget] = useState(null);

  useEffect(() => {
    getBudget(now.getMonth() + 1, now.getFullYear()).then(setBudget).catch(() => {});
  }, []);

  const logout = () => {
    localStorage.removeItem('fintrack_token');
    navigate('/login');
  };

  const pct = budget?.budget > 0 ? Math.min((budget.spent / budget.budget) * 100, 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      {/* Top bar — logo + dark toggle + logout only */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 px-6 h-14 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-accent-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">₹</div>
          <span className="font-semibold text-gray-900 dark:text-white text-[15px]">FinTrack</span>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => setDark(!dark)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-lg">
            {dark ? '☀' : '☾'}
          </button>
          <button onClick={logout}
            className="text-[13px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white transition-colors">
            Logout
          </button>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-52 bg-white dark:bg-gray-900 border-r border-gray-100 dark:border-gray-800 p-3 flex flex-col shrink-0">
          <p className="text-[10px] text-gray-400 uppercase tracking-widest px-2 mb-1.5 mt-2">Menu</p>
          {navLinks.map(l => (
            <Link key={l.to} to={l.to}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] mb-0.5 transition-colors
                ${pathname === l.to
                  ? 'bg-accent-100 text-accent-800 dark:bg-accent-900/40 dark:text-accent-300 font-medium'
                  : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-800 dark:hover:text-gray-200'}`}>
              {l.label}
            </Link>
          ))}

          {/* Budget mini */}
          {budget && budget.budget > 0 && (
            <div className="mt-auto bg-gray-50 dark:bg-gray-800 rounded-xl p-3">
              <p className="text-[11px] text-gray-400 mb-1">Monthly budget</p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                ₹{budget.budget?.toLocaleString('en-IN')}
              </p>
              <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                <div className={`h-1.5 rounded-full transition-all ${pct >= 80 ? 'bg-red-500' : 'bg-accent-500'}`}
                  style={{ width: `${pct}%` }} />
              </div>
              <p className="text-[11px] text-gray-400 mt-1.5">
                ₹{budget.remaining?.toLocaleString('en-IN')} remaining
              </p>
            </div>
          )}
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
