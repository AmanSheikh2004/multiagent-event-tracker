def simple_validate(event_dict):
    errors = []
    if not event_dict or not getattr(event_dict, 'date', None):
        errors.append('Missing date')
    if not getattr(event_dict, 'category', None):
        errors.append('Missing category')
    status = 'ok' if not errors else 'needs_review'
    return {'status': status, 'errors': errors}

class ValidatorAgent:
    def process(self, data):
        ev = data.get('event')
        return simple_validate(ev)
