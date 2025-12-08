# TOON: Token Oriented Object Notation

## Philosophy
TOON is a strictly utilitarian data and communication format designed to minimize Token Usage (Input/Output) for LLMs while retaining semantic clarity. It prioritizes **Information Density**.

## Rules

### 1. Protocol (Communication)
Instead of conversational filler, use structured blocks:
- `[STS]`: Status (Current State)
- `[ACT]`: Action (What is being done)
- `[RES]`: Result (Outcome)
- `[ERR]`: Error (If any)
- `[ASK]`: Question/Request

### 2. Schema (Data/JSON)
Abbreviate keys where context is implied.
**Standard JSON:**
```json
{
  "timestamp": "2025-12-08T09:00:00Z",
  "service": "ai_receptionist",
  "status": "healthy",
  "uptime": "24 hours"
}
```

**TOON:**
```json
{"t":"09:00Z","s":"ai_rep","st":"ok","up":"24h"}
```

### 3. Prompt Engineering (System Prompts)
Remove "persona" fluff if not functionally required. Use imperative, dense instructions.

**Standard:**
"You are a helpful assistant designed to help customers..."

**TOON:**
"Role: Assistant. Goal: Help customers. Tone: Polite, Efficient."
