"""
Comment Moderation Engine — auto-approve, auto-block, and learning.

Three-tier moderation:
1. BLOCK: spam patterns, excessive links, banned domains
2. AUTO-APPROVE: trusted users (3+ approved comments)  
3. PENDING: everything else awaits admin review

Learning: CommentModerationLog tracks admin decisions;
after 20+ decisions a simple TF-IDF classifier can flag/approve
comments automatically.
"""
import re
import logging

logger = logging.getLogger('news')


# ─── Spam patterns ─────────────────────────────────────────────
SPAM_KEYWORDS = [
    # Crypto / financial spam
    'bitcoin', 'crypto', 'blockchain', 'nft', 'airdrop', 'binance', 'coinbase',
    'forex', 'invest now', 'passive income', 'make money fast',
    'double your', 'guaranteed profit', 'trading signal',
    # Pharma spam
    'viagra', 'cialis', 'pharmacy', 'prescription',
    # Gambling / casino
    'casino', 'poker online', 'bet365', 'slot machine', 'jackpot',
    # SEO / link spam
    'seo services', 'backlink', 'buy followers', 'web traffic',
    'cheap website', 'rank your site',
    # Adult content
    'xxx', 'porn', 'adult content', 'onlyfans',
    # Generic scam
    'nigerian prince', 'congratulations you won', 'click here now',
    'free iphone', 'act now', 'limited time offer',
    'work from home', 'mlm', 'pyramid scheme',
]

SPAM_EMAIL_DOMAINS = [
    'tempmail.com', 'guerrillamail.com', 'mailinator.com',
    'yopmail.com', 'throwaway.email', 'dispostable.com',
    'fakeinbox.com', 'maildrop.cc', 'trashmail.com',
    'sharklasers.com', 'guerrillamailblock.com', 'grr.la',
]

# Max URLs allowed in a single comment
MAX_URLS_PER_COMMENT = 2

# Min/max comment length
MIN_COMMENT_LENGTH = 5
MAX_COMMENT_LENGTH = 5000

# Caps threshold — if > X% of text is uppercase, likely spam
CAPS_THRESHOLD = 0.6

# Minimum approved comments for auto-approve status
TRUSTED_USER_MIN_APPROVED = 3

# URL regex
URL_PATTERN = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+', re.IGNORECASE)


class ModerationResult:
    """Result of moderation check."""
    STATUS_PENDING = 'pending'
    STATUS_AUTO_APPROVED = 'auto_approved'
    STATUS_AUTO_BLOCKED = 'auto_blocked'
    
    def __init__(self, status, reason=''):
        self.status = status
        self.reason = reason
        self.is_approved = (status == self.STATUS_AUTO_APPROVED)

    def __repr__(self):
        return f"ModerationResult(status='{self.status}', reason='{self.reason}')"


def moderate_comment(content, name='', email='', user=None, article_id=None):
    """
    Run comment through moderation rules.
    
    Returns ModerationResult with status:
    - 'auto_blocked': comment should be hidden (spam/abuse)
    - 'auto_approved': trusted user, auto-approve
    - 'pending': needs admin review
    """
    content_text = (content or '').strip()
    email_lower = (email or '').lower()
    
    # ─── BLOCK rules (instant) ───────────────────────────
    
    # Rule 1: Too short
    if len(content_text) < MIN_COMMENT_LENGTH:
        return ModerationResult(
            ModerationResult.STATUS_AUTO_BLOCKED,
            f"Comment too short ({len(content_text)} chars, min {MIN_COMMENT_LENGTH})"
        )
    
    # Rule 2: Too long
    if len(content_text) > MAX_COMMENT_LENGTH:
        return ModerationResult(
            ModerationResult.STATUS_AUTO_BLOCKED,
            f"Comment too long ({len(content_text)} chars, max {MAX_COMMENT_LENGTH})"
        )
    
    # Rule 3: Spam keywords
    content_lower = content_text.lower()
    for keyword in SPAM_KEYWORDS:
        if keyword in content_lower:
            return ModerationResult(
                ModerationResult.STATUS_AUTO_BLOCKED,
                f"Spam keyword detected: '{keyword}'"
            )
    
    # Rule 4: Check name for spam too
    name_lower = (name or '').lower()
    for keyword in SPAM_KEYWORDS:
        if keyword in name_lower:
            return ModerationResult(
                ModerationResult.STATUS_AUTO_BLOCKED,
                f"Spam keyword in name: '{keyword}'"
            )
    
    # Rule 5: Banned email domains
    for domain in SPAM_EMAIL_DOMAINS:
        if email_lower.endswith(f'@{domain}'):
            return ModerationResult(
                ModerationResult.STATUS_AUTO_BLOCKED,
                f"Disposable email domain: {domain}"
            )
    
    # Rule 6: Too many URLs
    urls = URL_PATTERN.findall(content_text)
    if len(urls) > MAX_URLS_PER_COMMENT:
        return ModerationResult(
            ModerationResult.STATUS_AUTO_BLOCKED,
            f"Too many URLs ({len(urls)}, max {MAX_URLS_PER_COMMENT})"
        )
    
    # Rule 7: Excessive CAPS
    alpha_chars = [c for c in content_text if c.isalpha()]
    if len(alpha_chars) > 10:
        caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if caps_ratio > CAPS_THRESHOLD:
            return ModerationResult(
                ModerationResult.STATUS_AUTO_BLOCKED,
                f"Excessive caps ({caps_ratio:.0%} uppercase)"
            )
    
    # Rule 8: Repeated characters (e.g. "aaaaaaa", "!!!!!!!")
    if re.search(r'(.)\1{7,}', content_text):
        return ModerationResult(
            ModerationResult.STATUS_AUTO_BLOCKED,
            "Repeated characters detected"
        )
    
    # ─── AUTO-APPROVE rules ──────────────────────────────
    
    # Rule A: Staff users always auto-approve
    if user and user.is_staff:
        return ModerationResult(
            ModerationResult.STATUS_AUTO_APPROVED,
            "Staff user"
        )
    
    # Rule B: Trusted users (3+ previously approved comments)
    if user:
        try:
            from news.models import Comment
            approved_count = Comment.objects.filter(
                user=user,
                is_approved=True,
            ).count()
            if approved_count >= TRUSTED_USER_MIN_APPROVED:
                return ModerationResult(
                    ModerationResult.STATUS_AUTO_APPROVED,
                    f"Trusted user ({approved_count} approved comments)"
                )
        except Exception:
            pass
    
    # Rule C: Trusted email (3+ previously approved comments from same email)
    if email_lower:
        try:
            from news.models import Comment
            email_approved = Comment.objects.filter(
                email__iexact=email_lower,
                is_approved=True,
            ).count()
            if email_approved >= TRUSTED_USER_MIN_APPROVED:
                return ModerationResult(
                    ModerationResult.STATUS_AUTO_APPROVED,
                    f"Trusted email ({email_approved} approved comments)"
                )
        except Exception:
            pass
    
    # ─── ML classifier check (if trained) ────────────────
    try:
        result = _ml_classify(content_text)
        if result is not None:
            return result
    except Exception:
        pass
    
    # ─── DEFAULT: pending ────────────────────────────────
    return ModerationResult(
        ModerationResult.STATUS_PENDING,
        "Awaiting admin review"
    )


