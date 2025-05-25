import re
import logging

# Basic sentiment analysis using keyword matching
# This is a simplified version that doesn't require external ML libraries

class MoodAnalyzer:
    def __init__(self):
        # Emergency keywords that might indicate suicidal thoughts
        self.emergency_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die', 'no point living',
            'better off dead', 'worthless', 'hopeless', 'can\'t go on', 'end my life',
            'suicidal', 'kill me', 'hurt myself', 'self harm', 'cut myself',
            'overdose', 'jump off', 'hang myself', 'give up on life'
        ]
        
        # Positive and negative keywords for basic sentiment analysis
        self.positive_keywords = [
            'happy', 'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'joy', 'excited', 'love', 'perfect', 'awesome', 'brilliant', 'cheerful',
            'delighted', 'pleased', 'grateful', 'thankful', 'blessed', 'optimistic',
            'confident', 'proud', 'satisfied', 'content', 'peaceful', 'relaxed'
        ]
        
        self.negative_keywords = [
            'sad', 'bad', 'terrible', 'awful', 'horrible', 'depressed', 'angry',
            'frustrated', 'upset', 'worried', 'anxious', 'stressed', 'overwhelmed',
            'lonely', 'tired', 'exhausted', 'disappointed', 'hurt', 'pain',
            'scared', 'afraid', 'nervous', 'angry', 'mad', 'furious', 'hate'
        ]
        
        # Basic stop words
        self.stop_words = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
            'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she',
            'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
            'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an',
            'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of',
            'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after', 'above',
            'below', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once'
        }

    def preprocess_text(self, text):
        """Clean and preprocess text for analysis"""
        if not text:
            return ""
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
        
        # Simple tokenization and stop word removal
        words = text.split()
        filtered_words = [word for word in words if word not in self.stop_words and len(word) > 2]
        
        return ' '.join(filtered_words)

    def analyze_sentiment(self, text):
        """Analyze sentiment of the given text using keyword matching"""
        if not text or len(text.strip()) < 3:
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'score': 0.0,
                'detailed_scores': {}
            }
        
        # Preprocess text
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        # Count positive and negative words
        positive_count = sum(1 for word in words if word in self.positive_keywords)
        negative_count = sum(1 for word in words if word in self.negative_keywords)
        total_words = len(words)
        
        # Calculate sentiment scores
        if total_words == 0:
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'score': 0.0,
                'detailed_scores': {}
            }
        
        positive_ratio = positive_count / total_words
        negative_ratio = negative_count / total_words
        
        # Determine primary sentiment
        if positive_count > negative_count:
            primary_sentiment = 'positive'
            confidence = min(0.9, positive_ratio * 3)  # Cap confidence at 0.9
            mood_score = min(1.0, positive_ratio * 2)  # Scale to -1 to 1
        elif negative_count > positive_count:
            primary_sentiment = 'negative'
            confidence = min(0.9, negative_ratio * 3)
            mood_score = max(-1.0, -negative_ratio * 2)
        else:
            primary_sentiment = 'neutral'
            confidence = 0.5
            mood_score = 0.0
        
        return {
            'sentiment': primary_sentiment,
            'confidence': confidence,
            'score': mood_score,
            'detailed_scores': {
                'positive': positive_ratio,
                'negative': negative_ratio,
                'neutral': 1.0 - positive_ratio - negative_ratio
            }
        }

    def detect_emotions(self, text):
        """Detect specific emotions in the text using keyword matching"""
        if not text:
            return []
        
        # Emotion keywords
        emotion_keywords = {
            'joy': ['happy', 'joy', 'excited', 'cheerful', 'delighted', 'elated'],
            'sadness': ['sad', 'depressed', 'lonely', 'disappointed', 'grief'],
            'anger': ['angry', 'mad', 'furious', 'frustrated', 'irritated'],
            'fear': ['scared', 'afraid', 'worried', 'anxious', 'nervous'],
            'love': ['love', 'adore', 'cherish', 'affection', 'care'],
            'gratitude': ['grateful', 'thankful', 'blessed', 'appreciative']
        }
        
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        emotions = []
        for emotion, keywords in emotion_keywords.items():
            count = sum(1 for word in words if word in keywords)
            if count > 0:
                confidence = min(0.9, count / len(words) * 5)  # Scale confidence
                emotions.append({
                    'emotion': emotion,
                    'confidence': confidence
                })
        
        # Sort by confidence
        emotions.sort(key=lambda x: x['confidence'], reverse=True)
        return emotions[:3]  # Return top 3 emotions

    def check_emergency_keywords(self, text):
        """Check if text contains emergency/suicidal keywords"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.emergency_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords

    def analyze_mood_text(self, text):
        """Comprehensive mood analysis"""
        if not text:
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'score': 0.0,
                'emotions': [],
                'emergency_keywords': []
            }
        
        # Get sentiment analysis
        sentiment_result = self.analyze_sentiment(text)
        
        # Get emotions
        emotions = self.detect_emotions(text)
        
        # Check for emergency keywords
        emergency_keywords = self.check_emergency_keywords(text)
        
        return {
            'sentiment': sentiment_result['sentiment'],
            'confidence': sentiment_result['confidence'],
            'score': sentiment_result['score'],
            'emotions': emotions,
            'emergency_keywords': emergency_keywords,
            'detailed_scores': sentiment_result['detailed_scores']
        }

    def calculate_mood_trend(self, mood_scores, days=7):
        """Calculate mood trend over specified days"""
        if len(mood_scores) < 2:
            return 'stable'
        
        # Calculate simple trend
        recent_avg = sum(mood_scores[-3:]) / len(mood_scores[-3:]) if len(mood_scores) >= 3 else mood_scores[-1]
        older_avg = sum(mood_scores[:-3]) / len(mood_scores[:-3]) if len(mood_scores) > 3 else mood_scores[0]
        
        difference = recent_avg - older_avg
        
        if difference > 0.2:
            return 'improving'
        elif difference < -0.2:
            return 'declining'
        else:
            return 'stable'