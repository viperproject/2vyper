
array: int128[12]
matrix: int128[12][12]


@public
def array_read() -> int128:
    a: int128 = self.array[5]
    return a + self.matrix[4][7]