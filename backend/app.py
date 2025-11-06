from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
from openai import OpenAI
import os
import io
import json
import time
import base64
from dotenv import load_dotenv
from prompts.eval import scaffolding, scienceqa, reflection
from prompts.scienceqa import no_question, level_0, level_1, level_2, level_3, level_4

load_dotenv()
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", os.getenv("VUE_APP_URL")]}})

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global variable to track conversation start times
conversation_start_times = {}

# System prompt for Curio
CURIO_SYSTEM_PROMPT = """
<System Introduction>
You are Curio, a friendly and encouraging science chatbot for children aged 8-10. The system shows an image, and your task is to prompt the child to discover the scientific phenomenon behind the image. Once the child has discovered the scientific phenomenon, you will prompt the child to ask questions to discover the science knowledge behind the phenomenon.
</System Introduction>
"""

state_history = []
scienceqa_history = []

def state_classification(state, messages, phenomenon):
    # Load prompt from the txt file
    if state in ['greet', 'scaffolding']:
        eval_prompt = format_prompt(scaffolding, phenomenon, messages)
    elif state in ['discover', 'scienceqa']:
        eval_prompt = format_prompt(scienceqa, phenomenon, messages)
    elif state in ['reflection']:
        eval_prompt = format_prompt(reflection, phenomenon, messages)
    
    messages = [{"role": "system", "content": eval_prompt}]
    # print(f"messages: {messages}")

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500
    )

    # response = client.responses.create(
    #         model="gpt-5",
    #         input = messages,
    #         reasoning={ "effort": "low" },
    #     )

    # content = response.output_text or ""
    content = response.choices[0].message.content or ""
    eval_state = content.strip().lower().replace('<', '').replace('>', '')
    return eval_state

def state_update(current_state, eval_state):
    next_state = eval_state
    if eval_state == 'discover':
        next_state = 'discover'
    elif eval_state == 'scienceqa':
        if len(state_history) > 0 and state_history[-1] == 'scaffolding':
            next_state = 'discover'
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
            next_state = 'discover'
        else:
            next_state = 'scaffolding'
    elif eval_state == 'close':
        next_state = 'close'
    else:
        next_state = 'scienceqa'
    
    state_history.append(next_state)
    return next_state

def state_prompt_classification(state, child_question_level=None):
    if state == 'greet':
        return open('prompts/greet.txt', 'r').read()
    elif state == 'scaffolding':
        return open('prompts/scaffolding.txt', 'r').read()
    elif state == 'discover':
        return open('prompts/discover.txt', 'r').read()
    elif state == 'scienceqa':
        if child_question_level == 'no_question':
            return no_question
        elif child_question_level == 'irrelevant':
            return level_0
        elif child_question_level == 'factual':
            return level_1
        elif child_question_level == 'explanatory':
            return level_2
        elif child_question_level == 'general_causal':
            return level_3
        elif child_question_level == 'specific_causal':
            return level_4
    elif state == 'reflection':
        return open('prompts/reflection.txt', 'r').read()
    elif state == 'close':
        return open('prompts/close.txt', 'r').read()
    else:
        return open('prompts/scienceqa.txt', 'r').read()

def format_prompt(state_prompt, phenomenon='balloon', messages=None, child_question_level=None):
    if messages is None:
        messages = []
    
    phenomenon_json = json.load(open('prompts/phenomenon.json', 'r'))
    phenomenon_data = phenomenon_json.get(phenomenon, {})
    
    if '<Image Content>' in state_prompt:
        state_prompt = state_prompt.replace('<Image Content>', '<Image Content>\n' + phenomenon_data.get('image_content', ''))
    if '<Scientific Phenomenon>' in state_prompt:
        state_prompt = state_prompt.replace('<Scientific Phenomenon>', '<Scientific Phenomenon>\n' + phenomenon_data.get('phenomenon', ''))
    if '<Scientific Knowledge>' in state_prompt:
        state_prompt = state_prompt.replace('<Scientific Knowledge>', '<Scientific Knowledge>\n' + phenomenon_data.get('knowledge', ''))
    
    if '<Child\'s Question>' in state_prompt:
        state_prompt = state_prompt.replace('<Child\'s Question>', '<Child\'s Question>\n' + messages[-1]['content'].strip())
    if '<Conversation History>' in state_prompt:
        state_prompt = state_prompt.replace('<Conversation History>', '<Conversation History>\n' + json.dumps(messages))
    return state_prompt

def knowledge_retrieval(messages, phenomenon='balloon'):
    # Load prompt from the txt file
    retrieval_prompt = open('prompts/knowledge_matching.txt', 'r').read()
    retrieval_prompt = format_prompt(retrieval_prompt, phenomenon, messages)
    knowledge_base = open('knowledge/kg.json', 'r').read()
    knowledge_base = json.loads(knowledge_base)
    
    # Map phenomenon to knowledge base key
    phenomenon_map = {
        'balloon': 'Hair stands up near a balloon',
        'bend': 'Bending Water Stream with a Comb',
        'pepper': 'Pepper Leaping up to Spoon'
    }
    phenomenon_key = phenomenon_map.get(phenomenon, 'Hair stands up near a balloon')
    
    knowledge_concepts = list(knowledge_base[phenomenon_key]['concepts'].keys())

    retrieval_prompt = retrieval_prompt + '\n\n<Knowledge Components>\n' + json.dumps(knowledge_concepts) + '\n</Knowledge Components>'

    print(f"retrieval_prompt: {retrieval_prompt}")
    messages = [{"role": "system", "content": retrieval_prompt}]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=500
    )

    # response = client.responses.create(
    #         model="gpt-5",
    #         input = messages,
    #         reasoning={ "effort": "low" }
    #     )

    # content = response.output_text or ""
    content = response.choices[0].message.content or ""
    kg_raw = content.strip().lower()
    # print(f"kg_raw: {kg_raw}")
    return kg_raw

