
#@ requires: start > 0
#@ ensures: result() == (100 * 99) / 2 - 100 * start
@public
def sum_of_numbers(start: int128) -> int128:
    sum: int128
    for i in range(start, start + 100):
        sum += i

    return sum