def _ml_classify(content):
    """
    Run TF-IDF classifier if model exists.
    Returns ModerationResult or None if no model trained.
    """
    import os
    from django.conf import settings
    
    model_path = os.path.join(settings.MEDIA_ROOT, 'ml', 'comment_classifier.pkl')
    if not os.path.exists(model_path):
        return None
    
    try:
        import pickle
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        vectorizer = data['vectorizer']
        classifier = data['classifier']
        
        X = vectorizer.transform([content])
        prediction = classifier.predict(X)[0]
        probability = classifier.predict_proba(X)[0]
        
        confidence = max(probability)
        
        # Only auto-decide if confidence > 80%
        if confidence < 0.8:
            return None
        
        if prediction == 'approved':
            return ModerationResult(
                ModerationResult.STATUS_AUTO_APPROVED,
                f"ML classifier (confidence: {confidence:.0%})"
            )
        else:
            return ModerationResult(
                ModerationResult.STATUS_AUTO_BLOCKED,
                f"ML classifier flagged as spam (confidence: {confidence:.0%})"
            )
    except Exception as e:
        logger.warning(f"ML classifier error: {e}")
        return None


def train_classifier():
    """
    Train TF-IDF + LogisticRegression classifier from CommentModerationLog entries.
    Called manually from management command or admin action.
    Returns (success: bool, message: str).
    """
    import os
    from django.conf import settings
    
    try:
        from news.models import CommentModerationLog
        
        logs = CommentModerationLog.objects.select_related('comment').all()
        if logs.count() < 20:
            return False, f"Need at least 20 moderation decisions to train (have {logs.count()})"
        
        texts = []
        labels = []
        for log in logs:
            if log.comment and log.comment.content:
                texts.append(log.comment.content)
                labels.append(log.decision)
        
        if len(set(labels)) < 2:
            return False, "Need both 'approved' and 'rejected' examples to train"
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
        import pickle
        import numpy as np
        
        vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        X = vectorizer.fit_transform(texts)
        y = np.array(labels)
        
        classifier = LogisticRegression(max_iter=1000, class_weight='balanced')
        
        # Cross-validate
        scores = cross_val_score(classifier, X, y, cv=min(5, len(texts) // 2), scoring='accuracy')
        avg_score = scores.mean()
        
        # Train on full data
        classifier.fit(X, y)
        
        # Save model
        model_dir = os.path.join(settings.MEDIA_ROOT, 'ml')
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, 'comment_classifier.pkl')
        
        with open(model_path, 'wb') as f:
            pickle.dump({
                'vectorizer': vectorizer,
                'classifier': classifier,
                'accuracy': avg_score,
                'samples': len(texts),
            }, f)
        
        return True, f"Trained on {len(texts)} samples, CV accuracy: {avg_score:.1%}"
    
    except ImportError:
        return False, "scikit-learn not installed (pip install scikit-learn)"
    except Exception as e:
        return False, f"Training error: {str(e)}"
