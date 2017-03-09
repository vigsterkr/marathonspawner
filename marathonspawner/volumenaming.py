# from dockerspawner
def default_format_volume_name(template, spawner):
    if template is None:
        return None
    return template.format(username=spawner.user.name)
