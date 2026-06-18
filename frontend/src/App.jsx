import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Login        from './pages/Login';
import Dashboard    from './pages/Dashboard';
import Transactions from './pages/Transactions';
import Budget       from './pages/Budget';
import Upload       from './pages/Upload';
import Layout       from './components/Layout';

function RequireAuth({ children }) {
  return localStorage.getItem('fintrack_token') ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('ft_dark') === '1');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('ft_dark', dark ? '1' : '0');
  }, [dark]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={
          <RequireAuth>
            <Layout dark={dark} setDark={setDark}>
              <Routes>
                <Route path="/"             element={<Dashboard />} />
                <Route path="/transactions" element={<Transactions />} />
                <Route path="/budget"       element={<Budget />} />
                <Route path="/upload"       element={<Upload />} />
              </Routes>
            </Layout>
          </RequireAuth>
        } />
      </Routes>
    </BrowserRouter>
  );
}
