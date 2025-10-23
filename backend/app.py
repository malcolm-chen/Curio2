from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
from openai import OpenAI
import os
import io
import json
import time
from dotenv import load_dotenv
from prompts.eval import scaffolding, scienceqa, reflection

load_dotenv()
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", os.getenv("VUE_APP_URL")]}})

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global variable to track conversation start times
conversation_start_times = {}

# System prompt for Curio
CURIO_SYSTEM_PROMPT = """## Role
- You are Curio, a friendly and encouraging science chatbot for children aged 8-10. The system shows an image, and your task is to prompt the child to discover the scientific phenomenon behind the image. Once the child has discovered the scientific phenomenon, you will prompt the child to ask questions to discover the science knowledge behind the phenomenon. You can set the scene as a 'detection', where the child is a detective and you are the assistant.
"""

state_history = []

def state_classification(state, messages, phenomenon):
    # Load prompt from the txt file
    if state == 'discover':
        return 'scienceqa_init'
    if state in ['greet', 'scaffolding']:
        eval_prompt = format_prompt(scaffolding, phenomenon)
    elif state in ['scienceqa_init', 'scienceqa']:
        eval_prompt = format_prompt(scienceqa, phenomenon)
    elif state in ['reflection']:
        eval_prompt = format_prompt(reflection, phenomenon)

    messages = messages + [{"role": "system", "content": eval_prompt}]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500,
        temperature=0.7
    )
    eval_state = response.choices[0].message.content.strip().lower().replace('<', '').replace('>', '')
    return eval_state

def state_update(current_state, eval_state):
    next_state = eval_state
    if eval_state == 'discover':
        next_state = 'discover'
    elif eval_state == 'scienceqa_init':
        next_state = 'scienceqa_init'
    elif eval_state == 'scienceqa':
        if len(state_history) > 0 and state_history[-1] == 'scaffolding':
            next_state = 'scienceqa_init'
        elif not 'reflection' in state_history:
            total_sci = state_history.count('scienceqa')
            if total_sci >= 2:
                next_state = 'reflection'
            else:
                next_state = 'scienceqa'
        else:
            reflection_index = state_history.index('reflection')
            post_ref_sci = state_history[reflection_index:].count('scienceqa')
            num_of_reflection = state_history.count('reflection')
            if num_of_reflection >= 2:
                next_state = 'close'
            else:
                next_state = 'reflection' if post_ref_sci >= 2 else 'scienceqa'
    elif eval_state == 'reflection':
        next_state = 'reflection'
    elif eval_state == 'scaffolding':
        num_of_scaffolding = state_history.count('scaffolding')
        if num_of_scaffolding >= 1:
            next_state = 'scienceqa_init'
        else:
            next_state = 'scaffolding'
    elif eval_state == 'close':
        next_state = 'close'
    else:
        next_state = 'scienceqa'
    
    state_history.append(next_state)
    return next_state

def state_prompt_classification(state):
    if state == 'greet':
        return open('prompts/greet.txt', 'r').read()
    elif state == 'scaffolding':
        return open('prompts/scaffolding.txt', 'r').read()
    elif state == 'discover':
        return open('prompts/discover.txt', 'r').read()
    elif state == 'scienceqa_init':
        return open('prompts/scienceqa_init.txt', 'r').read()
    elif state == 'scienceqa':
        return open('prompts/scienceqa.txt', 'r').read()
    elif state == 'reflection':
        return open('prompts/reflection.txt', 'r').read()
    elif state == 'close':
        return open('prompts/close.txt', 'r').read()
    else:
        return open('prompts/scienceqa.txt', 'r').read()

