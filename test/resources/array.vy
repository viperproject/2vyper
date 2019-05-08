
array: int128[12]
matrix: int128[12][12]
tensor: int128[2][2][2]


@public
def array_read() -> int128:
    a: int128 = self.array[5]
    return a + self.matrix[4][7] + self.tensor[0][1][0]


#@ ensures: result() == 10
@public
def array_write() -> int128:
    self.array[0] = 10
    return self.array[0]


#@ ensures: result() == 100
@public
def matrix_write() -> int128:
    a: int128[12] = self.array
    a[11] = 10
    i: int128 = a[11]
    self.matrix[1][2] = i
    self.matrix[1][2] = 100
    return self.matrix[1][2]


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 101
@public
def matrix_write_fail() -> int128:
    a: int128[12] = self.array
    a[11] = 10
    i: int128 = a[11]
    self.matrix[1][2] = i
    self.matrix[1][2] = 100
    return self.matrix[1][2]
