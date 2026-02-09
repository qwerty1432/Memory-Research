def build_messages(context: str, user_message: str) -> list[dict]:
    """
    Build messages array for the GenAI API with context and user message.
    """
    system_prompt = "You are a friendly AI companion. Use the provided context to have a natural conversation."
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add context if available
    if context.strip():
        messages.append({
            "role": "system",
            "content": f"Context from previous conversations:\n{context}"
        })
    
    # Add user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages


async def extract_memories_from_conversation(
    user_message: str,
    existing_memories: list[str] = None
) -> list[str]:
    """
    Extract potential memory candidates from user message using LLM.
    
    CRITICAL: Only extracts from the user's message, NOT from assistant responses or inferences.
    
    Args:
        user_message: The user's message to extract memories from
        existing_memories: List of existing memory texts to avoid duplicates
    
    Returns list of memory candidate strings like:
    - "User mentioned liking hiking"
    - "User is studying at Purdue"
    """
    # Build existing memories context
    existing_context = ""
    if existing_memories:
        existing_context = "\n\nExisting memories (DO NOT extract these again):\n" + "\n".join(f"- {mem}" for mem in existing_memories[:20])  # Limit to 20 most recent
    
    extraction_prompt = f"""You are a memory extraction assistant. Extract ONLY factual information that the USER explicitly stated in their message.

CRITICAL RULES:
1. Extract ONLY from the user's message below - ignore everything else
2. Do NOT extract information from assistant responses or anything the assistant inferred
3. Only extract if the information is NEW and explicitly stated by the user
4. Do NOT extract information that already exists in the existing memories list
5. Return "None" if no new information is present in the user's message
6. Extract only clear, factual statements about the user
7. Return each memory as a separate line, starting with "User" (e.g., "User mentioned liking hiking")

User's message:
{user_message}{existing_context}

Extract memories (one per line, or "None" if nothing new):"""

    messages = [
        {
            "role": "system",
            "content": "You are a memory extraction assistant. Extract ONLY factual information that the user explicitly stated. Do NOT extract from assistant responses or inferences."
        },
        {
            "role": "user",
            "content": extraction_prompt
        }
    ]
    
    from .genai_client import call_genai
    
    try:
        response = await call_genai(messages, stream=False, temperature=0.1, max_tokens=200)
        
        # Parse response into memory candidates
        memories = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line.lower() != "none" and line.startswith("User"):
                # Clean up the memory text
                memory_text = line
                if len(memory_text) > 200:
                    memory_text = memory_text[:200]
                memories.append(memory_text)
        
        return memories
    except Exception as e:
        # If extraction fails, return empty list
        print(f"Memory extraction error: {e}")
        return []

