def get_next_id(model):
    try:
        id = model.objects.latest().pk + 1
    except model.DoesNotExist:
        id = 1
    return id
