"""
Database Viewer API endpoints for viewing and downloading conversation data
"""

import io
import json
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy.orm import Session

# Import will be done after app initialization to avoid circular import

db_viewer = Blueprint("db_viewer", __name__)

# These will be set when the blueprint is registered
SessionLocal = None
Conversation = None
Message = None


def init_db_viewer(session_local, conversation_model, message_model):
    """Initialize the database viewer with database models"""
    global SessionLocal, Conversation, Message
    SessionLocal = session_local
    Conversation = conversation_model
    Message = message_model


@db_viewer.route("/api/conversations", methods=["GET"])
def list_conversations():
    """List all conversations with summary information"""
    if SessionLocal is None:
        return jsonify({"error": "Database viewer not initialized"}), 500
    db = SessionLocal()
    try:
        # Get query parameters
        limit = request.args.get("limit", type=int, default=50)
        offset = request.args.get("offset", type=int, default=0)
        session_id = request.args.get("session_id")
        phenomenon = request.args.get("phenomenon")

        query = db.query(Conversation)

        # Apply filters
        if session_id:
            query = query.filter(Conversation.session_id == session_id)
        if phenomenon:
            query = query.filter(Conversation.phenomenon == phenomenon)

        # Order by most recent first
        conversations = (
            query.order_by(Conversation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        result = []
        for conv in conversations:
            # Count messages
            message_count = (
                db.query(Message).filter(Message.conversation_id == conv.id).count()
            )

            result.append(
                {
                    "id": conv.id,
                    "session_id": conv.session_id,
                    "image_path": conv.image_path,
                    "phenomenon": conv.phenomenon,
                    "started_at": conv.started_at.isoformat()
                    if conv.started_at
                    else None,
                    "finished_at": conv.finished_at.isoformat()
                    if conv.finished_at
                    else None,
                    "evaluation_result": conv.evaluation_result,
                    "message_count": message_count,
                    "created_at": conv.created_at.isoformat()
                    if conv.created_at
                    else None,
                }
            )

        return jsonify(
            {
                "conversations": result,
                "total": len(result),
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@db_viewer.route("/api/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get detailed information about a specific conversation including all messages"""
    if SessionLocal is None:
        return jsonify({"error": "Database viewer not initialized"}), 500
    db = SessionLocal()
    try:
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )

        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        # Get all messages for this conversation
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        message_list = []
        for msg in messages:
            message_data = {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "state": msg.state,
                "evaluation_result": msg.evaluation_result,
                "has_audio": msg.audio_data is not None,
                "audio_mime_type": msg.audio_mime_type,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            message_list.append(message_data)

        return jsonify(
            {
                "conversation": {
                    "id": conversation.id,
                    "session_id": conversation.session_id,
                    "image_path": conversation.image_path,
                    "phenomenon": conversation.phenomenon,
                    "started_at": conversation.started_at.isoformat()
                    if conversation.started_at
                    else None,
                    "finished_at": conversation.finished_at.isoformat()
                    if conversation.finished_at
                    else None,
                    "evaluation_result": conversation.evaluation_result,
                    "created_at": conversation.created_at.isoformat()
                    if conversation.created_at
                    else None,
                },
                "messages": message_list,
                "message_count": len(message_list),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@db_viewer.route(
    "/api/conversations/<conversation_id>/messages/<message_id>/audio", methods=["GET"]
)
def download_audio(conversation_id, message_id):
    """Download audio file for a specific message"""
    if SessionLocal is None:
        return jsonify({"error": "Database viewer not initialized"}), 500
    db = SessionLocal()
    try:
        message = (
            db.query(Message)
            .filter(
                Message.id == message_id, Message.conversation_id == conversation_id
            )
            .first()
        )

        if not message:
            return jsonify({"error": "Message not found"}), 404

        if not message.audio_data:
            return jsonify({"error": "No audio data available for this message"}), 404

        # Determine file extension from mime type
        mime_type = message.audio_mime_type or "audio/webm"
        extension_map = {
            "audio/webm": "webm",
            "audio/ogg": "ogg",
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
        }
        extension = extension_map.get(mime_type, "webm")

        # Create a file-like object from the binary data
        audio_file = io.BytesIO(message.audio_data)

        filename = f"audio_{message_id}.{extension}"

        return send_file(
            audio_file, mimetype=mime_type, as_attachment=True, download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@db_viewer.route("/api/export", methods=["GET"])
def export_all_data():
    """Export all conversation data as JSON"""
    if SessionLocal is None:
        return jsonify({"error": "Database viewer not initialized"}), 500
    db = SessionLocal()
    try:
        format_type = request.args.get("format", "json")  # json or csv

        conversations = (
            db.query(Conversation).order_by(Conversation.created_at.desc()).all()
        )

        export_data = {
            "export_date": datetime.utcnow().isoformat(),
            "total_conversations": len(conversations),
            "conversations": [],
        }

        for conv in conversations:
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.asc())
                .all()
            )

            message_list = []
            for msg in messages:
                message_data = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "state": msg.state,
                    "evaluation_result": msg.evaluation_result,
                    "has_audio": msg.audio_data is not None,
                    "audio_mime_type": msg.audio_mime_type,
                    "audio_size_bytes": len(msg.audio_data) if msg.audio_data else 0,
                    "created_at": msg.created_at.isoformat()
                    if msg.created_at
                    else None,
                }
                message_list.append(message_data)

            conv_data = {
                "id": conv.id,
                "session_id": conv.session_id,
                "image_path": conv.image_path,
                "phenomenon": conv.phenomenon,
                "started_at": conv.started_at.isoformat() if conv.started_at else None,
                "finished_at": conv.finished_at.isoformat()
                if conv.finished_at
                else None,
                "evaluation_result": conv.evaluation_result,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "messages": message_list,
                "message_count": len(message_list),
            }
            export_data["conversations"].append(conv_data)

        if format_type == "json":
            return jsonify(export_data)
        else:
            # CSV format (simplified - just conversation summary)
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(
                [
                    "Conversation ID",
                    "Session ID",
                    "Phenomenon",
                    "Started At",
                    "Finished At",
                    "Message Count",
                    "Evaluation Result",
                ]
            )

            # Data rows
            for conv in export_data["conversations"]:
                writer.writerow(
                    [
                        conv["id"],
                        conv["session_id"],
                        conv["phenomenon"],
                        conv["started_at"],
                        conv["finished_at"],
                        conv["message_count"],
                        conv["evaluation_result"],
                    ]
                )

            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode("utf-8")),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"conversations_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@db_viewer.route("/api/stats", methods=["GET"])
def get_statistics():
    """Get statistics about the database"""
    if SessionLocal is None:
        return jsonify({"error": "Database viewer not initialized"}), 500
    db = SessionLocal()
    try:
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        # Count distinct conversations that have at least one message with audio
        conversations_with_audio = (
            db.query(Message.conversation_id)
            .filter(Message.audio_data.isnot(None))
            .distinct()
            .count()
        )
        total_audio_messages = (
            db.query(Message).filter(Message.audio_data.isnot(None)).count()
        )

        # Group by phenomenon
        phenomenon_stats = {}
        conversations = db.query(Conversation).all()
        for conv in conversations:
            phenomenon = conv.phenomenon or "unknown"
            if phenomenon not in phenomenon_stats:
                phenomenon_stats[phenomenon] = 0
            phenomenon_stats[phenomenon] += 1

        # Average messages per conversation
        avg_messages = (
            total_messages / total_conversations if total_conversations > 0 else 0
        )

        return jsonify(
            {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "conversations_with_audio": conversations_with_audio,
                "total_audio_messages": total_audio_messages,
                "average_messages_per_conversation": round(avg_messages, 2),
                "phenomenon_distribution": phenomenon_stats,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
