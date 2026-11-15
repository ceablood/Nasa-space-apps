# -*- coding: utf-8 -*-
from . import t_data, t_game, t_nova, t_ui1, t_ui2, t_ui3
from . import x_data, x_game, x_nova, x_ui1, x_ui2, x_ui3

T = {}
for _t, _x in ((t_data, x_data), (t_game, x_game), (t_nova, x_nova), (t_ui1, x_ui1), (t_ui2, x_ui2), (t_ui3, x_ui3)):
    for _row, _xr in zip(_t.ROWS, _x.ROWS):
        T[_row[0]] = _xr[0]
