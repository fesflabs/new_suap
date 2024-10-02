# coding=utf-8

from random import randint


def generate_color():
    color = '#{:02x}{:02x}{:02x}'.format(*map(lambda x: randint(0, 255), range(3)))
    return color
