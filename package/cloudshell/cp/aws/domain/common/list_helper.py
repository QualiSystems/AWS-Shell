def first_or_default(lst, lambda_expression):
    result = filter(lambda_expression, lst)[:1]
    return result[0] if len(result) == 1 else None


def single(lst, lambda_expression):
    return filter(lambda_expression, lst)[0]


def index_of(lst, lambda_predicate):
    gen = (index for index, item in enumerate(lst) if lambda_predicate(item))

    try:
        first = gen.next()
    except StopIteration:
        return None

    return first