def nl2br_filter(text):
    if not text:
        return ""
    return text.replace('\n', '<br>')

def init_filters(app):
    app.template_filter('nl2br')(nl2br_filter) 