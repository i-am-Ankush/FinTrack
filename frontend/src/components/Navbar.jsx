import { Link, useNavigate, useLocation } from 'react-router-dom';

const links = [
  { to: '/',             label: 'Dashboard' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/budget',       label: 'Budget' },
  { to: '/upload',       label: 'Upload PDF' },
];

export default function Navbar() {
  const navigate  = useNavigate();
  const { pathname } = useLocation();

  const logout = () => {
    localStorage.removeItem('fintrack_token');
    navigate('/login');
  };

  return (
    <nav className="bg-indigo-600 text-white shadow">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
        <span className="font-bold text-lg tracking-tight">💰 FinTrack</span>
        <div className="flex gap-6 text-sm font-medium">
          {links.map(l => (
            <Link key={l.to} to={l.to}
              className={`hover:text-indigo-200 transition ${pathname === l.to ? 'border-b-2 border-white pb-0.5' : ''}`}>
              {l.label}
            </Link>
          ))}
        </div>
        <button onClick={logout} className="text-sm hover:text-indigo-200 transition">
          Logout
        </button>
      </div>
    </nav>
  );
}
