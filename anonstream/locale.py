from quart import current_app

LOCALES = current_app.locales

def get_lang_and_locale_from(context, burrow=(), validate=True):
    lang = context.args.get('lang')
    locale = LOCALES.get(lang)
    if locale is None:
        if validate:
            lang = None
        locale = LOCALES[None]
    for key in burrow:
        locale = locale[key]
    return lang, locale

def get_lang_from(context, validate=True):
    lang, locale = get_lang_and_locale_from(context, validate=validate)
    return lang

def get_locale_from(context, burrow=()):
    lang, locale = get_lang_and_locale_from(context)
    return locale
