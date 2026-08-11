"""Local backend bridge between AI Creator Studio and WanGP's headless session API."""
from __future__ import annotations
import json,mimetypes,os,sys,threading,uuid
from dataclasses import asdict,is_dataclass
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs,urlparse
ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
HOST="127.0.0.1";PORT=int(os.environ.get("AI_CREATOR_PORT","18765"));OUTPUT_DIR=(ROOT/"ai_creator_studio"/"projects"/"generated").resolve();DATA_DIR=(ROOT/"ai_creator_studio"/"projects"/"data").resolve();_session=None;_session_lock=threading.Lock();_jobs={};_render_jobs={}
def get_session():
 global _session
 with _session_lock:
  if _session is None:
   from shared.api import init
   _session=init(root=ROOT,output_dir=OUTPUT_DIR,console_output=False)
  return _session
def get_store():
 from studio_projects import ProjectStore
 return ProjectStore(DATA_DIR)
def get_timeline():
 from studio_timeline import TimelineStore
 return TimelineStore(DATA_DIR)
def jsonable(value:Any)->Any:
 if value is None or isinstance(value,(str,int,float,bool)): return value
 if isinstance(value,Path): return str(value)
 if is_dataclass(value): return jsonable(asdict(value))
 if isinstance(value,dict): return {str(k):jsonable(v) for k,v in value.items()}
 if isinstance(value,(list,tuple)): return [jsonable(v) for v in value]
 if hasattr(value,"model_dump"): return jsonable(value.model_dump())
 if hasattr(value,"__dict__"): return jsonable(value.__dict__)
 return str(value)
def model_info():
 try:return {"ok":True,"models":jsonable(get_session().list_model_metadata(include_availability=True))}
 except Exception as exc:return {"ok":False,"error":str(exc),"models":[]}
def choose_image_model(models):
 for model in models:
  mt=str(model.get("model_type") or "").strip()
  if not mt or (model.get("availability") or {}).get("available") is False:continue
  text=json.dumps(model,ensure_ascii=False).lower()
  if any(x in text for x in ("text-to-image","text to image","image generation","image","t2i")):return mt
 return None
def event_update(job,event):
 data=getattr(event,"data",None);name=data.__class__.__name__ if data is not None else ""
 if name=="ProgressUpdate":job.update(progress=max(0,min(100,int(getattr(data,"progress",0) or 0)))/100,phase=str(getattr(data,"phase","") or ""),status_text=str(getattr(data,"status","") or ""),current_step=getattr(data,"current_step",None),total_steps=getattr(data,"total_steps",None))
 elif name=="PreviewUpdate":job.update(preview_available=getattr(data,"image",None) is not None,phase=str(getattr(data,"phase","") or job.get("phase","")))
 elif str(getattr(event,"kind","")) in {"error","failed"}:job["error"]=str(data or "WanGP сообщила об ошибке")
def run_image(job_id,prompt,overrides):
 job=_jobs[job_id]
 try:
  session=get_session();job.update(status="preparing",progress=.02);models=session.list_model_metadata(include_availability=True);model_type=str(overrides.get("model_type") or choose_image_model(models) or "").strip()
  if not model_type:raise RuntimeError("WanGP не сообщил доступную модель для генерации изображения")
  schema=session.get_model_schema(model_type);settings=dict(schema.get("default_settings") or {});settings.update({k:v for k,v in overrides.items() if k!="model_type"});settings.update(model_type=model_type,prompt=prompt);settings.setdefault("repeat_generation",1);settings.setdefault("batch_size",1);job.update(status="running",progress=.05,model_type=model_type,model_name=schema.get("name"));sj=session.submit_task(settings);job["session_job"]=sj
  while not sj.done:
   event=sj.events.get(timeout=.25)
   if event is not None:event_update(job,event)
  result=sj.result();payload=jsonable(result);success=bool(getattr(result,"success",False));cancelled=bool(getattr(result,"cancelled",False));generated=payload.get("generated_files",[]) if isinstance(payload,dict) else [];pid=job.get("project_id")
  if success and pid:
   store=get_store();timeline=get_timeline()
   for path in generated:
    asset=store.add_asset(pid,"image",prompt,str(path),{"model_type":model_type})
    timeline.add(pid,{"kind":"image","track":"video","path":str(path),"asset_id":asset["id"],"name":Path(str(path)).name,"start":timeline.get(pid).get("duration",0),"duration":5,"volume":1})
  job.update(status="cancelled" if cancelled else ("completed" if success else "failed"),progress=1 if success else job.get("progress",0),result=payload)
  if not success:job["error"]="; ".join(str(e) for e in getattr(result,"errors",())) or "WanGP не смог выполнить генерацию"
 except Exception as exc:job.update(status="failed",progress=0,error=str(exc))
 finally:job.pop("session_job",None)
