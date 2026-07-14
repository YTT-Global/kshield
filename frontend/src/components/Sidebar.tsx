import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { LayoutDashboard, Settings2, BookOpen, Sun, Moon, X } from 'lucide-react';

interface SidebarProps {
  currentView: 'dashboard' | 'settings' | 'docs';
  setView: (view: 'dashboard' | 'settings' | 'docs') => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  isOpen: boolean;
  onClose: () => void;
}

const navItems: { id: 'dashboard' | 'settings' | 'docs'; label: string; Icon: LucideIcon }[] = [
  { id: 'dashboard', label: 'Dashboard',        Icon: LayoutDashboard },
  { id: 'settings',  label: 'Rules & Settings', Icon: Settings2        },
  { id: 'docs',      label: 'How to Use',       Icon: BookOpen         },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentView, setView, theme, toggleTheme, isOpen, onClose,
}) => {
  return (
    <aside className={`
      w-64 bg-white dark:bg-slate-900
      border-r border-slate-200 dark:border-slate-800
      flex flex-col h-screen fixed left-0 top-0 z-40
      transition-transform duration-300 ease-in-out
      ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      lg:translate-x-0
    `}>

      {/* Brand */}
      <div className="px-5 py-6 border-b border-slate-200 dark:border-slate-800 relative">
        <div className="flex flex-col items-center gap-2 w-full">
          {/* KShield — enterprise security badge */}
          <svg viewBox="0 0 48 54" fill="none" xmlns="http://www.w3.org/2000/svg"
               className="h-14 w-12 flex-shrink-0 drop-shadow-[0_8px_24px_rgba(185,28,28,0.65)]">
            <defs>
              {/* 4-stop body: bright cherry → vivid red → blood red → near-black */}
              <linearGradient id="eb" x1="24" y1="1" x2="24" y2="53" gradientUnits="userSpaceOnUse">
                <stop offset="0%"   stopColor="#ff4d4d" />
                <stop offset="28%"  stopColor="#cc0000" />
                <stop offset="68%"  stopColor="#7a0000" />
                <stop offset="100%" stopColor="#180000" />
              </linearGradient>
              {/* Convex gloss — top-left light source */}
              <radialGradient id="eg" cx="33%" cy="13%" r="44%">
                <stop offset="0%"   stopColor="rgba(255,255,255,0.24)" />
                <stop offset="100%" stopColor="rgba(255,255,255,0)"    />
              </radialGradient>
              {/* Base depth — grounds the badge */}
              <radialGradient id="ed" cx="50%" cy="96%" r="62%">
                <stop offset="0%"   stopColor="rgba(0,0,0,0.65)" />
                <stop offset="100%" stopColor="rgba(0,0,0,0)"    />
              </radialGradient>
              {/* K lettermark drop shadow */}
              <filter id="ekf" x="-30%" y="-30%" width="160%" height="160%">
                <feDropShadow dx="0" dy="1.5" stdDeviation="2" floodColor="rgba(0,0,0,0.55)" />
              </filter>
            </defs>

            {/* Outer cast shadow — baked for crisp rendering */}
            <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z"
                  fill="rgba(80,0,0,0.45)"
                  transform="translate(0,3) scale(1.03,1) translate(-0.72,0)" />

            {/* Main shield body */}
            <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z"
                  fill="url(#eb)" />
            {/* Convex gloss */}
            <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z"
                  fill="url(#eg)" />
            {/* Base depth */}
            <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52C13.5 48.5 5 39.5 5 27V9L24 2Z"
                  fill="url(#ed)" />

            {/* Metallic rim — left/top highlight (light side) */}
            <path d="M24 2L5 9V27C5 39.5 13.5 48.5 24 52"
                  fill="none" stroke="rgba(255,180,180,0.35)" strokeWidth="1.5" strokeLinecap="round" />
            {/* Metallic rim — right/bottom shadow (dark side) */}
            <path d="M24 2L43 9V27C43 39.5 34.5 48.5 24 52"
                  fill="none" stroke="rgba(0,0,0,0.55)" strokeWidth="1.5" strokeLinecap="round" />

            {/* Inner inset bevel */}
            <path d="M24 6.5L39.5 13V27C39.5 37.5 32.5 45.5 24 48.5C15.5 45.5 8.5 37.5 8.5 27V13L24 6.5Z"
                  fill="none" stroke="rgba(255,255,255,0.09)" strokeWidth="1" />

            {/* Subtle mid-line — the boundary between dev and production */}
            <line x1="9" y1="29" x2="39" y2="29"
                  stroke="rgba(255,255,255,0.06)" strokeWidth="0.75" />

            {/* K — bold architectural lettermark, square caps for machine precision */}
            {/* Vertical bar */}
            <line x1="15.5" y1="17" x2="15.5" y2="39"
                  stroke="white" strokeWidth="6" strokeLinecap="square"
                  filter="url(#ekf)" />
            {/* Upper arm — developer building upward toward deployment */}
            <line x1="15.5" y1="28" x2="33" y2="17"
                  stroke="white" strokeWidth="5" strokeLinecap="butt"
                  filter="url(#ekf)" />
            {/* Lower arm — grounding the shield */}
            <line x1="15.5" y1="28" x2="33" y2="39"
                  stroke="white" strokeWidth="5" strokeLinecap="butt"
                  filter="url(#ekf)" />

            {/* Forward-to-production arrow — subtle, right of K */}
            <path d="M35 26 L39 27.5 L35 29"
                  fill="none" stroke="rgba(255,255,255,0.32)"
                  strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="text-center">
            <h1 className="font-bold text-base tracking-widest uppercase text-slate-900 dark:text-white leading-none">KShield</h1>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono tracking-widest mt-1 block">v1.0.0 · LOCAL</span>
          </div>
        </div>
        {/* Mobile close button — absolute so it doesn't break centered layout */}
        <button
          onClick={onClose}
          className="lg:hidden absolute top-4 right-4 h-8 w-8 flex items-center justify-center rounded-lg transition-colors
            text-slate-400 hover:text-slate-600 dark:hover:text-slate-200
            hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="Close menu"
        >
          <X size={16} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-600 uppercase tracking-widest px-3 mb-2.5">Menu</p>
        {navItems.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setView(id)}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 flex items-center gap-3 ${
              currentView === id
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white'
                : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <Icon
              size={16}
              className={`transition-colors flex-shrink-0 ${
                currentView === id ? 'text-red-600 dark:text-red-500' : ''
              }`}
            />
            {label}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-slate-200 dark:border-slate-800 space-y-0.5">
        <button
          onClick={toggleTheme}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150
            text-slate-500 dark:text-slate-400
            hover:bg-slate-50 dark:hover:bg-slate-800/50
            hover:text-slate-800 dark:hover:text-slate-200"
        >
          {theme === 'dark'
            ? <Sun size={16} className="flex-shrink-0" />
            : <Moon size={16} className="flex-shrink-0" />
          }
          <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
        </button>

        <div className="flex items-center gap-3 px-3 py-2.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
          <span className="text-xs font-mono text-slate-400 dark:text-slate-500">Local Node · Active</span>
        </div>
      </div>

    </aside>
  );
};
