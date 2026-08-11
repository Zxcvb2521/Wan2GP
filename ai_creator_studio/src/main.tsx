import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Image, Video, Music, Mic2, BookOpen, FolderOpen, History, Settings, Sparkles, Cpu, HardDrive, ChevronRight } from 'lucide-react';
import './styles.css';

const actions = [
  { id: 'video', icon: Video, title: 'Видео', text: 'Создать видео по описанию' },
  { id: 'image', icon: Image, title: 'Изображение', text: 'Создать картинку' },
  { id: 'music', icon: Music, title: 'Музыка', text: 'Создать музыку' },
  { id: 'voice', icon: Mic2, title: 'Голос', text: 'Синтезировать речь' },
  { id: 'story', icon: BookOpen, title: 'История', text: 'Создать сценарий и проект' },
];

function App() {
  const [active, setActive] = useState('home');
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState('image');

  const selected = actions.find((item) => item.id === mode) ?? actions[1];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div><strong>AI Creator</strong><span>Studio</span></div>
        </div>

        <nav>
          <button className={active === 'home' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('home')}><Sparkles size={18} /> Создать</button>
          <button className={active === 'projects' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('projects')}><FolderOpen size={18} /> Проекты</button>
          <button className={active === 'history' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('history')}><History size={18} /> История</button>
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => setActive('settings')}><Settings size={18} /> Настройки</button>
          <div className="system-card">
            <div className="system-row"><Cpu size={15} /><span>RTX 5060 Ti</span><i className="online" /></div>
            <div className="system-row muted"><HardDrive size={15} /><span>Память 24 ГБ</span></div>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><span className="eyebrow">ЛОКАЛЬНАЯ AI-СТУДИЯ</span><h1>{active === 'home' ? 'Что создаём?' : active === 'projects' ? 'Мои проекты' : active === 'history' ? 'История генераций' : 'Настройки'}</h1></div>
          <div className="status"><i className="online" /> Движок готов</div>
        </header>

        {active === 'home' && (
          <section className="content">
            <div className="mode-grid">
              {actions.map(({ id, icon: Icon, title, text }) => (
                <button key={id} className={mode === id ? 'mode-card selected' : 'mode-card'} onClick={() => setMode(id)}>
                  <div className="mode-icon"><Icon size={22} /></div>
                  <div><strong>{title}</strong><span>{text}</span></div>
                  <ChevronRight size={17} className="arrow" />
                </button>
              ))}
            </div>

            <div className="creator-card">
              <div className="creator-head">
                <div><span className="eyebrow">{selected.title.toUpperCase()}</span><h2>{selected.text}</h2></div>
                <button className="ghost">Расширенные настройки</button>
              </div>
              <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Опишите, что вы хотите создать…" />
              <div className="creator-footer">
                <span className="hint">Генерация выполняется локально на вашем компьютере</span>
                <button className="generate" disabled={!prompt.trim()}><Sparkles size={18} /> Создать</button>
              </div>
            </div>

            <div className="section-title"><h3>Последние проекты</h3><button className="link">Показать все</button></div>
            <div className="empty-state"><div className="empty-icon"><FolderOpen size={24} /></div><strong>Пока здесь пусто</strong><span>Создайте первый материал — он появится здесь.</span></div>
          </section>
        )}

        {active !== 'home' && <section className="placeholder"><div className="empty-icon"><Sparkles size={24} /></div><h2>Раздел готовится</h2><p>Это окно уже подключено к новой оболочке. Следующим этапом сюда подключается реальный backend WanGP.</p></section>}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
