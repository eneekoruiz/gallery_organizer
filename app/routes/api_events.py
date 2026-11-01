from flask import Blueprint, Response, stream_with_context
import json
import time
from app.services.events import sse_manager

api_events_bp = Blueprint('api_events', __name__)

@api_events_bp.route('/api/stream/events')
def stream_events():
    def event_stream():
        q = sse_manager.listen()
        try:
            # Send initial connection success event
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                msg = q.get()
                yield f"data: {json.dumps(msg)}\n\n"
        except GeneratorExit:
            sse_manager.remove(q)
            
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
