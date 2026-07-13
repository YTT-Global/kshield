import React, { useState, useEffect } from 'react';
import { Menu, Shield } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { Settings } from './components/Settings';

type Theme = 'light' | 'dark';

export const App: React.FC = () => {
  const [currentView, setView] = useState<'dashboard' | 'settings'>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('kshield-theme');
    return stored === 'light' ? 'light' : 'dark';
  });

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  useEffect(() => {
    const root = document.documentElement;
    theme === 'dark' ? root.classList.add('dark') : root.classList.remove('dark');
    localStorage.setItem('kshield-theme', theme);
  }, [theme]);

  const handleSetView = (view: 'dashboard' | 'settings') => {
    setView(view);
    setSidebarOpen(false);
  };

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">

      {/* Mobile top bar */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-14 z-20 flex items-center px-4 gap-3
        bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 shadow-sm dark:shadow-none">
        <button
          onClick={() => setSidebarOpen(true)}
          className="h-9 w-9 flex items-center justify-center rounded-lg transition-colors
            text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Open menu"
        >
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-md bg-red-600 flex items-center justify-center">
            <Shield size={14} className="text-white" strokeWidth={2.5} />
          </div>
          <span className="font-bold text-sm text-slate-900 dark:text-white tracking-tight">KShield</span>
        </div>
      </header>

      {/* Mobile sidebar backdrop */}
      <div
        onClick={() => setSidebarOpen(false)}
        className={`lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-30 transition-opacity duration-300 ${
          sidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
      />

      <Sidebar
        currentView={currentView}
        setView={handleSetView}
        theme={theme}
        toggleTheme={toggleTheme}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex-1 lg:pl-64 min-w-0 pt-14 lg:pt-0">
        <div className="px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
          <div className="max-w-[1400px] mx-auto">
            {currentView === 'dashboard' ? <Dashboard /> : <Settings />}
          </div>
        </div>
      </main>

    </div>
  );
};

export default App;
