#!/usr/bin/python
# -*- coding: utf-8 -*-
# converts.py
# Author: Petter J. Barhaugen <petter@petternett.no>

from datetime import datetime, timedelta
import emoji  #allows emoji normalization/comparison

"""
converts date to wordle number and vice-versa.
emoji conversion would allow parsing of result emoji grids. currently unussed

Functions:
 - num_to_date(number): map Wordle number -> date
 - date_to_num(date_arg): map date -> Wordle number
 - convert_grid(message_lines): parse emoji result lines -> numeric grid

Dev note:
 - Functions are async to match the bot's calling convention. they are not async ops
"""

# Date-number calculation
date_format = "%d.%m.%Y %H:%M:%S"
min_date = "01.01.2022 00:00:00"

#base_num / base_date are a historical number/date pair
base_num  = 259
base_date = "05.03.2022 00:00:00"
base_date_dt = datetime.strptime(base_date, date_format)


async def num_to_date(number):
    delta = number - base_num
    ret = base_date_dt + timedelta(days=delta)

    return ret.date()

async def date_to_num(date_arg=datetime.today()):
    return base_num + int((date_arg - base_date_dt).days)



"""
Convert message lines to grid.
unused, experimental.
"""
async def convert_grid(message_lines):
    # Initalize 2D array with 0's
    res  = [ [0]*3 for i in range(3) ]

    for i, line in enumerate(message_lines):
        for j, char in enumerate(line):
            if char is emoji.emojize(":black_large_square:") or \
               char is emoji.emojize(":white_large_square:"):
                res[i][j] = 0
            if char is emoji.emojize(":yellow_square:"):
                res[i][j] = 1
            if char is emoji.emojize(":green_square"):
                res[i][j] = 2

    return res
