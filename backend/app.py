import base64
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote_plus

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from models import Conversation, Message
from prompts.eval import reflection, scaffolding, scienceqa
from prompts.scienceqa import level_0, level_1, level_2, level_3, level_4, no_question

load_dotenv()
app = Flask(__name__)

# CORS configuration - allow both dev server and Docker frontend
allowed_origins = [
    "http://localhost",  # Docker frontend (localhost without port)
    "http://localhost:80",  # Docker frontend (default nginx port)
    "http://localhost:5173",  # Development frontend
    "http://localhost:8080",  # Common Docker mapped port
]
if os.getenv("VUE_APP_URL"):
    allowed_origins.append(os.getenv("VUE_APP_URL"))
CORS(app, resources={r"/*": {"origins": allowed_origins}})

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
client = OpenAI(api_key=openai_api_key)

# OpenAI Model Configuration
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4")
OPENAI_WHISPER_MODEL = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "500"))

# Database setup
# Prioritize POSTGRES_* environment variables (set by docker-compose) over DATABASE_URL
# This ensures we use the correct values even if DATABASE_URL is set incorrectly in .env
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_host = os.getenv("POSTGRES_HOST")
postgres_port = os.getenv("POSTGRES_PORT")
postgres_db = os.getenv("POSTGRES_DB")

# If POSTGRES_* variables are set (e.g., in Docker), construct URL from them
# Otherwise, try to use DATABASE_URL from environment
if postgres_user and postgres_password and postgres_host and postgres_db:
    # Construct DATABASE_URL from individual components
    if not postgres_port:
        postgres_port = "5432"
    # URL encode password in case it contains special characters
    encoded_password = quote_plus(postgres_password)
    database_url = f"postgresql://{postgres_user}:{encoded_password}@{postgres_host}:{postgres_port}/{postgres_db}"
    # Debug: print connection info (mask password)
    print("Constructed DATABASE_URL from POSTGRES_* environment variables")
    print(
        f"  User: {postgres_user}, Host: {postgres_host}, Port: {postgres_port}, Database: {postgres_db}"
    )
else:
    # Fall back to DATABASE_URL if POSTGRES_* variables are not set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Last resort: use defaults
        postgres_user = postgres_user or "curio"
        postgres_password = postgres_password or "curio_password"
        postgres_host = postgres_host or "postgres"
        postgres_port = postgres_port or "5432"
        postgres_db = postgres_db or "curio_db"
        encoded_password = quote_plus(postgres_password)
        database_url = f"postgresql://{postgres_user}:{encoded_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        print("Constructed DATABASE_URL from defaults")
    else:
        print("Using DATABASE_URL from environment")

engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False)
)

# Global variable to track conversation start times
conversation_start_times = {}

# System prompt for Curio
CURIO_SYSTEM_PROMPT = """
<System Introduction>
You are Curio, a friendly and encouraging science chatbot for children aged 8-10. The system shows an image, and your task is to prompt the child to discover the scientific phenomenon behind the image. Once the child has discovered the scientific phenomenon, you will prompt the child to ask questions to discover the science knowledge behind the phenomenon.
</System Introduction>
"""

state_history = defaultdict(list)
scienceqa_history = defaultdict(list)


def state_classification(state, messages, phenomenon):
    # Load prompt from the txt file
    if state in ["greet", "scaffolding"]:
        eval_prompt = format_prompt(scaffolding, phenomenon, messages)
    elif state in ["discover", "scienceqa"]:
        eval_prompt = format_prompt(scienceqa, phenomenon, messages)
    elif state in ["reflection"]:
        eval_prompt = format_prompt(reflection, phenomenon, messages)

    messages = [{"role": "system", "content": eval_prompt}]
    # print(f"messages: {messages}")

    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL, messages=messages, max_tokens=OPENAI_MAX_TOKENS
    )

    # response = client.responses.create(
    #         model="gpt-5",
    #         input = messages,
    #         reasoning={ "effort": "low" },
    #     )

    # content = response.output_text or ""
    content = response.choices[0].message.content or ""
    eval_state = content.strip().lower().replace("<", "").replace(">", "")
    return eval_state


def state_update(current_state, eval_state, state_history_list):
    next_state = eval_state
    if eval_state == "discover":
        next_state = "discover"
    elif eval_state == "scienceqa":
        if len(state_history_list) > 0 and state_history_list[-1] == "scaffolding":
            next_state = "discover"
        elif "reflection" not in state_history_list:
            total_sci = state_history_list.count("scienceqa")
            if total_sci >= 2:
                next_state = "reflection"
            else:
                next_state = "scienceqa"
        else:
            reflection_index = state_history_list.index("reflection")
            post_ref_sci = state_history_list[reflection_index:].count("scienceqa")
            num_of_reflection = state_history_list.count("reflection")
            if num_of_reflection >= 2:
                next_state = "close"
            else:
                next_state = "reflection" if post_ref_sci >= 2 else "scienceqa"
    elif eval_state == "reflection":
        next_state = "reflection"
    elif eval_state == "scaffolding":
        num_of_scaffolding = state_history_list.count("scaffolding")
        if num_of_scaffolding >= 1:
            next_state = "discover"
        else:
            next_state = "scaffolding"
    elif eval_state == "close":
        next_state = "close"
    else:
        next_state = "scienceqa"

    state_history_list.append(next_state)
    return next_state


