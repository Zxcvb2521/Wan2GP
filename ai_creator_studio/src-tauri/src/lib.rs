use serde::Serialize;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, State};

#[derive(Default)]
pub struct RuntimeState {
    child: Mutex<Option<Child>>,
}

#[derive(Debug, Serialize)]
pub struct EngineStatus {
    pub running: bool,
    pub runtime_dir: String,
    pub engine_dir: String,
}

fn runtime_root(app: &AppHandle) -> Result<PathBuf, String> {
    let resource_dir = app.path().resource_dir().map_err(|e| e.to_string())?;
    let candidates = [
        resource_dir.join("runtime"),
        resource_dir.parent().unwrap_or(&resource_dir).join("runtime"),
        resource_dir.parent().unwrap_or(&resource_dir).parent().unwrap_or(&resource_dir).join("runtime"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").join("ai_creator_studio").join("runtime"),
    ];
    candidates.iter().find(|path| path.join("WanGP").exists()).cloned().ok_or_else(|| {
        format!("Встроенный runtime WanGP не найден. Проверены: {}", candidates.iter().map(|p| p.display().to_string()).collect::<Vec<_>>().join("; "))
    })
}

fn development_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
}

fn engine_root(app: &AppHandle) -> Result<PathBuf, String> {
    let runtime = runtime_root(app)?;
    let packaged_engine = runtime.join("WanGP");
    let dev_root = development_root();
    if dev_root.join("shared").exists() && dev_root.join("wgp.py").exists() {
        return Ok(dev_root);
    }
    Ok(packaged_engine)
}

fn python_command(runtime: &PathBuf) -> Command {
    let packaged = if cfg!(windows) { runtime.join("python").join("python.exe") } else { runtime.join("python").join("bin").join("python3") };
    if packaged.exists() {
        return Command::new(packaged);
    }
    if cfg!(windows) { Command::new("python") } else { Command::new("python3") }
}

#[tauri::command]
pub fn engine_status(app: AppHandle, state: State<'_, RuntimeState>) -> Result<EngineStatus, String> {
    let runtime = runtime_root(&app)?;
    let engine = engine_root(&app)?;
    let running = state.child.lock().map_err(|_| "Не удалось получить состояние движка")?.as_ref().is_some();
    Ok(EngineStatus { running, runtime_dir: runtime.display().to_string(), engine_dir: engine.display().to_string() })
}

#[tauri::command]
pub fn start_engine(app: AppHandle, state: State<'_, RuntimeState>) -> Result<String, String> {
    let runtime = runtime_root(&app)?;
    let engine = engine_root(&app)?;
    let entry = if engine.join("ai_creator_studio").join("runtime").join("WanGP").join("studio_backend.py").exists() {
        engine.join("ai_creator_studio").join("runtime").join("WanGP").join("studio_backend.py")
    } else {
        engine.join("studio_backend.py")
    };
    if !entry.exists() { return Err(format!("Backend AI Creator не найден: {}", entry.display())); }

    let mut guard = state.child.lock().map_err(|_| "Не удалось получить состояние движка")?;
    if guard.is_some() { return Ok("Движок уже запущен".into()); }

    let child = python_command(&runtime).arg(&entry)
        .current_dir(&engine)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("Не удалось запустить WanGP: {e}"))?;
    *guard = Some(child);
    Ok("Движок запущен".into())
}

#[tauri::command]
pub fn stop_engine(state: State<'_, RuntimeState>) -> Result<String, String> {
    let mut guard = state.child.lock().map_err(|_| "Не удалось получить состояние движка")?;
    if let Some(mut child) = guard.take() { let _ = child.kill(); let _ = child.wait(); return Ok("Движок остановлен".into()); }
    Ok("Движок не был запущен".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(RuntimeState::default())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![engine_status, start_engine, stop_engine])
        .run(tauri::generate_context!())
        .expect("error while running AI Creator Studio");
}
