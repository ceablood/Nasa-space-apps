# -*- coding: utf-8 -*-
from . import t_data, t_game, t_nova, t_ui1, t_ui2, t_ui3
from . import x_data, x_game, x_nova, x_ui1, x_ui2, x_ui3

T = {}
for _t, _x in ((t_data, x_data), (t_game, x_game), (t_nova, x_nova), (t_ui1, x_ui1), (t_ui2, x_ui2), (t_ui3, x_ui3)):
    for _row, _xr in zip(_t.ROWS, _x.ROWS):
        T[_row[0]] = _xr[2]

# Sürüm 3.2+ metinleri için bu dilde çeviri yoksa İngilizce kullanılır (Türkçe kaynağa düşmez)
from . import t_v34 as _v34
for _row in _v34.ROWS:
    T.setdefault(_row[0], _row[1])
from . import t_v36 as _v36
for _row in _v36.ROWS:
    T.setdefault(_row[0], _row[1])

# AJANS > DAHA FAZLA: bu dilde yazılmış çeviriler
from . import t_more as _more
for _row in _more.ROWS:
    T[_row[0]] = _row[5]