def state_prompt_classification(state, child_question_level=None):
    if state == "greet":
        return open("prompts/greet.txt", "r").read()
    elif state == "scaffolding":
        return open("prompts/scaffolding.txt", "r").read()
    elif state == "discover":
        return open("prompts/discover.txt", "r").read()
    elif state == "scienceqa":
        if child_question_level == "no_question":
            return no_question
        elif child_question_level == "irrelevant":
            return level_0
        elif child_question_level == "factual":
            return level_1
        elif child_question_level == "explanatory":
            return level_2
        elif child_question_level == "general_causal":
            return level_3
        elif child_question_level == "specific_causal":
            return level_4
    elif state == "reflection":
        return open("prompts/reflection.txt", "r").read()
    elif state == "close":
        return open("prompts/close.txt", "r").read()
    else:
        return open("prompts/scienceqa.txt", "r").read()


def format_prompt(
    state_prompt, phenomenon="balloon", messages=None, child_question_level=None
):
    if messages is None:
        messages = []

    phenomenon_json = json.load(open("prompts/phenomenon.json", "r"))
    phenomenon_data = phenomenon_json.get(phenomenon, {})

    if "<Image Content>" in state_prompt:
        state_prompt = state_prompt.replace(
            "<Image Content>",
            "<Image Content>\n" + phenomenon_data.get("image_content", ""),
        )
    if "<Scientific Phenomenon>" in state_prompt:
        state_prompt = state_prompt.replace(
            "<Scientific Phenomenon>",
            "<Scientific Phenomenon>\n" + phenomenon_data.get("phenomenon", ""),
        )
    if "<Scientific Knowledge>" in state_prompt:
        state_prompt = state_prompt.replace(
            "<Scientific Knowledge>",
            "<Scientific Knowledge>\n" + phenomenon_data.get("knowledge", ""),
        )

    if "<Child's Question>" in state_prompt:
        state_prompt = state_prompt.replace(
            "<Child's Question>",
            "<Child's Question>\n" + messages[-1]["content"].strip(),
        )
    if "<Conversation History>" in state_prompt:
        state_prompt = state_prompt.replace(
            "<Conversation History>", "<Conversation History>\n" + json.dumps(messages)
        )
    return state_prompt


def knowledge_retrieval(messages, phenomenon="balloon"):
    # Load prompt from the txt file
    retrieval_prompt = open("prompts/knowledge_matching.txt", "r").read()
    retrieval_prompt = format_prompt(retrieval_prompt, phenomenon, messages)
    knowledge_base = open("knowledge/kg.json", "r").read()
    knowledge_base = json.loads(knowledge_base)

    # Map phenomenon to knowledge base key
    phenomenon_map = {
        "balloon": "Hair stands up near a balloon",
        "bend": "Bending Water Stream with a Comb",
        "pepper": "Pepper Leaping up to Spoon",
    }
    phenomenon_key = phenomenon_map.get(phenomenon, "Hair stands up near a balloon")

    knowledge_concepts = list(knowledge_base[phenomenon_key]["concepts"].keys())

    retrieval_prompt = (
        retrieval_prompt
        + "\n\n<Knowledge Components>\n"
        + json.dumps(knowledge_concepts)
        + "\n</Knowledge Components>"
    )

    print(f"retrieval_prompt: {retrieval_prompt}")
    messages = [{"role": "system", "content": retrieval_prompt}]
    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL, messages=messages, max_tokens=OPENAI_MAX_TOKENS
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


def format_kg(mode="definition", kg_raw="", phenomenon="balloon"):
    knowledge_base = open("knowledge/kg.json", "r").read()
    knowledge_base = json.loads(knowledge_base)

    # Map phenomenon to knowledge base key
    phenomenon_map = {
        "balloon": "Hair stands up near a balloon",
        "bend": "Bending Water Stream with a Comb",
        "pepper": "Pepper Leaping up to Spoon",
    }
    phenomenon_key = phenomenon_map.get(phenomenon, "Hair stands up near a balloon")

    try:
        kg_list = json.loads(kg_raw)
        kg_content = ""
        for component in kg_list:
            definition = knowledge_base[phenomenon_key]["concepts"][component][
                "definition"
            ]
            explanation = knowledge_base[phenomenon_key]["concepts"][component][
                "explanation"
            ]
            if mode == "definition":
                kg_content += (
                    "'" + component + "':\n\nDefinition: " + definition + "\n\n"
                )
            elif mode == "explanation":
                kg_content += (
                    "'" + component + "':\n\nExplanation: " + explanation + "\n\n"
                )
            elif mode == "definition_and_explanation":
                kg_content += (
                    "'"
                    + component
                    + "':\n\nDefinition: "
                    + definition
                    + "\n\nExplanation: "
                    + explanation
                    + "\n\n"
                )
        kg_content = kg_content.strip()
        print(f"kg_content: {kg_content}")
        return kg_content
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing knowledge graph: {e}")
        return ""


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "service": "curio2-backend",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        200,
    )


