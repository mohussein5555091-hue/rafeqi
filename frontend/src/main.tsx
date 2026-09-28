import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { I18nProvider } from './i18n';
import { ThemeProvider } from './theme';
import { SessionProvider } from './data/session';
import { ToastProvider } from './components';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <I18nProvider>
        <ThemeProvider>
          <SessionProvider>
            <ToastProvider>
              <App />
            </ToastProvider>
          </SessionProvider>
        </ThemeProvider>
      </I18nProvider>
    </BrowserRouter>
  </StrictMode>,
);
