import json
import os
from flask import Blueprint, jsonify, request

from backend.utils import _json_error
from backend.web.context import AppContext

try:
    import requests
except Exception:
    requests = None


def _get_chat_api_key(base_dir: str):
    key = os.environ.get('OPENAI_API_KEY')
    if key:
        return key
    try:
        path = os.path.join(base_dir, 'chat_key.txt')
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                line = f.readline().strip()
                if line:
                    return line
    except Exception:
        pass
    return None


def create_chat_blueprint(ctx: AppContext) -> Blueprint:
    bp = Blueprint('chat', __name__)

    @bp.route('/api/chat', methods=['POST'])
    def api_chat():
        try:
            payload = request.get_json(force=True)
        except Exception:
            return _json_error('Niepoprawny JSON w ciele żądania.', status=400)

        if not payload or 'message' not in payload:
            return _json_error("Oczekiwany JSON: { 'message': '...' }", status=400)

        user_message = str(payload.get('message', '')).strip()
        if not user_message:
            return jsonify({'error': 'Pusta wiadomość'}), 400

        requested_model = str(payload.get('model', '')).strip() or None
        requested_temperature = payload.get('temperature', None)
        requested_max_tokens = payload.get('max_tokens', None)
        assistant_role = payload.get('assistant_role')
        custom_system = payload.get('system')

        api_key = _get_chat_api_key(ctx.base_dir)
        if not api_key:
            return _json_error('Brak klucza API. Ustaw OPENAI_API_KEY lub utwórz chat_key.txt w katalogu projektu.', status=500)

        allowed_models = ['gpt-3.5-turbo', 'gpt-4', 'gpt-5-pro']
        model = 'gpt-3.5-turbo'
        if requested_model:
            if requested_model in allowed_models:
                model = requested_model
            else:
                return _json_error(f'Nieznany model: {requested_model}', status=400, allowed_models=allowed_models)

        temperature = 0.6
        try:
            if requested_temperature is not None:
                temperature = float(requested_temperature)
                if not (0.0 <= temperature <= 2.0):
                    raise ValueError('temperature must be between 0.0 and 2.0')
        except Exception as e:
            return _json_error(f'Niepoprawna temperatura: {e}', status=400)

        model_max_tokens = {
            'gpt-3.5-turbo': 2000,
            'gpt-4': 8000,
            'gpt-5-pro': 32768,
        }
        model_cap = model_max_tokens.get(model, 2000)
        max_tokens = 500
        try:
            if requested_max_tokens is not None:
                max_tokens = int(requested_max_tokens)
                if max_tokens <= 0 or max_tokens > model_cap:
                    raise ValueError(f'max_tokens musi być w zakresie 1..{model_cap} dla modelu {model}')
        except Exception as e:
            return _json_error(f'Niepoprawny max_tokens: {e}', status=400)

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        assistant_role_presets = {
            'care_assistant': (
                "You are a caring assistant specialized in supporting caregivers of autistic patients. "
                "Answer concisely, using calm, respectful language. Provide practical, evidence-informed suggestions for caregiving, "
                "sensory regulation, communication strategies and safety. When giving advice, explain briefly why and give one concrete next step. "
                "Do NOT provide medical diagnoses or replace professional medical advice; when appropriate, recommend consulting a qualified clinician."
            ),
            'default': (
                "You are a helpful assistant. Reply politely and helpfully."
            )
        }

        system_message = None
        if assistant_role:
            if assistant_role in assistant_role_presets:
                system_message = assistant_role_presets[assistant_role]
            else:
                return _json_error(f'Nieznana rola assistant_role: {assistant_role}', status=400, allowed_roles=list(assistant_role_presets.keys()))
        if custom_system:
            try:
                cs = str(custom_system)
                if len(cs) > 4000:
                    return _json_error('Custom system prompt jest za długi (limit 4000 znaków).', status=400)
                system_message = cs
            except Exception:
                return _json_error('Niepoprawny system prompt.', status=400)

        messages = []
        if system_message:
            messages.append({'role': 'system', 'content': system_message})
        messages.append({'role': 'user', 'content': user_message})

        body = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }

        try:
            responses_models = {'gpt-5-pro'}
            if model in responses_models:
                body_resp = {
                    'model': model,
                    'input': (system_message + "\n\n" + user_message) if system_message else user_message,
                    'max_output_tokens': max_tokens,
                }
                if requests is not None:
                    resp = requests.post('https://api.openai.com/v1/responses', headers=headers, json=body_resp, timeout=30)
                    if resp.status_code != 200:
                        try:
                            return jsonify({'error': 'Błąd od OpenAI', 'details': resp.text}), resp.status_code
                        except Exception:
                            return jsonify({'error': 'Błąd od OpenAI', 'status': resp.status_code}), resp.status_code
                    data = resp.json()
                else:
                    import urllib.request as _ur
                    req = _ur.Request('https://api.openai.com/v1/responses', data=json.dumps(body_resp).encode('utf-8'), headers=headers)
                    with _ur.urlopen(req, timeout=30) as r:
                        raw = r.read().decode('utf-8')
                    data = json.loads(raw)
            else:
                if requests is not None:
                    resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=body, timeout=15)
                    if resp.status_code != 200:
                        try:
                            return jsonify({'error': 'Błąd od OpenAI', 'details': resp.text}), resp.status_code
                        except Exception:
                            return jsonify({'error': 'Błąd od OpenAI', 'status': resp.status_code}), resp.status_code
                    data = resp.json()
                else:
                    import urllib.request as _ur
                    req = _ur.Request('https://api.openai.com/v1/chat/completions', data=json.dumps(body).encode('utf-8'), headers=headers)
                    with _ur.urlopen(req, timeout=15) as r:
                        raw = r.read().decode('utf-8')
                    data = json.loads(raw)

            reply = None
            try:
                if isinstance(data, dict) and 'choices' in data:
                    choices = data.get('choices')
                    if choices and len(choices) > 0:
                        first = choices[0]
                        if isinstance(first, dict):
                            msg = first.get('message')
                            if isinstance(msg, dict):
                                content = msg.get('content')
                                if isinstance(content, str):
                                    reply = content
                                elif isinstance(content, dict):
                                    reply = content.get('text') or content.get('content')
                            else:
                                reply = first.get('text') or None

                if not reply and isinstance(data, dict) and 'output' in data:
                    out = data.get('output')
                    if isinstance(out, list) and len(out) > 0:
                        parts = []
                        for item in out:
                            if isinstance(item, dict):
                                content = item.get('content')
                                if isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict):
                                            if 'text' in c:
                                                parts.append(c.get('text'))
                                            elif 'type' in c and c.get('type') == 'output_text' and 'text' in c:
                                                parts.append(c.get('text'))
                                        elif isinstance(c, str):
                                            parts.append(c)
                                elif isinstance(content, str):
                                    parts.append(content)
                        if parts:
                            reply = "\n".join([p for p in parts if p])

                if not reply and isinstance(data, dict):
                    if 'reply' in data:
                        reply = data.get('reply')
                    elif 'message' in data and isinstance(data.get('message'), str):
                        reply = data.get('message')

            except Exception:
                reply = None

            if not reply:
                try:
                    reply = json.dumps(data)[:2000]
                except Exception:
                    reply = str(data)[:2000]

            return jsonify({'reply': reply})
        except Exception as e:
            return _json_error('Błąd podczas wysyłania żądania do API czatu', status=500, details=str(e))

    return bp
