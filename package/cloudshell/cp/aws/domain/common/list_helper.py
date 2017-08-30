def first_or_default(lst, lambda_expression):
    result = filter(lambda_expression, lst)[:1]
    return result[0] if len(result) == 1 else None


def single(lst, lambda_expression):
    return filter(lambda_expression, lst)[0]