def format_prompt(state_prompt, phenomenon='balloon'):
    if phenomenon == 'balloon':
        if '## Image Content' in state_prompt:
            state_prompt = state_prompt.replace('## Image Content', '## Image Content\n- In the living room, a child wears a fleece sweater and holds a balloon near her hair. Suddenly, her hair stands straight up, each strand reaching away from the others like a spiky crown. The hairs are trying to get away from each other! Nearby, her sibling holds a balloon near her own hair, but nothing happens. The sibling\'s hair stays flat as she stares at her, amazed.')
        if '## Scientific Phenomenon' in state_prompt:
            state_prompt = state_prompt.replace('## Scientific Phenomenon', '## Scientific Phenomenon\nThe right child\'s hair stands straight up.')
        if '## Scientific Knowledge' in state_prompt:
            state_prompt = state_prompt.replace('## Scientific Knowledge', '## Scientific Knowledge\nWhen you rub the balloon, you’re giving it electric energy. That energy creates a force strong enough to move your hair without touching it. The hairs also get energy and move away from each other. This shows how energy can cause motion without direct contact.')
    return state_prompt

def knowledge_retrieval(messages):
    # Load prompt from the txt file
    retrieval_prompt = open('prompts/knowledge_matching.txt', 'r').read()
    knowledge_base = open('knowledge/kg.json', 'r').read()
    knowledge_base = json.loads(knowledge_base)

    retrieval_prompt = retrieval_prompt + '\n\n## Knowledge Graph\n' + json.dumps(knowledge_base)
    messages = messages + [{"role": "system", "content": retrieval_prompt}]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500,
        temperature=0.7
    )
    kg_raw = response.choices[0].message.content.strip().lower()
    try:
        kg_list = json.loads(kg_raw)
        kg_content = [knowledge_base[component.strip()] for component in kg_list]
        return '\n\n'.join(kg_content)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing knowledge graph: {e}")
        return ""

@app.route('/chat', methods=['POST'])
def chat_completion():
    """Generate chat response and a next_state using OpenAI"""
    try:
        # Record start time for latency tracking
        start_time = time.time()
        session_id = request.remote_addr  # Use IP as session identifier
        conversation_start_times[session_id] = start_time
        
        data = request.get_json()
        messages = data.get('messages', [])
        state = (data.get('state') or 'greet').strip()
        print(f"state: {state}")
        eval_state = state_classification(state, messages, 'balloon')
        print(f"eval_state: {eval_state}")
        current_state = state_update(state, eval_state)
        print(f"current_state: {current_state}")
        state_prompt = state_prompt_classification(current_state)

        if current_state == 'scienceqa' or current_state == 'reflection':
            kg = knowledge_retrieval(messages)
            print(f"kg: {kg}")
            state_prompt = state_prompt + '\n\n## Relevant Knowledge Component\n' + kg
        
        state_prompt = format_prompt(state_prompt, 'balloon')

        system_message = {"role": "system", "content": CURIO_SYSTEM_PROMPT}
        all_messages = [system_message] + messages + [{"role": "system", "content": state_prompt}]

        # Generate response using GPT-4
        response = client.chat.completions.create(
            model="gpt-4",
            messages=all_messages,
            max_tokens=500,
            temperature=0.7
        )

        content = response.choices[0].message.content or ""

        return jsonify({'response': content, 'next_state': current_state})

    except Exception as e:
        print(f"Chat completion error: {e}")
        return jsonify({'error': 'Chat completion failed'}), 500

@app.route('/speech', methods=['POST'])
def generate_speech():
    """Generate speech audio using OpenAI TTS"""
    try:
        # Calculate latency from conversation start to audio generation
        session_id = request.remote_addr
        end_time = time.time()
        
        if session_id in conversation_start_times:
            total_latency = end_time - conversation_start_times[session_id]
            print(f"🎯 Total latency (user message → audio response): {total_latency:.2f} seconds")
            # Clean up the stored start time
            del conversation_start_times[session_id]
        else:
            print("⚠️  No start time found for session, cannot calculate latency")
        
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate speech using OpenAI TTS
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
            response_format="mp3"
        )
        
        # Return the audio data
        return response.content, 200, {
            'Content-Type': 'audio/mpeg',
            'Content-Disposition': 'attachment; filename=speech.mp3'
        }
    
    except Exception as e:
        print(f"Speech generation error: {e}")
        return jsonify({'error': 'Speech generation failed'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)