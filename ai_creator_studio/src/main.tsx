import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { invoke } from '@tauri-apps/api/core';
import { Image, Video, Music, Mic2, BookOpen, FolderOpen, History, Settings, Sparkles, Cpu, HardDrive, ChevronRight, LoaderCircle } from 'lucide-react';
import './styles.css';

const API = 'http://127.0.0.1:18765';
const actions = [
  { id: 'video', icon: Video, title: 'Видео', text: 'Создать видео по описанию' },
  { id: 'image', icon: Image, title: 'Изображение', text: 'Создать картинку' },
  { id: 'music', icon: Music, title: 'Музыка', text: 'Создать музыку' },
  { id: 'voice', icon: Mic2, title: 'Голос', text: 'Синтезировать речь' },
  { id: 'story', icon: BookOpen, title: 'История', text: 'Создать сценарий и проект' },
];

type Model = { model_type: string; name?: string; availability?: { available?: boolean }; metadata?: Record<string, unknown> };

async function waitForBackend() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try { if ((await fetch(`${API}/health`)).ok) return true; } catch { /* starting */ }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function App() {
  const [active, setActive] = useState('home');
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState('image');
  const [engineReady, setEngineReady] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<string[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [modelType, setModelType] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [width, setWidth] = useState('');
  const [height, setHeight] = useState('');
  const [steps, setSteps] = useState('');
  const [seed, setSeed] = useState('');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        await invoke('start_engine');
        const ready = await waitForBackend();
        if (!mounted) return;
        setEngineReady(ready);
        if (ready) {
          const response = await fetch(`${API}/models`);
          const data = await response.json();
          if (data.ok) {
            const discovered = data.models as Model[];
            setModels(discovered);
            const first = discovered.find((m) => m.availability?.available !== false);
            if (first) setModelType(first.model_type);
          }
        }
      } catch (err) { if (mounted) setError(String(err)); }
    })();
    return () => { mounted = false; };
  }, []);

  const selected = actions.find((item) => item.id === mode) ?? actions[1];

  async function generate() {
    if (!prompt.trim() || generating || mode !== 'image') return;
    setGenerating(true); setError(''); setResult([]);
    try {
      const settings: Record<string, unknown> = { model_type: modelType };
      if (width) settings.width = Number(width);
      if (height) settings.height = Number(height);
      if (steps) settings.num_inference_steps = Number(steps);
      if (seed) settings.seed = Number(seed);
      const response = await fetch(`${API}/generate/image`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, settings }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Не удалось создать задачу');
      const jobId = data.job_id as string;
      let current: any = null;
      for (let i = 0; i < 720; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        current = await (await fetch(`${API}/jobs/${jobId}`)).json();
        if (current.status === 'completed' || current.status === 'failed') break;
      }
      if (!current || current.status === 'failed') throw new Error(current?.error || 'Генерация завершилась с ошибкой');
      const payload = current.result || {};
      const files = payload.generated_files || payload.files || payload.artifacts?.map((item: { path?: string }) => item.path).filter(Boolean) || [];
      setResult(files.length ? files : [JSON.stringify(payload)]);
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setGenerating(false); }
  }

  const imageResults = result.filter((file) => /\.(png|jpe?g|webp)$/i.test(file));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><div><strong>AI Creator</strong><span>Studio</span></div></div>
        <nav>
          <button className={active === 'home' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('home')}><Sparkles size={18} /> Создать</button>
          <button className={active === 'projects' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('projects')}><FolderOpen size={18} /> Проекты</button>
          <button className={active === 'history' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('history')}><History size={18} /> История</button>
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => setActive('settings')}><Settings size={18} /> Настройки</button>
          <div className="system-card"><div className="system-row"><Cpu size={15} /><span>RTX 5060 Ti</span><i className={engineReady ? 'online' : 'offline'} /></div><div className="system-row muted"><HardDrive size={15} /><span>24 ГБ памяти</span></div></div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar"><div><span className="eyebrow">ЛОКАЛЬНАЯ AI-СТУДИЯ</span><h1>{active === 'home' ? 'Что создаём?' : active === 'projects' ? 'Мои проекты' : active === 'history' ? 'История генераций' : 'Настройки'}</h1></div><div className="status"><i className={engineReady ? 'online' : 'offline'} /> {engineReady ? 'Движок готов' : 'Запуск движка…'}</div></header>
        {active === 'home' && <section className="content">
          <div className="mode-grid">{actions.map(({ id, icon: Icon, title, text }) => <button key={id} className={mode === id ? 'mode-card selected' : 'mode-card'} onClick={() => setMode(id)}><div className="mode-icon"><Icon size={22} /></div><div><strong>{title}</strong><span>{text}</span></div><ChevronRight size={17} className="arrow" /></button>)}</div>
          <div className="creator-card">
            <div className="creator-head"><div><span className="eyebrow">{selected.title.toUpperCase()}</span><h2>{selected.text}</h2></div><button className="ghost" onClick={() => setAdvanced((v) => !v)}>{advanced ? 'Скрыть настройки' : 'Расширенные настройки'}</button></div>
            {advanced && <div className="advanced"><label>Модель<select value={modelType} onChange={(e) => setModelType(e.target.value)}>{models.map((model) => <option key={model.model_type} value={model.model_type}>{model.name || model.model_type}</option>)}</select></label><label>Ширина<input value={width} onChange={(e) => setWidth(e.target.value)} placeholder="по умолчанию" /></label><label>Высота<input value={height} onChange={(e) => setHeight(e.target.value)} placeholder="по умолчанию" /></label><label>Шаги<input value={steps} onChange={(e) => setSteps(e.target.value)} placeholder="по умолчанию" /></label><label>Seed<input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="-1" /></label></div>}
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Опишите, что вы хотите создать…" />
            <div className="creator-footer"><span className="hint">Генерация выполняется локально на вашем компьютере</span><button className="generate" disabled={!prompt.trim() || generating || !engineReady || mode !== 'image'} onClick={generate}>{generating ? <><LoaderCircle size={18} className="spin" /> Генерация…</> : <><Sparkles size={18} /> Создать</>}</button></div>
            {error && <div className="error-box">{error}</div>}
            {imageResults.length > 0 && <div className="result-gallery">{imageResults.map((file) => <img key={file} src={`${API}/file?path=${encodeURIComponent(file)}`} alt="Результат генерации" />)}</div>}
            {result.length > 0 && imageResults.length === 0 && <div className="result-box"><strong>Готово</strong>{result.map((file) => <div key={file} className="result-file">{file}</div>)}</div>}
          </div>
          <div className="section-title"><h3>Последние проекты</h3><button className="link">Показать все</button></div><div className="empty-state"><div className="empty-icon"><FolderOpen size={24} /></div><strong>Пока здесь пусто</strong><span>Создайте первый материал — он появится здесь.</span></div>
        </section>}
        {active !== 'home' && <section className="placeholder"><div className="empty-icon"><Sparkles size={24} /></div><h2>Раздел готовится</h2><p>Основа приложения уже работает. Следующий этап — проекты, история и остальные генераторы.</p></section>}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