@app.route("/api/transcribe", methods=["POST"])
def transcribe_audio():
    """Transcribe audio using OpenAI Whisper API"""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]

    try:
        # Call OpenAI Whisper API from backend
        transcript = client.audio.transcriptions.create(
            model=OPENAI_WHISPER_MODEL, file=audio_file, response_format="json"
        )

        return jsonify({"text": transcript.text}), 200

    except Exception as e:
        app.logger.error(f"Transcription error: {str(e)}")
        return jsonify({"error": "Transcription failed"}), 500


@app.route("/api/chat", methods=["POST"])
def chat_completion():
    """Generate chat response and a next_state using OpenAI"""
    db = SessionLocal()
    try:
        # Record start time for latency tracking
        start_time = time.time()
        request_session_id = request.remote_addr  # Fallback session identifier
        conversation_start_times[request_session_id] = start_time

        data = request.get_json()
        messages = data.get("messages", [])
        state = (data.get("state") or "greet").strip()
        image_path = data.get("image_path", "")  # Get the selected image path
        session_identifier = (
            data.get("session_id") or request_session_id or ""
        ).strip()
        conversation_id = (data.get("conversation_id") or str(uuid.uuid4())).strip()
        user_audio_b64 = data.get("user_audio")
        user_audio_mime_type = data.get("user_audio_mime_type")

        user_audio_bytes = None
        if user_audio_b64:
            try:
                user_audio_bytes = base64.b64decode(user_audio_b64)
            except (ValueError, TypeError) as audio_error:
                print(
                    f"Failed to decode user audio for conversation {conversation_id}: {audio_error}"
                )

        latest_user_message = ""
        if messages:
            last_message = messages[-1]
            if last_message.get("role") == "user":
                latest_user_message = last_message.get("content", "")

        # Determine the phenomenon based on image path
        if "balloon.jpg" in image_path:
            phenomenon = "balloon"
        elif "bend.jpg" in image_path:
            phenomenon = "bend"
        elif "pepper.jpg" in image_path:
            phenomenon = "pepper"
        else:
            phenomenon = "balloon"  # default fallback

        conversation = db.get(Conversation, conversation_id)
        if not conversation:
            conversation = Conversation(
                id=conversation_id,
                session_id=session_identifier or str(uuid.uuid4()),
                image_path=image_path,
                phenomenon=phenomenon,
                started_at=datetime.utcnow(),
            )
            db.add(conversation)

        conv_state_history = state_history[conversation_id]
        conv_scienceqa_history = scienceqa_history[conversation_id]

        eval_state = None
        if state != "scienceqa":
            print(f"state: {state}")
            eval_state = state_classification(state, messages, phenomenon)
            print(f"eval_state: {eval_state}")
            current_state = state_update(state, eval_state, conv_state_history)
            print(f"current_state: {current_state}")

            # If transitioning to scienceqa, classify the question level immediately
            if current_state == "scienceqa":
                child_question_level = state_classification(state, messages, phenomenon)
                conv_scienceqa_history.append(child_question_level)
                print(f"child_question_level: {child_question_level}")
                print(f"scienceqa_history: {conv_scienceqa_history}")
                state_prompt = state_prompt_classification(
                    current_state, child_question_level
                )
            else:
                child_question_level = None
                state_prompt = state_prompt_classification(current_state)
        else:
            # Check if we should move to reflection based on qualified questions
            qualified_question_num = sum(
                1
                for question in conv_scienceqa_history
                if question in ["explanatory", "general_causal", "specific_causal"]
            )

            if qualified_question_num > 2:
                current_state = "reflection"
                state_prompt = state_prompt_classification(current_state)
                child_question_level = None
            else:
                # Classify the child's question level
                child_question_level = state_classification(state, messages, phenomenon)
                conv_scienceqa_history.append(child_question_level)
                print(f"child_question_level: {child_question_level}")
                print(f"scienceqa_history: {conv_scienceqa_history}")
                current_state = "scienceqa"  # Stay in scienceqa state
                state_prompt = state_prompt_classification(
                    current_state, child_question_level
                )
            if not conv_state_history or conv_state_history[-1] != current_state:
                conv_state_history.append(current_state)
            eval_state = current_state

        if current_state in ["scienceqa", "reflection"]:
            if current_state == "scienceqa" and child_question_level in [
                "factual",
                "explanatory",
                "general_causal",
                "specific_causal",
            ]:
                kg = knowledge_retrieval(messages, phenomenon)
                print(f"kg: {kg}")
                if kg != "":
                    if child_question_level in [
                        "explanatory",
                        "general_causal",
                        "specific_causal",
                    ]:
                        state_prompt = (
                            state_prompt
                            + "\n\n<Relevant Knowledge Components>\n"
                            + format_kg("definition_and_explanation", kg, phenomenon)
                            + "\n</Relevant Knowledge Components>"
                        )
                    elif child_question_level == "factual":
                        state_prompt = (
                            state_prompt
                            + "\n\n<Relevant Knowledge Components>\n"
                            + format_kg("definition", kg, phenomenon)
                            + "\n</Relevant Knowledge Components>"
                        )
            elif current_state == "reflection":
                kg = knowledge_retrieval(messages, phenomenon)
                print(f"kg: {kg}")
                if kg != "":
                    state_prompt = (
                        state_prompt
                        + "\n\n<Relevant Knowledge Components>\n"
                        + format_kg("definition_and_explanation", kg, phenomenon)
                        + "\n</Relevant Knowledge Components>"
                    )

        if current_state == "scienceqa" and child_question_level is not None:
            state_prompt = format_prompt(
                state_prompt, phenomenon, messages, child_question_level
            )
        else:
            state_prompt = format_prompt(state_prompt, phenomenon, messages)

        user_evaluation_result = child_question_level or eval_state or current_state

        if latest_user_message:
            user_message_record = Message(
                conversation_id=conversation.id,
                role="user",
                content=latest_user_message,
                state=state,
                evaluation_result=user_evaluation_result,
                audio_data=user_audio_bytes,
                audio_mime_type=user_audio_mime_type,
            )
            db.add(user_message_record)

        conversation.image_path = image_path
        conversation.phenomenon = phenomenon
        conversation.updated_at = datetime.utcnow()
        if user_evaluation_result:
            conversation.evaluation_result = user_evaluation_result
        if current_state == "close" and not conversation.finished_at:
            conversation.finished_at = datetime.utcnow()
        if current_state == "close":
            state_history.pop(conversation_id, None)
            scienceqa_history.pop(conversation_id, None)

        system_message = {"role": "system", "content": CURIO_SYSTEM_PROMPT}

        all_messages = (
            [system_message] + messages + [{"role": "user", "content": state_prompt}]
        )

        response = client.chat.completions.create(
            model=OPENAI_CHAT_MODEL, messages=all_messages, max_tokens=OPENAI_MAX_TOKENS
        )

        content = response.choices[0].message.content or ""

        assistant_message_record = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=content,
            state=current_state,
        )
        db.add(assistant_message_record)

        db.commit()

        return jsonify({"response": content, "next_state": current_state})

    except SQLAlchemyError as db_error:
        db.rollback()
        print(f"Database error during chat completion: {db_error}")
        return jsonify({"error": "Chat completion failed"}), 500
    except Exception as e:
        db.rollback()
        print(f"Chat completion error: {e}")
        return jsonify({"error": "Chat completion failed"}), 500
    finally:
        db.close()


