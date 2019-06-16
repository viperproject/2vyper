
time: timestamp


#@ ensures: self.time == t
#@ ensures: t >= 0
@public
def set_time(t: timestamp):
    self.time = t


#@ ensures: self.time == old(self.time) + t
@public
def increase_time(t: timedelta):
    self.time += t


#@ ensures: self.time == block.timestamp
@public
def use_block():
    self.time = block.timestamp