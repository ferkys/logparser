import yaml
from collections import defaultdict
from datetime import datetime, timedelta
from string import Template

_options = defaultdict(dict)


def get_option(path):
    def _get_option(tmp_dict, key, pending_path):
        if pending_path:
            head, *tail = pending_path
            return _get_option(tmp_dict[key], head, tail)
        else:
            if isinstance(tmp_dict[key], str):
                return _apply_template(tmp_dict[key])
            else:
                return tmp_dict[key]
    head, *tail = path.split('.')
    return _get_option(_options, head, tail)


def set_option(path, value):
    assert value, "Value must not be `None`"

    def _set_option(tmp_dict, pending_path, value):
        head, *tail = pending_path

        if tail:
            # Ugly, but We need to pass _set_option a defaultdict type
            tmp2 = defaultdict(dict)
            tmp2.update(tmp_dict)

            tmp_dict[head] = _set_option(tmp2[head], tail, value)
        else:
            tmp_dict[head] = value

        return tmp_dict

    head, *tail = path.split('.')
    if tail:
        _options.update({head: _set_option(_options[head], tail, value)})
    else:
        _options.update({head: value})


def exists_option(key):
    try:
        get_option(key)
    except KeyError:
        return False
    return True


def update_with_dict(dct):
    _options.update(dct)


def update_from_yaml(yaml_path):
    with open(yaml_path, 'r') as f:
        update_with_dict(yaml.load(f))



def _get_template_tags(dt_time):
    """

    :param dt_time:
    :return:
    """
    assert isinstance(dt_time, datetime), "_get_tags: dt_time argument not of type datetime"

    dt_time_minus_1 = dt_time - timedelta(days=1)
    dt_time_minus_2 = dt_time - timedelta(days=2)

    return {
        'TodayYear': dt_time.year,
        'TodayMonth': dt_time.strftime("%m"),
        'TodayDay': dt_time.strftime("%d"),

        'YesterdayYear': dt_time_minus_1.year,
        'YesterdayMonth': dt_time_minus_1.strftime("%m"),
        'YesterdayDay': dt_time_minus_1.strftime("%d"),

        'TwoDaysAgoYear': dt_time_minus_2.year,
        'TwoDaysAgoMonth': dt_time_minus_2.strftime("%m"),
        'TwoDaysAgoDay': dt_time_minus_2.strftime("%d"),

        'Now': dt_time.strftime('%Y%m%d%H%M%S')
    }


def _apply_template(tagged_string):
    """

    """
    pat = Template(tagged_string)
    pat = pat.substitute(_get_template_tags(datetime.now()))

    return pat

