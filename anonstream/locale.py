from quart import current_app

LOCALES = current_app.locales

def get_lang_and_locale_from(context):
    lang = context.args.get('lang')
    locale = LOCALES.get(lang)
    if locale is None:
        lang, locale = None, LOCALES[None]
    return lang, locale

def get_lang_from(context):
    lang, locale = get_lang_and_locale_from(context)
    return lang

def get_locale_from(context):
    lang, locale = get_lang_and_locale_from(context)
    return locale
