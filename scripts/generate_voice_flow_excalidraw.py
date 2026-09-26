#!/usr/bin/env python3
# ruff: noqa: E501
"""Generates docs/coligo_voice_processing_flow.excalidraw detailing the complete
inbound voice note transcription (STT) and outbound neural audio response (TTS) flow.
"""

import json
import uuid
from pathlib import Path


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def rect(
    x: float,
    y: float,
    w: float,
    h: float,
    stroke: str = "#1e1e2e",
    bg: str = "transparent",
    stroke_w: int = 2,
    round_type: int = 3,
) -> dict:
    return {
        "id": new_id(),
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": stroke_w,
        "roughness": 0,
        "opacity": 100,
        "roundness": {"type": round_type},
    }


def text(
    content: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size: int = 16,
    align: str = "center",
    valign: str = "middle",
    color: str = "#1e1e2e",
) -> dict:
    return {
        "id": new_id(),
        "type": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": content,
        "fontSize": size,
        "fontFamily": 1,
        "textAlign": align,
        "verticalAlign": valign,
        "strokeColor": color,
        "fillStyle": "solid",
        "backgroundColor": "transparent",
        "roughness": 0,
        "opacity": 100,
    }


def arrow(
    points: list[list[float]],
    start_x: float,
    start_y: float,
    color: str = "#1e1e2e",
    stroke_w: int = 2,
    end_arrow: str = "arrow",
) -> dict:
    pts = [[p[0], p[1]] for p in points]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    return {
        "id": new_id(),
        "type": "arrow",
        "x": start_x,
        "y": start_y,
        "width": max(w, 1),
        "height": max(h, 1),
        "strokeColor": color,
        "strokeWidth": stroke_w,
        "roughness": 0,
        "opacity": 100,
        "points": pts,
        "endArrowhead": end_arrow,
    }