def format_kg(mode='definition', kg_raw='', phenomenon='balloon'):
    knowledge_base = open('knowledge/kg.json', 'r').read()
    knowledge_base = json.loads(knowledge_base)
    
    # Map phenomenon to knowledge base key
    phenomenon_map = {
        'balloon': 'Hair stands up near a balloon',
        'bend': 'Bending Water Stream with a Comb',
        'pepper': 'Pepper Leaping up to Spoon'
    }
    phenomenon_key = phenomenon_map.get(phenomenon, 'Hair stands up near a balloon')
    
    try:
        kg_list = json.loads(kg_raw)
        kg_content = ''
        for component in kg_list:
            definition = knowledge_base[phenomenon_key]['concepts'][component]['definition']
            explanation = knowledge_base[phenomenon_key]['concepts'][component]['explanation']
            if mode == 'definition':
                kg_content += "'" + component + "':\n\nDefinition: " + definition + '\n\n'
            elif mode == 'explanation':
                kg_content += "'" + component + "':\n\nExplanation: " + explanation + '\n\n'
            elif mode == 'definition_and_explanation':
                kg_content += "'" + component + "':\n\nDefinition: " + definition + '\n\nExplanation: ' + explanation + '\n\n'
        kg_content = kg_content.strip()
        print(f"kg_content: {kg_content}")
        return kg_content
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing knowledge graph: {e}")
        return ""

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

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
        image_path = data.get('image_path', '')  # Get the selected image path
        
        # Determine the phenomenon based on image path
        if 'balloon.jpg' in image_path:
            phenomenon = 'balloon'
        elif 'bend.jpg' in image_path:
            phenomenon = 'bend'
        elif 'pepper.jpg' in image_path:
            phenomenon = 'pepper'
        else:
            phenomenon = 'balloon'  # default fallback
        
        if state != 'scienceqa':
            print(f"state: {state}")
            eval_state = state_classification(state, messages, phenomenon)
            print(f"eval_state: {eval_state}")
            current_state = state_update(state, eval_state)
            print(f"current_state: {current_state}")
            
            # If transitioning to scienceqa, classify the question level immediately
            if current_state == 'scienceqa':
                child_question_level = state_classification(state, messages, phenomenon)
                scienceqa_history.append(child_question_level)
                print(f"child_question_level: {child_question_level}")
                print(f"scienceqa_history: {scienceqa_history}")
                state_prompt = state_prompt_classification(current_state, child_question_level)
            else:
                child_question_level = None
                state_prompt = state_prompt_classification(current_state)
        else:
            # Check if we should move to reflection based on qualified questions
            qualified_question_num = 0
            for question in scienceqa_history:
                if question in ['explanatory', 'general_causal', 'specific_causal']:
                    qualified_question_num += 1
            
            if qualified_question_num > 2:
                current_state = 'reflection'
                state_prompt = state_prompt_classification(current_state)
                child_question_level = None
            else:   
                # Classify the child's question level
                child_question_level = state_classification(state, messages, phenomenon)
                scienceqa_history.append(child_question_level)
                print(f"child_question_level: {child_question_level}")
                print(f"scienceqa_history: {scienceqa_history}")
                current_state = 'scienceqa'  # Stay in scienceqa state
                state_prompt = state_prompt_classification(current_state, child_question_level)

        if current_state in ['scienceqa', 'reflection']:
            if current_state == 'scienceqa' and child_question_level in ['factual', 'explanatory', 'general_causal', 'specific_causal']:
                kg = knowledge_retrieval(messages, phenomenon)
                print(f"kg: {kg}")
                if kg != '':
                    if child_question_level in ['explanatory', 'general_causal', 'specific_causal']:
                        state_prompt = state_prompt + '\n\n<Relevant Knowledge Components>\n' + format_kg('definition_and_explanation', kg, phenomenon) + '\n</Relevant Knowledge Components>'
                    elif child_question_level == 'factual':
                        state_prompt = state_prompt + '\n\n<Relevant Knowledge Components>\n' + format_kg('definition', kg, phenomenon) + '\n</Relevant Knowledge Components>'
            elif current_state == 'reflection':
                kg = knowledge_retrieval(messages, phenomenon)
                print(f"kg: {kg}")
                if kg != '':
                    state_prompt = state_prompt + '\n\n<Relevant Knowledge Components>\n' + format_kg('definition_and_explanation', kg, phenomenon) + '\n</Relevant Knowledge Components>'

        
        if current_state == 'scienceqa' and child_question_level is not None:
            state_prompt = format_prompt(state_prompt, phenomenon, messages, child_question_level)
            # print(f"state_prompt: {state_prompt}")
        else:
            state_prompt = format_prompt(state_prompt, phenomenon, messages)

        # print(f"state_prompt: {state_prompt}")

        system_message = {"role": "system", "content": CURIO_SYSTEM_PROMPT}
        # all_messages = [system_message] + messages + [
        #     {
        #         "role": "user", 
        #         "content": [
        #             {"type": "input_text", "text": state_prompt},
        #             {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encode_image(image_path[1:])}"}
        #         ]
        #     }
        # ]

        all_messages = [system_message] + messages + [{"role": "user", "content": state_prompt}]

        response = client.chat.completions.create(
            model="gpt-4",
            messages=all_messages,
            max_tokens=500
        )

        # response = client.responses.create(
        #     model="gpt-5",
        #     input = all_messages,
        #     reasoning={ "effort": "low" },
        # )

        # content = response.output_text or ""
        content = response.choices[0].message.content or ""
        # content = response.choices[0].message.content or ""

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
    app.run(debug=True, host='0.0.0.0', port=5001)