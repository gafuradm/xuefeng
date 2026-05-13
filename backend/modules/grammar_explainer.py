import os
import json
import asyncio
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

load_dotenv()

# Функция для получения правильного пути к файлам в папке data
def get_data_path(filename: str) -> str:
    """Возвращает правильный путь к файлу в папке data"""
    base_dir = Path(__file__).parent.parent  # backend/
    return str(base_dir / "data" / filename)


class GrammarExplainer:
    """AI grammar explainer for Chinese"""
    
    def __init__(self):
        self.client = self._get_client()
        self.grammar_topics = self._load_grammar_topics()  # Загружаем из файла
        self.explanation_cache = {}
        
    def _load_grammar_topics(self) -> List[Dict]:
        """Загрузка грамматических тем из файла"""
        try:
            with open(get_data_path("grammar_topics.json"), "r", encoding="utf-8") as f:
                topics = json.load(f)
            print(f"✅ Загружено {len(topics)} грамматических тем")
            return topics
        except FileNotFoundError:
            print("⚠️ Файл grammar_topics.json не найден")
            return []
        except Exception as e:
            print(f"❌ Ошибка загрузки грамматики: {e}")
            return []
    
    def _get_client(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("⚠️ DeepSeek API key not found. Using fallback explanations.")
            return None
        
        return OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    
    async def explain_grammar(self, grammar_topic: Dict, user_level: str = "初") -> Dict:
        """
        Generate AI explanation for a grammar topic
        """
        # If no client or topics, return basic explanation
        if not self.client or not grammar_topic:
            return self._create_fallback_explanation(grammar_topic)
        
        cache_key = f"{grammar_topic.get('id', '')}_{user_level}"
        if cache_key in self.explanation_cache:
            return self.explanation_cache[cache_key]
        
        try:
            prompt = self._create_grammar_prompt(grammar_topic, user_level)
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Explain the grammar topic: {grammar_topic.get('chinese', '')}"}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON or create structure
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = self._parse_ai_response(result_text)
            
            # Add basic topic information
            result.update({
                "topic_id": grammar_topic.get("id", ""),
                "topic_chinese": grammar_topic.get("chinese", ""),
                "topic_pinyin": grammar_topic.get("pinyin", ""),
                "topic_english": grammar_topic.get("english", ""),
                "topic_russian": grammar_topic.get("russian", ""),
                "level": grammar_topic.get("level", "初"),
                "category": grammar_topic.get("category", ""),
                "tags": grammar_topic.get("tags", [])
            })
            
            # Cache
            self.explanation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return self._create_fallback_explanation(grammar_topic)
    
    def _create_grammar_prompt(self, topic: Dict, user_level: str) -> str:
        """Create prompt for grammar explanation"""
        
        level_map = {
            "初": "beginner (HSK 1-2)",
            "中": "intermediate (HSK 3-4)", 
            "高": "advanced (HSK 5-6)"
        }
        
        user_level_desc = level_map.get(user_level, "beginner")
        
        return f"""You are an expert Chinese language teacher for Russian-speaking students.
Your task is to give a clear, structured explanation of a grammar topic.

TOPIC INFORMATION:
- Chinese name: {topic.get('chinese', '')}
- Pinyin: {topic.get('pinyin', '')}
- English translation: {topic.get('english', '')}
- Russian translation: {topic.get('russian', '')}
- Topic difficulty level: {topic.get('level', '初')}
- Category: {topic.get('category', '')}
- Description: {topic.get('description', '')}
- Tags: {', '.join(topic.get('tags', []))}

STUDENT LEVEL: {user_level_desc}

Return the answer in JSON format with the following fields:
1. "topic_summary" - brief topic summary (2-3 sentences)
2. "basic_rule" - main usage rule
3. "formula" - grammar formula/structure (if applicable)
4. "examples" - array of 3-5 examples, each object contains:
   - "chinese": Chinese text
   - "pinyin": pinyin
   - "translation": Russian translation
   - "explanation": example explanation
5. "when_to_use" - when to use this construction
6. "common_mistakes" - common mistakes by Russian speakers
7. "memory_tips" - memorization tips
8. "practice_sentences" - 2-3 sentences for independent practice
9. "related_topics" - related grammar topics

Important requirements:
1. Explain as simply and clearly as possible
2. Provide real-life examples
3. Consider the student's level ({user_level_desc})
4. Give specific memorization tips
5. Mention features for Russian speakers

Format: JSON only, no additional text."""
    
    def _parse_ai_response(self, text: str) -> Dict:
        """Parses AI text into structured JSON"""
        import re
        
        # Try to find JSON in text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        # If failed, create structure
        return {
            "topic_summary": text[:200] + "..." if len(text) > 200 else text,
            "basic_rule": "See detailed explanation above",
            "formula": "Depends on usage context",
            "examples": [
                {
                    "chinese": "这是一个例子",
                    "pinyin": "zhè shì yí gè lì zi",
                    "translation": "This is an example",
                    "explanation": "Basic usage example"
                }
            ],
            "when_to_use": "In appropriate grammatical contexts",
            "common_mistakes": "Avoid literal translation from Russian",
            "memory_tips": "Practice with examples daily",
            "practice_sentences": ["Create your own sentence", "Translate to Chinese"],
            "related_topics": "Related grammatical constructions"
        }
    
    def _create_fallback_explanation(self, topic: Dict) -> Dict:
        """Create fallback explanation if AI is unavailable"""
        return {
            "topic_summary": f"{topic.get('chinese', '')} ({topic.get('english', '')}) - {topic.get('russian', '')}",
            "basic_rule": topic.get('description', 'Use according to grammar rules'),
            "formula": f"Structure: depends on usage of {topic.get('chinese', 'topic')}",
            "examples": [
                {
                    "chinese": "示例句子",
                    "pinyin": "shì lì jù zi",
                    "translation": "example sentence",
                    "explanation": "Basic example"
                }
            ],
            "when_to_use": "In appropriate grammatical contexts",
            "common_mistakes": "Avoid literal translation from Russian",
            "memory_tips": "Repeat several times a day",
            "practice_sentences": ["Practice using this grammar", "Create your own sentence"],
            "related_topics": "Other grammar topics",
            "fallback": True,
            "note": "AI explanation temporarily unavailable. This is a basic topic description."
        }
    
    async def generate_practice(self, topic_id: str, difficulty: str = "medium") -> Dict:
        """Generate practical exercises"""
        try:
            # Find topic
            topic = next((t for t in self.grammar_topics if t["id"] == topic_id), None)
            if not topic:
                return {"error": "Topic not found"}
            
            if not self.client:
                return self._create_fallback_exercises(topic)
            
            prompt = f"""Create Chinese grammar exercises.

TOPIC: {topic.get('chinese', '')} ({topic.get('pinyin', '')})
DESCRIPTION: {topic.get('description', '')}
LEVEL: {topic.get('level', '初')}
EXERCISE DIFFICULTY: {difficulty}

Create 4 types of exercises:

1. MULTIPLE CHOICE (3 questions):
   - Questions should be about the specific topic
   - 4 answer options (A, B, C, D)
   - Explanation of correct answer

2. FILL IN THE BLANKS:
   - Text with 3-4 blanks
   - Use topic {topic.get('chinese', '')}

3. ERROR CORRECTION:
   - 2-3 sentences with typical mistakes
   - Error explanations

4. SENTENCE FORMATION:
   - Provide words for composing sentences
   - Use grammar topic

Return ONLY JSON in format:
{{
    "multiple_choice": [
        {{
            "question": "question text",
            "options": ["A", "B", "C", "D"],
            "correct": "A",
            "explanation": "explanation"
        }}
    ],
    "fill_in_blanks": "text with blanks",
    "error_correction": "text with errors",
    "sentence_formation": "words for sentence formation"
}}"""
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You create Chinese grammar exercises. Reply ONLY in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            
            # Clean and parse JSON
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = self._create_fallback_exercises(topic)
            
            # Add metadata
            result["topic"] = topic.get('chinese', '')
            result["topic_russian"] = topic.get('russian', '')
            result["difficulty"] = difficulty
            
            return result
            
        except Exception as e:
            print(f"Error generating exercises: {e}")
            topic = next((t for t in self.grammar_topics if t["id"] == topic_id), None)
            return self._create_fallback_exercises(topic)
    
    def _create_fallback_exercises(self, topic: Dict) -> Dict:
        """Fallback exercises"""
        return {
            "multiple_choice": [
                {
                    "question": f"How to correctly use {topic.get('chinese', 'this grammar')}?",
                    "options": [
                        "In affirmative sentences",
                        "Only in questions",
                        "To express future tense",
                        "In negative sentences"
                    ],
                    "correct": "A",
                    "explanation": f"{topic.get('chinese', 'This construction')} is used in affirmative sentences"
                }
            ],
            "fill_in_blanks": f"Fill in the blanks using topic '{topic.get('chinese', '')}':\n\n1. 我昨天 ______ (do) homework。\n2. 他经常 ______ (use) this construction。",
            "error_correction": f"Correct errors in using topic '{topic.get('chinese', '')}':\n\n1. 我学中文在教室。\n2. 他吃饭了已经。",
            "sentence_formation": f"Compose sentences using topic '{topic.get('chinese', '')}':\n\n我, 喜欢, 学习, 中文, 在, 学校",
            "note": "Exercises generated automatically"
        }
    
    async def answer_grammar_question(self, question: str, context: Dict = None) -> Dict:
        """Answer a grammar question"""
        if not self.client:
            return {"answer": "AI service temporarily unavailable. Check API settings."}
        
        try:
            prompt = "You are an expert in Chinese grammar. Answer in detail and clearly."
            
            if context and context.get('topic'):
                prompt += f"\nContext: topic '{context['topic'].get('chinese', '')}'"
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            return {
                "answer": response.choices[0].message.content,
                "examples": "Study examples in the textbook",
                "practice_tip": "Practice daily"
            }
            
        except Exception as e:
            return {"error": str(e)}

# Global instance
grammar_explainer = GrammarExplainer()