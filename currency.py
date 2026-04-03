from currency_utils import convert, format_currency

def get_rate(amount, src, dst):
    return format_currency(convert(amount, src, dst), dst)
