from sqlalchemy.inspection import inspect


def model_to_dict(instance):
    return {
        c.key: getattr(instance, c.key) for c in inspect(instance).mapper.column_attrs
    }


