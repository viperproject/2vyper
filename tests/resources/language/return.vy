
#@ ensures: result() == 5
@public
def normal() -> int128:
    return 5

#@ ensures: result() == 0
@public
def in_loop() -> int128:
    for i in range(3):
        return i
    
    return -1

@public
def no_val():
    return
