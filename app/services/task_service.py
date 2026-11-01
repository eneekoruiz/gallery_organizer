# -*- coding: utf-8 -*-
"""
task_service.py  -  Sistema Central de Tareas en Background

Gestiona todas las operaciones async de la app con:
- Estado completo (pending / running / done / error)
- Stacktrace completo si falla
- Retry automatico (max 1 vez)
- API REST para consultar y reintentar
"""
import threading
import traceback
import uuid
import time
from flask import jsonify, request

_task_registry = {}
_task_lock = threading.Lock()
MAX_TASKS = 100


class Task:
    def __init__(self, task_id, name, fn, args=(), kwargs=None, retry=True):
        self.task_id = task_id
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}
        self.retry = retry
        self.attempts = 0
        self.status = "pending"
        self.progress = ""
        self.result = None
        self.error = None
        self.traceback_str = None
        self.started_at = None
        self.finished_at = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "traceback": self.traceback_str,
            "attempts": self.attempts,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.finished_at - self.started_at, 2) if self.finished_at and self.started_at else None
        }

    def run(self):
        self.attempts += 1
        self.status = "running"
        self.started_at = time.time()
        try:
            result = self.fn(self, *self.args, **self.kwargs)
            self.result = result
            self.status = "done"
        except Exception as e:
            self.error = str(e)
            self.traceback_str = traceback.format_exc()
            if self.retry and self.attempts < 2:
                self.status = "retrying"
                time.sleep(1)
                self.run()
            else:
                self.status = "error"
        finally:
            self.finished_at = time.time()
        return self


def submit_task(name, fn, args=(), kwargs=None, retry=True):
    task_id = str(uuid.uuid4())[:8]
    task = Task(task_id, name, fn, args, kwargs, retry)
    with _task_lock:
        if len(_task_registry) >= MAX_TASKS:
            done_keys = [k for k, v in _task_registry.items() if v.status in ("done", "error")]
            for k in done_keys[:20]:
                del _task_registry[k]
        _task_registry[task_id] = task
    threading.Thread(target=task.run, daemon=True).start()
    return task_id


def get_task(task_id):
    return _task_registry.get(task_id)


def retry_task(task_id):
    task = _task_registry.get(task_id)
    if not task:
        return None
    task.status = "pending"
    task.error = None
    task.traceback_str = None
    task.result = None
    task.attempts = 0
    threading.Thread(target=task.run, daemon=True).start()
    return task


def api_task_status():
    task_id = request.view_args.get("task_id") or request.args.get("task_id")
    task = _task_registry.get(task_id)
    if not task:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(task.to_dict())


def api_task_list():
    with _task_lock:
        tasks = [t.to_dict() for t in _task_registry.values()]
    tasks.sort(key=lambda x: x.get("started_at") or 0, reverse=True)
    return jsonify(tasks)


def api_task_retry():
    task_id = request.view_args.get("task_id") or (request.json or {}).get("task_id")
    task = retry_task(task_id)
    if not task:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify({"status": "started", "task_id": task_id})
