import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, signup } from '../api';

export default function Login() {
  const navigate = useNavigate();
  const [mode,     setMode]    = useState('login');
  const [email,    setEmail]   = useState('');
  const [password, setPass]    = useState('');
  const [error,    setError]   = useState('');
  const [loading,  setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      const data = await (mode === 'login' ? login : signup)(email, password);
      localStorage.setItem('fintrack_token', data.token);
      navigate('/');
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-8 justify-center">
          <div className="w-9 h-9 bg-accent-600 rounded-xl flex items-center justify-center text-white font-bold text-lg">₹</div>
          <span className="text-2xl font-semibold text-gray-900 dark:text-white">FinTrack</span>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 p-6 shadow-sm">
          <h2 className="text-[15px] font-semibold text-gray-900 dark:text-white mb-1">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-[13px] text-gray-400 mb-5">
            {mode === 'login' ? 'Sign in to your account' : 'Start tracking your finances'}
          </p>

          <form onSubmit={submit} className="flex flex-col gap-3">
            <div>
              <label className="text-[12px] font-medium text-gray-500 dark:text-gray-400 block mb-1">Email</label>
              <input type="email" required placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent transition" />
            </div>
            <div>
              <label className="text-[12px] font-medium text-gray-500 dark:text-gray-400 block mb-1">Password</label>
              <input type="password" required placeholder="Min 6 characters" value={password} onChange={e => setPass(e.target.value)}
                className="w-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-lg px-3 py-2 text-[13px] outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent transition" />
            </div>

            {error && <p className="text-red-500 text-[12px]">{error}</p>}

            <button type="submit" disabled={loading}
              className="w-full bg-accent-600 hover:bg-accent-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-[13px] transition mt-1">
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-[12px] text-gray-400 mt-4">
            {mode === 'login' ? "Don't have an account? " : 'Already registered? '}
            <button onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }}
              className="text-accent-600 dark:text-accent-400 font-medium hover:underline">
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