def build_voice_flow_excalidraw():
    elements = []

    # Title & Subtitle
    elements.append(
        text(
            "Coligo — WhatsApp Voice Note (STT & TTS) End-to-End Processing Architecture",
            40,
            20,
            1560,
            45,
            size=28,
            color="#0f172a",
        )
    )
    elements.append(
        text(
            "Live Trace Simulation: Inbound Voice Note (0:05) -> Whisper STT -> LangGraph RAG Agent -> Dual Text & Neural Voice Note Dispatch",
            40,
            65,
            1560,
            30,
            size=16,
            color="#475569",
        )
    )

    # 4 Main Columns / Stages
    cols = [
        (
            60,
            120,
            340,
            "1. INBOUND VOICE MESSAGE",
            "#10b981",
            "#ecfdf5",
            "#047857",
        ),
        (
            440,
            120,
            350,
            "2. TRANSCRIPTION & ECHO (STT)",
            "#0284c7",
            "#f0f9ff",
            "#0369a1",
        ),
        (
            830,
            120,
            370,
            "3. LANGGRAPH RAG REASONING",
            "#7c3aed",
            "#f5f3ff",
            "#6d28d9",
        ),
        (
            1240,
            120,
            360,
            "4. DUAL TEXT & VOICE DISPATCH (TTS)",
            "#ea580c",
            "#fff7ed",
            "#c2410c",
        ),
    ]

    for cx, cy, cw, title, stroke_c, bg_c, text_c in cols:
        elements.append(rect(cx, cy, cw, 680, stroke=stroke_c, bg=bg_c, stroke_w=2))
        elements.append(
            text(title, cx + 10, cy + 15, cw - 20, 30, size=18, color=text_c)
        )

    # Column 1 Cards (Student WhatsApp & Meta Webhook)
    elements.append(rect(80, 180, 300, 140, stroke="#10b981", bg="#ffffff", stroke_w=2))
    elements.append(
        text(
            "Student WhatsApp Client\n\n• Records 5-second voice note:\n  'I want the SKCET CSE cutoff for every community.'\n• Audio format: OGG OPUS\n• Sent to Coligo WhatsApp Bot",
            90,
            190,
            280,
            120,
            size=14,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(rect(80, 360, 300, 160, stroke="#10b981", bg="#ffffff", stroke_w=2))
    elements.append(
        text(
            "Meta Cloud API (Graph v21.0)\n\n• Receives audio from user\n• Stores media temporarily on CDN\n• Fires Webhook POST to:\n  https://coligo...render.com/webhook\n• Payload: {\n    'type': 'audio',\n    'audio': {'id': 'media_12345'}\n  }",
            90,
            370,
            280,
            140,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(rect(80, 560, 300, 110, stroke="#10b981", bg="#ffffff", stroke_w=2))
    elements.append(
        text(
            "Security & Routing Filter\n\n• api/routers/whatsapp.py\n• Validates X-Hub-Signature-256\n• Resolves session: whatsapp:919876543210\n• Enqueues async background task",
            90,
            570,
            280,
            90,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    # Arrows Col 1
    elements.append(arrow([[0, 0], [0, 40]], 230, 320, color="#10b981"))
    elements.append(arrow([[0, 0], [0, 40]], 230, 520, color="#10b981"))
    elements.append(arrow([[0, 0], [60, 0]], 380, 440, color="#0284c7"))

    # Column 2 Cards (Audio Service & Groq Whisper STT)
    elements.append(
        rect(460, 180, 310, 140, stroke="#0284c7", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Media Ingestion & Download\n\n• api/services/audio_service.py\n• Queries Meta Graph API for media URL\n• Downloads binary audio payload\n• Validates size (< 16 MB)\n• Retains OGG bytes in memory buffer",
            470,
            190,
            290,
            120,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(
        rect(460, 360, 310, 150, stroke="#0284c7", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Speech-to-Text (STT) Engine\n\n• Groq Whisper (whisper-large-v3-turbo)\n• Fallback: Gemini 1.5 Flash Audio\n• Transcribes English, Tamil & Tanglish\n• Output Text:\n  'I want the SKCET CSE cutoff for every community.'",
            470,
            370,
            290,
            130,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(
        rect(460, 550, 310, 130, stroke="#0284c7", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Instant WhatsApp Transcript Echo\n\n• Immediate reassuring feedback to student\n• Outbound text dispatch:\n  Voice note transcript:\n  'I want the SKCET CSE cutoff for every community.'\n• Sent via api/services/whatsapp_service.py",
            470,
            560,
            290,
            110,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    # Arrows Col 2
    elements.append(arrow([[0, 0], [0, 40]], 615, 320, color="#0284c7"))
    elements.append(arrow([[0, 0], [0, 40]], 615, 510, color="#0284c7"))
    elements.append(arrow([[0, 0], [60, 0]], 770, 435, color="#7c3aed"))

    # Column 3 Cards (LangGraph RAG Reasoning)
    elements.append(
        rect(850, 180, 330, 130, stroke="#7c3aed", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Router Node (api/services/agent/nodes/router.py)\n\n• Intent: cutoff_query\n• College: Sri Krishna College of Engg (SKCET)\n• Branch: CSE\n• Community: All Categories (OC, BC, BCM, MBC, SC, ST)\n• Language: English detected",
            860,
            190,
            310,
            110,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(
        rect(850, 350, 330, 140, stroke="#7c3aed", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Tool Agent & Database Retrieval\n\n• Tool: query_college_cutoffs(college='SKCET', branch='CSE')\n• PostgreSQL + pgvector query:\n  - OC: 192\n  - BC: 189.5\n  - BCM: 189\n  - MBC: 186.5\n• Fetches verified TNEA counselling closing marks",
            860,
            360,
            310,
            120,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(
        rect(850, 530, 330, 150, stroke="#7c3aed", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Synthesizer Node\n\n• Synthesizes professional response:\n  'SKCET – Computer Science & Engineering Cutoffs:\n   • OC – 192\n   • BC – 189.5\n   • BCM – 189\n   • MBC – 186.5'\n• Strict Plain Text (Zero Emojis Enforced)",
            860,
            540,
            310,
            130,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    # Arrows Col 3
    elements.append(arrow([[0, 0], [0, 40]], 1015, 310, color="#7c3aed"))
    elements.append(arrow([[0, 0], [0, 40]], 1015, 490, color="#7c3aed"))
    elements.append(arrow([[0, 0], [60, 0]], 1180, 605, color="#ea580c"))

    # Column 4 Cards (Dual Dispatch: Written Text + Neural Audio Note)
    elements.append(
        rect(1260, 180, 320, 150, stroke="#ea580c", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Branch A: Written Text & Quick Actions\n\n• Formats full detailed markdown response\n• send_text(sender, formatted_answer)\n• Appends interactive Quick Action buttons:\n  [ 3-Tier Choice List ]\n  [ Fee Details ]\n  [ Compare College ]\n• Delivered instantly to WhatsApp chat",
            1270,
            190,
            300,
            130,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(
        rect(1260, 360, 320, 160, stroke="#ea580c", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Branch B: Neural Speech Synthesis (TTS)\n\n• api/services/tts_service.py\n• ENABLE_VOICE_RESPONSES = True\n• prepare_spoken_summary() extracts spoken text\n• Voice selection: en-IN-NeerjaNeural (or ta-IN-PallaviNeural)\n• Edge-TTS streams high-fidelity neural audio\n• Byte length: ~70-130 KB",
            1270,
            370,
            300,
            140,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    elements.append(
        rect(1260, 550, 320, 140, stroke="#ea580c", bg="#ffffff", stroke_w=2)
    )
    elements.append(
        text(
            "Outbound WhatsApp Voice Note Delivery\n\n• upload_media(audio_bytes, mime_type='audio/mpeg')\n• Meta returns media_id: 1644575737297388\n• send_audio(to='919876543210', media_id)\n• Student receives real voice note playback in WhatsApp chat!",
            1270,
            560,
            300,
            120,
            size=13,
            align="left",
            color="#0f172a",
        )
    )

    # Arrows Col 4
    elements.append(arrow([[0, 0], [0, 30]], 1420, 330, color="#ea580c"))
    elements.append(arrow([[0, 0], [0, 30]], 1420, 520, color="#ea580c"))

    # Bottom Summary Banner
    elements.append(rect(60, 830, 1540, 90, stroke="#0f172a", bg="#f8fafc", stroke_w=2))
    elements.append(
        text(
            "SIMULATION VERIFICATION & KEY TAKEAWAYS:\n"
            "1. When student speaks English or Tamil, Groq Whisper transcribes it and sends an immediate transcript echo.\n"
            "2. LangGraph RAG Agent retrieves official TNEA cutoffs and formats the exact text answer without emojis.\n"
            "3. Outbound dispatch sends BOTH the structured written text table AND the synthesized neural voice note (MP3/OGG) to WhatsApp.",
            80,
            840,
            1500,
            70,
            size=14,
            align="left",
            color="#0f172a",
        )
    )

    data = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": 20,
            "gridStep": 5,
            "zoom": {"value": 1},
            "scrollX": 0,
            "scrollY": 0,
        },
        "files": {},
    }

    target = Path("docs/coligo_voice_processing_flow.excalidraw")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated {target} with {len(elements)} elements.")


if __name__ == "__main__":
    build_voice_flow_excalidraw()
