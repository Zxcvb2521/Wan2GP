import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { invoke } from '@tauri-apps/api/core';
import { Image, Video, Music, Mic2, BookOpen, FolderOpen, History, Settings, Sparkles, Cpu, HardDrive, ChevronRight, LoaderCircle, XCircle } from 'lucide-react';
import './styles.css';

const API = 'http://127.0.0.1:18765';
const actions = [
  { id: 'video', icon: Video, title: 'Видео', text: 'Создать видео по описанию' },
  { id: 'image', icon: Image, title: 'Изображение', text: 'Создать картинку' },
  { id: 'music', icon: Music, title: 'Музыка', text: 'Создать музыку' },
  { id: 'voice', icon: Mic2, title: 'Голос', text: 'Синтезировать речь' },
  { id: 'story', icon: BookOpen, title: 'История', text: 'Создать сценарий и проект' },
];
type Model = { model_type: string; name?: string; availability?: { available?: boolean } };
type Job = { id: string; status: string; progress: number; phase?: string; status_text?: string; current_step?: number; total_steps?: number; result?: any; error?: string; model_name?: string };

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
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState('');
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
    setGenerating(true); setError(''); setJob(null);
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
      let current: Job | null = null;
      for (let i = 0; i < 1440; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 350));
        current = await (await fetch(`${API}/jobs/${jobId}`)).json();
        setJob(current);
        if (['completed', 'failed', 'cancelled'].includes(current.status)) break;
      }
      if (!current) throw new Error('Нет ответа от задачи генерации');
      if (current.status === 'failed') throw new Error(current.error || 'Генерация завершилась с ошибкой');
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setGenerating(false); }
  }

  async function cancelGeneration() {
    if (!job?.id) return;
    try { await fetch(`${API}/jobs/${job.id}/cancel`, { method: 'POST' }); } catch (err) { setError(String(err)); }
  }

  const files = (job?.result?.generated_files || job?.result?.files || job?.result?.artifacts?.map((item: { path?: string }) => item.path).filter(Boolean) || []) as string[];
  const imageResults = files.filter((file) => /\.(png|jpe?g|webp)$/i.test(file));
  const percent = Math.round(Math.max(0, Math.min(1, job?.progress || 0)) * 100);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={19} /></div><div><strong>AI Creator</strong><span>Studio</span></div></div>
        <nav>
          <button className={active === 'home' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('home')}><Sparkles size={18} /> Создать</button>
          <button className={active === 'projects' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('projects')}><FolderOpen size={18} /> Проекты</button>
          <button className={active === 'history' ? 'nav-item active' : 'nav-item'} onClick={() => setActive('history')}><History size={18} /> История</button>
        </nav>
        <div className="sidebar-bottom"><button className="nav-item" onClick={() => setActive('settings')}><Settings size={18} /> Настройки</button><div className="system-card"><div className="system-row"><Cpu size={15} /><span>RTX 5060 Ti</span><i className={engineReady ? 'online' : 'offline'} /></div><div className="system-row muted"><HardDrive size={15} /><span>24 ГБ памяти</span></div></div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div><span className="eyebrow">ЛОКАЛЬНАЯ AI-СТУДИЯ</span><h1>{active === 'home' ? 'Что создаём?' : active === 'projects' ? 'Мои проекты' : active === 'history' ? 'История генераций' : 'Настройки'}</h1></div><div className="status"><i className={engineReady ? 'online' : 'offline'} /> {engineReady ? 'Движок готов' : 'Запуск движка…'}</div></header>
        {active === 'home' && <section className="content">
          <div className="mode-grid">{actions.map(({ id, icon: Icon, title, text }) => <button key={id} className={mode === id ? 'mode-card selected' : 'mode-card'} onClick={() => setMode(id)}><div className="mode-icon"><Icon size={22} /></div><div><strong>{title}</strong><span>{text}</span></div><ChevronRight size={17} className="arrow" /></button>)}</div>
          <div className="creator-card">
            <div className="creator-head"><div><span className="eyebrow">{selected.title.toUpperCase()}</span><h2>{selected.text}</h2></div><button className="ghost" onClick={() => setAdvanced((v) => !v)}>{advanced ? 'Скрыть настройки' : 'Расширенные настройки'}</button></div>
            {advanced && <div className="advanced"><label>Модель<select value={modelType} onChange={(e) => setModelType(e.target.value)}>{models.map((model) => <option key={model.model_type} value={model.model_type}>{model.name || model.model_type}</option>)}</select></label><label>Ширина<input value={width} onChange={(e) => setWidth(e.target.value)} placeholder="по умолчанию" /></label><label>Высота<input value={height} onChange={(e) => setHeight(e.target.value)} placeholder="по умолчанию" /></label><label>Шаги<input value={steps} onChange={(e) => setSteps(e.target.value)} placeholder="по умолчанию" /></label><label>Seed<input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="-1" /></label></div>}
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Опишите, что вы хотите создать…" />
            {generating && job && <div className="progress-card"><div className="progress-head"><div><strong>{job.phase || 'Генерация'}</strong><span>{job.status_text || 'WanGP обрабатывает запрос'}</span></div><b>{percent}%</b></div><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.max(2, percent)}%` }} /></div>{job.current_step != null && job.total_steps != null && <div className="step-line">Шаг {job.current_step} из {job.total_steps}{job.model_name ? ` · ${job.model_name}` : ''}</div>}<button className="cancel" onClick={cancelGeneration}><XCircle size={15} /> Остановить</button></div>}
            <div className="creator-footer"><span className="hint">Генерация выполняется локально на вашем компьютере</span><button className="generate" disabled={!prompt.trim() || generating || !engineReady || mode !== 'image'} onClick={generate}>{generating ? <><LoaderCircle size={18} className="spin" /> Генерация…</> : <><Sparkles size={18} /> Создать</>}</button></div>
            {error && <div className="error-box">{error}</div>}
            {job?.status === 'cancelled' && <div className="result-box"><strong>Генерация остановлена</strong><div className="result-file">Задача отменена пользователем.</div></div>}
            {imageResults.length > 0 && <div className="result-gallery">{imageResults.map((file) => <img key={file} src={`${API}/file?path=${encodeURIComponent(file)}`} alt="Результат генерации" />)}</div>}
            {files.length > 0 && imageResults.length === 0 && <div className="result-box"><strong>Готово</strong>{files.map((file) => <div key={file} className="result-file">{file}</div>)}</div>}
          </div>
          <div className="section-title"><h3>Последние проекты</h3><button className="link">Показать все</button></div><div className="empty-state"><div className="empty-icon"><FolderOpen size={24} /></div><strong>Пока здесь пусто</strong><span>Создайте первый материал — он появится здесь.</span></div>
        </section>}
        {active !== 'home' && <section className="placeholder"><div className="empty-icon"><Sparkles size={24} /></div><h2>Раздел готовится</h2><p>Основа приложения уже работает. Следующий этап — проекты, история и остальные генераторы.</p></section>}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
