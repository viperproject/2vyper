
ss: string[5]


#@ invariant: len(self.ss) == 5


@public
def set_ss(new_ss: string[5]):
    self.ss = new_ss
    self.ss = "asdfg"


#@ ensures: len(self.ss) == 5
@public
def get_ss() -> string[6]:
    return self.ss