
array: int128[12]
matrix: int128[12][12]
tensor: int128[2][2][2]

zeros: int128[1000]

mp: map(int128, int128[10])

#:: Label(CONST_ZEROS)
#@ invariant: self.zeros == old(self.zeros)


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


#@ ensures: not success()
@public
def out_of_bounds_read():
    a: int128 = self.array[42]


#@ ensures: not success()
@public
def out_of_bounds_write():
    self.array[42] = 12


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 0
@public
def get_zeros_fail() -> int128:
    return self.zeros[1000]


#:: ExpectedOutput(postcondition.violated:assertion.false)
#@ ensures: result() == 0
@public
def get_zeros_at_fail(i: int128) -> int128:
    return self.zeros[i]


#:: ExpectedOutput(invariant.violated:assertion.false, CONST_ZEROS)
@public
def set_zeros_fail():
    self.zeros[12] = 100


@public
def acc_map():
    self.mp[1][2] = 5


#@ ensures: not success()
@public
def acc_bounds() -> int128:
    return self.mp[2][1000]


#:: ExpectedOutput(not.wellformed:seq.index.negative)
#@ ensures: a[n] == 0
@public
def index_negative_fail(a: int128[5], n: int128):
    pass


#:: ExpectedOutput(not.wellformed:seq.index.length)
#@ ensures: implies(n >= 0, a[n] == 0)
@public
def index_size_fail(a: int128[5], n: int128):
    pass