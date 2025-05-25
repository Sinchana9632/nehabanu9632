import os
import re
import logging
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
except ImportError:
    # Fallback for when transformers is not available
    pipeline = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    logging.warning("Transformers library not available. Using fallback sentiment analysis.")
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
except:
    pass

class MoodAnalyzer:
    def __init__(self):
        # Initialize sentiment analysis pipeline
        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
        except Exception as e:
            logging.warning(f"Could not load advanced model, using default: {e}")
            self.sentiment_analyzer = pipeline("sentiment-analysis", return_all_scores=True)
        
        # Initialize emotion detection pipeline
        try:
            self.emotion_analyzer = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                return_all_scores=True
            )
        except Exception as e:
            logging.warning(f"Could not load emotion model: {e}")
            self.emotion_analyzer = None
        
        # Emergency keywords that might indicate suicidal thoughts
        self.emergency_keywords = [
            'suicide', 'kill myself', 'end it all', 'want to die', 'no point living',
            'better off dead', 'worthless', 'hopeless', 'can\'t go on', 'end my life',
            'suicidal', 'kill me', 'hurt myself', 'self harm', 'cut myself',
            'overdose', 'jump off', 'hang myself', 'give up on life'
        ]
        
        # Initialize text processing tools
        try:
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
        except:
            self.stop_words = set()
            self.lemmatizer = None

    def preprocess_text(self, text):
        """Clean and preprocess text for analysis"""
        if not text:
            return ""
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
        
        if self.lemmatizer:
            try:
                # Tokenize and remove stop words
                tokens = word_tokenize(text)
                tokens = [self.lemmatizer.lemmatize(token) for token in tokens 
                         if token not in self.stop_words and len(token) > 2]
                return ' '.join(tokens)
            except:
                pass
        
        return text

    def analyze_sentiment(self, text):
        """Analyze sentiment of the given text"""
        if not text or len(text.strip()) < 3:
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'score': 0.0,
                'detailed_scores': {}
            }
        
        try:
            # Get sentiment analysis
            results = self.sentiment_analyzer(text)
            
            if isinstance(results, list) and len(results) > 0:
                # Handle different model outputs
                if isinstance(results[0], list):
                    scores = results[0]
                else:
                    scores = results
                
                # Process scores
                sentiment_scores = {}
                for score in scores:
                    label = score['label'].lower()
                    # Normalize labels
                    if 'positive' in label or label == 'pos':
                        sentiment_scores['positive'] = score['score']
                    elif 'negative' in label or label == 'neg':
                        sentiment_scores['negative'] = score['score']
                    else:
                        sentiment_scores['neutral'] = score['score']
                
                # Determine primary sentiment
                max_sentiment = max(sentiment_scores.items(), key=lambda x: x[1])
                primary_sentiment = max_sentiment[0]
                confidence = max_sentiment[1]
                
                # Calculate mood score (-1 to 1)
                mood_score = 0.0
                if 'positive' in sentiment_scores and 'negative' in sentiment_scores:
                    mood_score = sentiment_scores['positive'] - sentiment_scores['negative']
                elif 'positive' in sentiment_scores:
                    mood_score = sentiment_scores['positive'] - 0.5
                elif 'negative' in sentiment_scores:
                    mood_score = 0.5 - sentiment_scores['negative']
                
                return {
                    'sentiment': primary_sentiment,
                    'confidence': confidence,
                    'score': mood_score,
                    'detailed_scores': sentiment_scores
                }
                
        except Exception as e:
            logging.error(f"Error in sentiment analysis: {e}")
        
        return {
            'sentiment': 'neutral',
            'confidence': 0.0,
            'score': 0.0,
            'detailed_scores': {}
        }

    def detect_emotions(self, text):
        """Detect specific emotions in the text"""
        if not self.emotion_analyzer or not text:
            return []
        
        try:
            results = self.emotion_analyzer(text)
            emotions = []
            
            for result in results:
                if result['score'] > 0.3:  # Only include emotions with reasonable confidence
                    emotions.append({
                        'emotion': result['label'],
                        'confidence': result['score']
                    })
            
            # Sort by confidence
            emotions.sort(key=lambda x: x['confidence'], reverse=True)
            return emotions[:3]  # Return top 3 emotions
            
        except Exception as e:
            logging.error(f"Error in emotion detection: {e}")
            return []

    def check_emergency_keywords(self, text):
        """Check if text contains emergency/suicidal keywords"""
        if not text:
            return False, []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.emergency_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return len(found_keywords) > 0, found_keywords

    def analyze_mood_text(self, text):
        """Comprehensive mood analysis"""
        if not text:
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'mood_score': 0.0,
                'emotions': [],
                'is_emergency': False,
                'emergency_keywords': []
            }
        
        # Preprocess text
        processed_text = self.preprocess_text(text)
        
        # Analyze sentiment
        sentiment_result = self.analyze_sentiment(text)
        
        # Detect emotions
        emotions = self.detect_emotions(text)
        
        # Check for emergency keywords
        is_emergency, emergency_keywords = self.check_emergency_keywords(text)
        
        return {
            'sentiment': sentiment_result['sentiment'],
            'confidence': sentiment_result['confidence'],
            'mood_score': sentiment_result['score'],
            'detailed_scores': sentiment_result['detailed_scores'],
            'emotions': emotions,
            'is_emergency': is_emergency,
            'emergency_keywords': emergency_keywords
        }

    def calculate_mood_trend(self, mood_scores, days=7):
        """Calculate mood trend over specified days"""
        if len(mood_scores) < 2:
            return 'stable'
        
        recent_scores = mood_scores[-days:]
        
        # Calculate trend
        if len(recent_scores) >= 3:
            trend_sum = 0
            for i in range(1, len(recent_scores)):
                trend_sum += recent_scores[i] - recent_scores[i-1]
            
            avg_trend = trend_sum / (len(recent_scores) - 1)
            
            if avg_trend > 0.1:
                return 'improving'
            elif avg_trend < -0.1:
                return 'declining'
        
        return 'stable'

# Global analyzer instance
mood_analyzer = MoodAnalyzer()
