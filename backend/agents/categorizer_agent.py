def categorize_text(text):
    t = text.lower()
    if 'faculty' in t or 'staff' in t or 'prof' in t:
        return 'Faculty Event'
    if 'quiz' in t:
        return 'Student Quiz'
    if 'student' in t or 'workshop' in t or 'seminar' in t:
        return 'Student Event'
    return 'General Event'

class CategorizerAgent:
    def process(self, data):
        text = data.get('raw_text','')
        return {'category': categorize_text(text)}
