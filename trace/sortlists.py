def sort_lists_by(lists, key_list=0, desc=False):
    return list(zip(*sorted(zip(*lists), reverse=desc,
                 key=lambda x: x[key_list])))
