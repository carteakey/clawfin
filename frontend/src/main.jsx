import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/700.css';
import App from './App';
import './index.css';

const stored = localStorage.getItem('autofin_theme') || localStorage.getItem('clawfin_theme');
if (!localStorage.getItem('autofin_theme') && stored) {
  localStorage.setItem('autofin_theme', stored);
}
const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
document.documentElement.dataset.theme = stored || (prefersLight ? 'light' : 'dark');

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
