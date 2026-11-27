# -*- coding: utf-8 -*-
from . import t_data, t_game, t_nova, t_ui1, t_ui2, t_ui3, t_v34, t_v36

T = {}
for _m in (t_data, t_game, t_nova, t_ui1, t_ui2, t_ui3, t_v34, t_v36):
    for _row in _m.ROWS:
        T[_row[0]] = _row[1]

# AJANS > DAHA FAZLA: bu dilde yazılmış çeviriler
from . import t_more as _more
for _row in _more.ROWS:
    T[_row[0]] = _row[1]
