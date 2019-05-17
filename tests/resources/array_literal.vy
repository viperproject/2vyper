
array: int128[5]


@public
def assign_field():
    self.array = [1, 2, 3, 4, 5]


@public
def assign_local():
    a: int128[5] = [2, 3, 4, 5, 6]