import json
import os
import openai
from typing import Dict, Any, Optional

SYSTEM_PROMPT = """
You are an expert Data Engineering mentor. Your task is to evaluate a student's answer to a technical question (SQL or Python).

Compare the USER ANSWER against the CANONICAL ANSWER. 
- Logic and understanding are more important than exact syntax.
- If the user answer is essentially correct or shows they understand the core concept, mark it as is_correct: true.
- If correct: Provide detailed, encouraging feedback (3-4 sentences) that explains the concept deeper or adds interesting context.
- If incorrect: Provide short feedback (max 2 sentences) guiding them to the right track.

You MUST return a JSON object with the following fields:
1. "is_correct": boolean
2. "confidence": float (0.0 to 1.0) - how sure you are that the user understands the concept.
3. "short_feedback": string (3-4 sentences if correct, max 2 if incorrect)
4. "hint": string (only if is_correct is false, a small nudge)

Example Output:
{
  "is_correct": true,
  "confidence": 0.95,
  "short_feedback": "Spot on! You correctly identified the difference between UNION and UNION ALL. UNION ALL is generally faster because it doesn't incur the overhead of sorting to remove duplicates, which is a key performance consideration in large datasets.",
  "hint": null
}
"""

class LLMEvaluator:
    def __init__(self):
        import logging
        self.logger = logging.getLogger(__name__)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment.")
        self.client = openai.AsyncClient(api_key=api_key)

    async def generate_hint(self, question_text: str, canonical_answer: str) -> str:
        """
        Generates a hint for the user without revealing the answer.
        """
        prompt = f"""
        You are a helpful tutor. A student is stuck on this question:
        
        QUESTION: {question_text}
        CANONICAL ANSWER: {canonical_answer}
        
        Provide a SHORT, helpful hint (max 1 sentence) that guides them towards the solution 
        without giving it away explicitly.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Hint Generation Error: {e}", exc_info=True)
            return "Review the concepts related to this topic."

    async def evaluate_answer(self, question_text: str, canonical_answer: str, user_answer: str) -> Dict[str, Any]:
        """
        Evaluates the user's answer using OpenAI.
        Returns a dictionary with is_correct, confidence, short_feedback, and hint.
        """
        user_prompt = f"""
        QUESTION: {question_text}
        
        CANONICAL ANSWER: {canonical_answer}
        
        USER ANSWER: {user_answer}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Or gpt-3.5-turbo depending on budget/preference
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Enforce confidence threshold logic from requirements
            if result.get("confidence", 0) < 0.75:
                result["is_correct"] = False
                
            return result

        except Exception as e:
            self.logger.error(f"LLM Evaluation Error: {e}", exc_info=True)
            # Fallback safe response
            return {
                "is_correct": False,
                "confidence": 0.0,
                "short_feedback": "Unable to evaluate automatically. Please compare with the canonical answer.",
                "hint": None
            }