@app.route("/api/speech", methods=["POST"])
def generate_speech():
    """Generate speech audio using OpenAI TTS"""
    try:
        # Calculate latency from conversation start to audio generation
        session_id = request.remote_addr
        end_time = time.time()

        if session_id in conversation_start_times:
            total_latency = end_time - conversation_start_times[session_id]
            print(
                f"🎯 Total latency (user message → audio response): {total_latency:.2f} seconds"
            )
            # Clean up the stored start time
            del conversation_start_times[session_id]
        else:
            print("⚠️  No start time found for session, cannot calculate latency")

        data = request.get_json()
        text = data.get("text", "")

        if not text:
            return jsonify({"error": "No text provided"}), 400

        # Generate speech using OpenAI TTS
        response = client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=text,
            response_format="mp3",
        )

        # Return the audio data
        return (
            response.content,
            200,
            {
                "Content-Type": "audio/mpeg",
                "Content-Disposition": "attachment; filename=speech.mp3",
            },
        )

    except Exception as e:
        print(f"Speech generation error: {e}")
        return jsonify({"error": "Speech generation failed"}), 500


# Register database viewer blueprint
from database_viewer import db_viewer, init_db_viewer  # noqa: E402

init_db_viewer(SessionLocal, Conversation, Message)
app.register_blueprint(db_viewer)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))  # Default 5001 for local dev
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=debug, host="0.0.0.0", port=port)