def safe_output_file(value):
 path=Path(value).expanduser().resolve()
 if path!=OUTPUT_DIR and OUTPUT_DIR not in path.parents:raise ValueError("Файл находится вне каталога результатов")
 if not path.is_file():raise FileNotFoundError(path)
 return path
def run_render(job_id,project_id,timeline):
 job=_render_jobs[job_id]
 try:
  from studio_render import render_timeline
  job.update(status="rendering",progress=.02,phase="Подготовка")
  output=OUTPUT_DIR/project_id/f"{job_id}.mp4"
  result=render_timeline(timeline,output,ROOT)
  store=get_store();asset=store.add_asset(project_id,"video","Экспорт Timeline",str(result),{"duration":timeline.get("duration",0),"fps":timeline.get("fps",30)})
  job.update(status="completed",progress=1,phase="Готово",output=str(result),asset=asset)
 except Exception as exc:job.update(status="failed",progress=0,error=str(exc))
class Handler(BaseHTTPRequestHandler):
 def send_json(self,status,payload):
  data=json.dumps(payload,ensure_ascii=False).encode();self.send_response(status);self.send_header("Access-Control-Allow-Origin","*");self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
 def read_json(self):
  n=int(self.headers.get("Content-Length","0"));return json.loads(self.rfile.read(n) or b"{}")
 def do_OPTIONS(self):
  self.send_response(204);self.send_header("Access-Control-Allow-Origin","*");self.send_header("Access-Control-Allow-Headers","Content-Type");self.send_header("Access-Control-Allow-Methods","GET,POST,PUT,DELETE,OPTIONS");self.end_headers()
 def do_GET(self):
  try:
   p=urlparse(self.path)
   if p.path=="/health":self.send_json(200,{"ok":True,"engine":"WanGP","stage":"session"})
   elif p.path=="/hardware":
    from studio_hardware import detect_hardware
    self.send_json(200,detect_hardware())
   elif p.path=="/models":self.send_json(200,model_info())
   elif p.path.startswith("/models/") and p.path.endswith("/schema"):self.send_json(200,jsonable(get_session().get_model_schema(p.path[len("/models/"):-len("/schema") ])))
   elif p.path=="/projects":self.send_json(200,{"ok":True,"projects":get_store().list_projects()})
   elif p.path.startswith("/projects/") and p.path.endswith("/assets"):self.send_json(200,{"ok":True,"assets":get_store().list_assets(p.path.split("/")[2])})
   elif p.path.startswith("/projects/") and p.path.endswith("/timeline"):self.send_json(200,{"ok":True,"timeline":get_timeline().get(p.path.split("/")[2])})
   elif p.path=="/file":path=safe_output_file(parse_qs(p.query).get("path",[""])[0]);data=path.read_bytes();self.send_response(200);self.send_header("Access-Control-Allow-Origin","*");self.send_header("Content-Type",mimetypes.guess_type(path.name)[0] or "application/octet-stream");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
   elif p.path.startswith("/jobs/"):
    job=_jobs.get(p.path.rsplit("/",1)[-1]);self.send_json(200 if job else 404,{k:v for k,v in job.items() if k!="session_job"} if job else {"error":"Задача не найдена"})
   elif p.path.startswith("/renders/"):
    job=_render_jobs.get(p.path.rsplit("/",1)[-1]);self.send_json(200 if job else 404,job or {"error":"Рендер не найден"})
   else:self.send_json(404,{"ok":False,"error":"Не найдено"})
  except Exception as exc:self.send_json(500,{"ok":False,"error":str(exc)})
 def do_POST(self):
  try:
   p=urlparse(self.path);body=self.read_json()
   if p.path=="/projects":project=get_store().create_project(str(body.get("name","Новый проект")));self.send_json(201,{"ok":True,"project":project});return
   if p.path.startswith("/projects/") and p.path.endswith("/timeline/items"):
    pid=p.path.split("/")[2];self.send_json(201,{"ok":True,"timeline":get_timeline().add(pid,body)});return
   if p.path.startswith("/projects/") and p.path.endswith("/render"):
    pid=p.path.split("/")[2];timeline=get_timeline().get(pid);jid=uuid.uuid4().hex;_render_jobs[jid]={"id":jid,"status":"queued","progress":0,"phase":"","project_id":pid};threading.Thread(target=run_render,args=(jid,pid,timeline),daemon=True).start();self.send_json(202,{"ok":True,"job_id":jid});return
   if p.path=="/generate/image":
    prompt=str(body.get("prompt","")).strip()
    if not prompt:self.send_json(400,{"ok":False,"error":"Введите описание изображения"});return
    jid=uuid.uuid4().hex;_jobs[jid]={"id":jid,"status":"queued","progress":0.0,"phase":"","project_id":body.get("project_id")};threading.Thread(target=run_image,args=(jid,prompt,body.get("settings") or {}),daemon=True).start();self.send_json(202,{"ok":True,"job_id":jid});return
   if p.path.startswith("/jobs/") and p.path.endswith("/cancel"):
    job=_jobs.get(p.path.split("/")[2]);sj=job.get("session_job") if job else None
    if not job:self.send_json(404,{"ok":False,"error":"Задача не найдена"});return
    if sj is None:self.send_json(409,{"ok":False,"error":"Генерация ещё не запустилась"});return
    sj.cancel();job["status"]="cancelling";self.send_json(202,{"ok":True,"status":"cancelling"});return
   self.send_json(404,{"ok":False,"error":"Не найдено"})
  except Exception as exc:self.send_json(500,{"ok":False,"error":str(exc)})
 def do_PUT(self):
  try:
   p=urlparse(self.path);body=self.read_json()
   parts=[x for x in p.path.split("/") if x]
   if len(parts)==4 and parts[0]=="projects" and parts[2]=="timeline" and parts[3]=="items":
    self.send_json(400,{"ok":False,"error":"Не указан ID клипа"});return
   if len(parts)==5 and parts[0]=="projects" and parts[2]=="timeline" and parts[3]=="items":
    self.send_json(200,{"ok":True,"timeline":get_timeline().update_item(parts[1],parts[4],body)});return
   if len(parts)==3 and parts[0]=="projects" and parts[2]=="timeline":
    self.send_json(200,{"ok":True,"timeline":get_timeline().save(parts[1],body)});return
   self.send_json(404,{"ok":False,"error":"Не найдено"})
  except KeyError as exc:self.send_json(404,{"ok":False,"error":str(exc)})
  except Exception as exc:self.send_json(500,{"ok":False,"error":str(exc)})
 def do_DELETE(self):
  try:
   p=urlparse(self.path);parts=[x for x in p.path.split("/") if x]
   if len(parts)==5 and parts[0]=="projects" and parts[2]=="timeline" and parts[3]=="items":
    self.send_json(200,{"ok":True,"timeline":get_timeline().delete_item(parts[1],parts[4])});return
   self.send_json(404,{"ok":False,"error":"Не найдено"})
  except KeyError as exc:self.send_json(404,{"ok":False,"error":str(exc)})
  except Exception as exc:self.send_json(500,{"ok":False,"error":str(exc)})
 def log_message(self,*_args):return
if __name__=="__main__":OUTPUT_DIR.mkdir(parents=True,exist_ok=True);DATA_DIR.mkdir(parents=True,exist_ok=True);ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
